import io

import segno
from fastapi import APIRouter, Response, status

from wcam.api.health import create_health_router
from wcam.api.schemas import PairingResponse, QualityPresetRequest, StatusResponse, iso_utc, status_response
from wcam.services import AgentServices

QR_ERROR_LEVEL = "m"
QR_DARK = "#000"
QR_LIGHT = "#fff"
PAIRING_FRAGMENT = "#t="


def pairing_url(phone_page_url: str, token: str) -> str:
    return f"{phone_page_url}{PAIRING_FRAGMENT}{token}"


def qr_svg(url: str) -> str:
    document = io.BytesIO()
    segno.make(url, error=QR_ERROR_LEVEL).save(
        document,
        kind="svg",
        xmldecl=False,
        svgns=True,
        omitsize=True,
        dark=QR_DARK,
        light=QR_LIGHT,
    )
    return document.getvalue().decode("utf-8")


def create_console_router(services: AgentServices, phone_page_url: str) -> APIRouter:
    manager = services.manager
    router = APIRouter()
    router.include_router(create_health_router("console"))

    @router.post(
        "/api/pairing",
        status_code=status.HTTP_201_CREATED,
        summary="Open the pairing window",
        description="Generates a one-time token valid for 120 s, invalidating the previous one, and returns the "
        "phone URL with the token in the fragment and its QR code as SVG.",
    )
    async def open_pairing() -> PairingResponse:
        ticket = manager.open_pairing()
        url = pairing_url(phone_page_url, ticket.token)
        return PairingResponse(url=url, qr_svg=qr_svg(url), expires_at=iso_utc(ticket.expires_at))

    @router.delete(
        "/api/pairing",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Close the pairing window",
        description="Invalidates the current pairing token.",
    )
    async def close_pairing() -> Response:
        manager.close_pairing()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get(
        "/api/status",
        summary="Agent status",
        description="Pairing window, current session with its confirmation code and measured video, why the last "
        "session ended, the virtual camera, the quality preset, the agent CPU and, with a reference file, the "
        "measured quality.",
    )
    async def get_status() -> StatusResponse:
        return status_response(
            manager.status(), services.pipeline, services.cpu.percent, services.comparisons is not None
        )

    @router.put(
        "/api/quality-preset",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Choose the quality preset",
        description="Sets the maximum bitrate for the current session and the next ones until the agent "
        "closes, and tells the connected phone.",
    )
    async def set_quality_preset(body: QualityPresetRequest) -> Response:
        manager.set_quality_preset(body.preset)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.post(
        "/api/sessions/current/confirm",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Confirm the session",
        description="Opens the frame gate after the user checked that both screens show the same code.",
    )
    async def confirm_session() -> Response:
        manager.confirm()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.post(
        "/api/sessions/current/reject",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Reject the session",
        description="Ends the session waiting for confirmation. A new pairing is required.",
    )
    async def reject_session() -> Response:
        await manager.reject()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.delete(
        "/api/sessions/current",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Disconnect the phone",
        description="Ends the current session from the computer.",
    )
    async def disconnect_session() -> Response:
        await manager.disconnect()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router

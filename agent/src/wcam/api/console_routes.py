import io

import segno
from fastapi import APIRouter, Response, status
from fastapi.responses import StreamingResponse

from wcam.api.events import developer_events, event_stream, repeated_events
from wcam.api.health import create_health_router
from wcam.api.schemas import (
    ControlsRequest,
    PairingResponse,
    PreviewRequest,
    PreviewResponse,
    StatusResponse,
    VideoFormatRequest,
    iso_utc,
    status_response,
)
from wcam.services import AgentServices
from wcam.sessions.errors import InvalidOfferError

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

    def current_status() -> StatusResponse:
        return status_response(
            manager.status(), services.pipeline, services.cpu.percent, services.comparisons is not None
        )

    def status_json() -> str:
        return current_status().model_dump_json(by_alias=True)

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
        "session ended, the virtual camera, the video format, the agent CPU and, with a reference file, the "
        "measured quality.",
    )
    async def get_status() -> StatusResponse:
        return current_status()

    @router.get(
        "/api/events",
        response_class=StreamingResponse,
        summary="Status events",
        description="Server-sent events with the same JSON as the status, named status: on connecting, on "
        "every change that is not a measurement and every second.",
    )
    async def status_events() -> StreamingResponse:
        return event_stream(repeated_events(services.status_changes, "status", status_json))

    @router.get(
        "/api/dev/events",
        response_class=StreamingResponse,
        summary="Developer console events",
        description="Server-sent events for the developer console: metrics every second and each event as it "
        "happens, starting with the last 50. Detailed timing and the phone statistics run only while someone "
        "listens.",
    )
    async def developer_console_events() -> StreamingResponse:
        dev = services.dev_console
        return event_stream(developer_events(services.dev_events, dev.metrics, services.status_changes))

    @router.put(
        "/api/video-format",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Choose the video format",
        description="Sets the resolution and frame rate for the current session and the next ones until the agent "
        "closes. The format must be one the phone camera offers. The virtual camera announces it when no app is "
        "receiving its video, and the phone follows what the camera announces.",
    )
    async def set_video_format(body: VideoFormatRequest) -> Response:
        manager.set_video_format(body.format)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.patch(
        "/api/controls",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Change the controls",
        description="Freezes the image, turns the phone camera off or on, mirrors the image or switches the phone "
        "camera. Any subset of the fields; freezing, the camera and switching need a live phone. The phone gets the "
        "new controls right after.",
    )
    async def change_controls(body: ControlsRequest) -> Response:
        manager.change_controls(body.to_change())
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.post(
        "/api/preview",
        status_code=status.HTTP_201_CREATED,
        summary="Open the console preview",
        description="Answers a WebRTC offer from the console with a video of what the apps receive, reduced to "
        "960x540 at up to 30 fps, over loopback only. A new preview closes the previous one.",
    )
    async def open_preview(body: PreviewRequest) -> PreviewResponse:
        try:
            return PreviewResponse(sdp=await services.preview.open(body.sdp))
        except ValueError as error:
            raise InvalidOfferError from error

    @router.delete(
        "/api/preview",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Close the console preview",
        description="Closes the preview connection, if any, and stops reducing and encoding frames for it.",
    )
    async def close_preview() -> Response:
        await services.preview.close()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.post(
        "/api/sessions/current/confirm",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Confirm the session",
        description="Marks the code as confirmed on the computer. The phone goes live when it confirmed too.",
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

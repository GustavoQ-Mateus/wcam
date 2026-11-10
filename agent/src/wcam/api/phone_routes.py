from fastapi import APIRouter, Request, status

from wcam.api.health import create_health_router
from wcam.api.schemas import CreateSessionRequest, CreateSessionResponse, create_session_response
from wcam.sessions.device import describe_device, display_convention
from wcam.sessions.manager import SessionManager, SessionRequest

USER_AGENT_HEADER = "user-agent"


def create_phone_router(manager: SessionManager) -> APIRouter:
    router = APIRouter()
    router.include_router(create_health_router("phone"))

    @router.post(
        "/api/sessions",
        status_code=status.HTTP_201_CREATED,
        summary="Start a session",
        description="Consumes the pairing token, answers the WebRTC offer and returns the nonce used to derive "
        "the confirmation code.",
    )
    async def create_session(body: CreateSessionRequest, request: Request) -> CreateSessionResponse:
        client = request.client
        user_agent = request.headers.get(USER_AGENT_HEADER, "")
        session_request = SessionRequest(
            token=body.token,
            offer_sdp=body.sdp,
            remote_ip=client.host if client is not None else "",
            device_name=describe_device(user_agent),
            display=display_convention(user_agent),
        )
        return create_session_response(await manager.create_session(session_request))

    return router

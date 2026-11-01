from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from wcam.media.metrics import VideoStats
from wcam.sessions.manager import LastEnded, SessionOffer, SessionView, Status


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class PairingResponse(CamelModel):
    url: str
    qr_svg: str
    expires_at: str


class PairingBody(CamelModel):
    expires_at: str


class VideoBody(CamelModel):
    width: int
    height: int
    fps: float
    bitrate_kbps: int


class SessionBody(CamelModel):
    id: str
    state: str
    device_name: str | None
    remote_ip: str
    started_at: str
    confirmation_code: str | None
    video: VideoBody | None


class LastEndedBody(CamelModel):
    reason: str
    at: str


class StatusResponse(CamelModel):
    pairing: PairingBody | None
    session: SessionBody | None
    last_ended: LastEndedBody | None


class CreateSessionRequest(CamelModel):
    token: str
    sdp: str


class CreateSessionResponse(CamelModel):
    session_id: str
    sdp: str
    confirmation_nonce: str


def iso_utc(moment: datetime) -> str:
    return moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def status_response(status: Status) -> StatusResponse:
    expires_at = status.pairing_expires_at
    return StatusResponse(
        pairing=None if expires_at is None else PairingBody(expires_at=iso_utc(expires_at)),
        session=None if status.session is None else session_body(status.session),
        last_ended=None if status.last_ended is None else last_ended_body(status.last_ended),
    )


def session_body(session: SessionView) -> SessionBody:
    return SessionBody(
        id=session.id,
        state=session.state,
        device_name=session.device_name,
        remote_ip=session.remote_ip,
        started_at=iso_utc(session.started_at),
        confirmation_code=session.confirmation_code,
        video=None if session.video is None else video_body(session.video),
    )


def video_body(video: VideoStats) -> VideoBody:
    return VideoBody(width=video.width, height=video.height, fps=video.fps, bitrate_kbps=video.bitrate_kbps)


def last_ended_body(last_ended: LastEnded) -> LastEndedBody:
    return LastEndedBody(reason=last_ended.reason, at=iso_utc(last_ended.at))


def create_session_response(offer: SessionOffer) -> CreateSessionResponse:
    return CreateSessionResponse(
        session_id=offer.session_id,
        sdp=offer.answer_sdp,
        confirmation_nonce=offer.confirmation_nonce,
    )

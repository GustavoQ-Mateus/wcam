from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from wcam.media.metrics import VideoStats
from wcam.media.pipeline import FramePipeline
from wcam.media.quality import QualityReport
from wcam.sessions.manager import LastEnded, SessionOffer, SessionView, Status
from wcam.virtualcam.sink import OUTPUT_FPS, OUTPUT_HEIGHT, OUTPUT_WIDTH


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
    codec: str | None
    frames_scaled: int


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


class OutputBody(CamelModel):
    width: int
    height: int
    fps: int


class VirtualCameraBody(CamelModel):
    state: str
    backend: str
    reason: str | None
    output: OutputBody
    source: str


class ProcessBody(CamelModel):
    cpu_percent: float


class QualityBody(CamelModel):
    ssim: float | None
    minimum: float | None
    frames: int


class StatusResponse(CamelModel):
    pairing: PairingBody | None
    session: SessionBody | None
    last_ended: LastEndedBody | None
    virtual_camera: VirtualCameraBody
    process: ProcessBody
    quality: QualityBody | None


class CreateSessionRequest(CamelModel):
    token: str
    sdp: str


class CreateSessionResponse(CamelModel):
    session_id: str
    sdp: str
    confirmation_nonce: str


def iso_utc(moment: datetime) -> str:
    return moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def status_response(status: Status, pipeline: FramePipeline, cpu_percent: float) -> StatusResponse:
    expires_at = status.pairing_expires_at
    quality = pipeline.quality_report
    return StatusResponse(
        pairing=None if expires_at is None else PairingBody(expires_at=iso_utc(expires_at)),
        session=None if status.session is None else session_body(status.session),
        last_ended=None if status.last_ended is None else last_ended_body(status.last_ended),
        virtual_camera=virtual_camera_body(pipeline),
        process=ProcessBody(cpu_percent=cpu_percent),
        quality=None if quality is None else quality_body(quality),
    )


def virtual_camera_body(pipeline: FramePipeline) -> VirtualCameraBody:
    sink_status = pipeline.sink.status
    return VirtualCameraBody(
        state=sink_status.state,
        backend=pipeline.sink.backend,
        reason=sink_status.reason,
        output=OutputBody(width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT, fps=OUTPUT_FPS),
        source=pipeline.source,
    )


def quality_body(quality: QualityReport) -> QualityBody:
    return QualityBody(ssim=quality.ssim, minimum=quality.minimum, frames=quality.frames)


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
    return VideoBody(
        width=video.width,
        height=video.height,
        fps=video.fps,
        bitrate_kbps=video.bitrate_kbps,
        codec=video.codec,
        frames_scaled=video.frames_scaled,
    )


def last_ended_body(last_ended: LastEnded) -> LastEndedBody:
    return LastEndedBody(reason=last_ended.reason, at=iso_utc(last_ended.at))


def create_session_response(offer: SessionOffer) -> CreateSessionResponse:
    return CreateSessionResponse(
        session_id=offer.session_id,
        sdp=offer.answer_sdp,
        confirmation_nonce=offer.confirmation_nonce,
    )

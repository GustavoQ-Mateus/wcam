from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from wcam.media.color_correction import ColorCorrection, CorrectionState, DisplayConvention
from wcam.media.metrics import VideoStats
from wcam.media.pipeline import FramePipeline
from wcam.media.quality import QualityReport
from wcam.media.quality_preset import QualityPreset
from wcam.sessions.manager import LastEnded, SessionOffer, SessionView, Status
from wcam.sessions.phone_messages import CameraCapabilitiesMessage
from wcam.virtualcam.sink import OUTPUT_FPS, OUTPUT_HEIGHT, OUTPUT_WIDTH


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class PairingResponse(CamelModel):
    url: str
    qr_svg: str
    expires_at: str


class PairingBody(CamelModel):
    expires_at: str


class ColorCorrectionBody(CamelModel):
    state: str
    transfer: str | None
    display: str


class VideoBody(CamelModel):
    width: int
    height: int
    fps: float
    bitrate_kbps: int
    codec: str | None
    frames_scaled: int
    color_range: str
    color_matrix: str
    color_correction: ColorCorrectionBody


class CameraColorSpaceBody(CamelModel):
    primaries: str | None
    transfer: str | None
    matrix: str | None
    full_range: bool | None


class CameraCapabilitiesBody(CamelModel):
    width: int | None
    height: int | None
    frame_rate: float | None
    facing_mode: str | None
    codecs: list[str]
    color_space: CameraColorSpaceBody | None


class SessionBody(CamelModel):
    id: str
    state: str
    device_name: str | None
    remote_ip: str
    started_at: str
    confirmation_code: str | None
    video: VideoBody | None
    camera_capabilities: CameraCapabilitiesBody | None


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
    fallback_reason: str | None
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
    quality_preset: QualityPreset
    process: ProcessBody
    quality: QualityBody | None
    dev_tools: bool


class QualityPresetRequest(CamelModel):
    preset: QualityPreset


class CreateSessionRequest(CamelModel):
    token: str
    sdp: str


class CreateSessionResponse(CamelModel):
    session_id: str
    sdp: str
    confirmation_nonce: str


def iso_utc(moment: datetime) -> str:
    return moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def status_response(status: Status, pipeline: FramePipeline, cpu_percent: float, dev_tools: bool) -> StatusResponse:
    expires_at = status.pairing_expires_at
    quality = pipeline.quality_report
    return StatusResponse(
        pairing=None if expires_at is None else PairingBody(expires_at=iso_utc(expires_at)),
        session=None if status.session is None else session_body(status.session),
        last_ended=None if status.last_ended is None else last_ended_body(status.last_ended),
        virtual_camera=virtual_camera_body(pipeline),
        quality_preset=status.quality_preset,
        process=ProcessBody(cpu_percent=cpu_percent),
        quality=None if quality is None else quality_body(quality),
        dev_tools=dev_tools,
    )


def virtual_camera_body(pipeline: FramePipeline) -> VirtualCameraBody:
    sink_status = pipeline.sink.status
    return VirtualCameraBody(
        state=sink_status.state,
        backend=pipeline.sink.backend,
        reason=sink_status.reason,
        fallback_reason=pipeline.fallback_reason,
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
        camera_capabilities=camera_capabilities_body(session.camera_capabilities),
    )


def camera_capabilities_body(capabilities: CameraCapabilitiesMessage | None) -> CameraCapabilitiesBody | None:
    if capabilities is None:
        return None
    return CameraCapabilitiesBody(
        width=capabilities.width,
        height=capabilities.height,
        frame_rate=capabilities.frame_rate,
        facing_mode=capabilities.facing_mode,
        codecs=list(capabilities.codecs),
        color_space=None
        if capabilities.color_space is None
        else CameraColorSpaceBody(
            primaries=capabilities.color_space.primaries,
            transfer=capabilities.color_space.transfer,
            matrix=capabilities.color_space.matrix,
            full_range=capabilities.color_space.full_range,
        ),
    )


def video_body(video: VideoStats) -> VideoBody:
    return VideoBody(
        width=video.width,
        height=video.height,
        fps=video.fps,
        bitrate_kbps=video.bitrate_kbps,
        codec=video.codec,
        frames_scaled=video.frames_scaled,
        color_range=video.color_range,
        color_matrix=video.color_matrix,
        color_correction=color_correction_body(video.color_correction),
    )


def color_correction_body(correction: ColorCorrection | None) -> ColorCorrectionBody:
    if correction is None:
        return ColorCorrectionBody(state=CorrectionState.DEFAULT, transfer=None, display=DisplayConvention.STANDARD)
    return ColorCorrectionBody(state=correction.state, transfer=correction.transfer, display=correction.display)


def last_ended_body(last_ended: LastEnded) -> LastEndedBody:
    return LastEndedBody(reason=last_ended.reason, at=iso_utc(last_ended.at))


def create_session_response(offer: SessionOffer) -> CreateSessionResponse:
    return CreateSessionResponse(
        session_id=offer.session_id,
        sdp=offer.answer_sdp,
        confirmation_nonce=offer.confirmation_nonce,
    )

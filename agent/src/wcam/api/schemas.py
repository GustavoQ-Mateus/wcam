from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from wcam.media.color_correction import ColorCorrection, CorrectionState, DisplayConvention
from wcam.media.metrics import VideoStats
from wcam.media.pipeline import FramePipeline
from wcam.media.quality import QualityReport
from wcam.media.video_format import VideoFormat
from wcam.sessions.controls import Controls, ControlsChange, Facing
from wcam.sessions.manager import LastEnded, SessionOffer, SessionView, Status, VideoFormatState
from wcam.sessions.phone_messages import CameraCapabilitiesMessage, CameraColorSpaceMessage, CameraModesMessage
from wcam.virtualcam.sink import CameraState


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
    orientation: str
    color_range: str
    color_matrix: str
    color_correction: ColorCorrectionBody


class CameraColorSpaceBody(CamelModel):
    primaries: str | None
    transfer: str | None
    matrix: str | None
    full_range: bool | None


class CameraModesBody(CamelModel):
    exposure_mode: str | None
    white_balance_mode: str | None
    focus_mode: str | None


class CameraCapabilitiesBody(CamelModel):
    width: int | None
    height: int | None
    frame_rate: float | None
    facing_mode: str | None
    codecs: list[str]
    color_space: CameraColorSpaceBody | None
    modes: CameraModesBody | None


class ConfirmationsBody(CamelModel):
    pc: bool
    phone: bool


class SessionBody(CamelModel):
    id: str
    state: str
    device_name: str | None
    remote_ip: str
    started_at: str
    confirmation_code: str | None
    confirmations: ConfirmationsBody
    rtp_packets_before_live: int
    video: VideoBody | None
    camera_capabilities: CameraCapabilitiesBody | None


class LastEndedBody(CamelModel):
    reason: str
    at: str
    rtp_packets_before_live: int


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
    streaming_apps: int | None


class VideoFormatBody(CamelModel):
    selected: VideoFormat
    available: list[VideoFormat]
    camera: VideoFormat
    pending: bool


class ProcessBody(CamelModel):
    cpu_percent: float


class QualityBody(CamelModel):
    ssim: float | None
    minimum: float | None
    frames: int


class ControlsBody(CamelModel):
    frozen: bool
    camera_off: bool
    mirror: bool
    facing: Facing | None


class ControlsRequest(CamelModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=False, strict=True, extra="forbid")

    frozen: bool | None = None
    camera_off: bool | None = None
    mirror: bool | None = None
    facing: Facing | None = None

    def to_change(self) -> ControlsChange:
        return ControlsChange(self.frozen, self.camera_off, self.mirror, self.facing)


class StatusResponse(CamelModel):
    pairing: PairingBody | None
    session: SessionBody | None
    last_ended: LastEndedBody | None
    virtual_camera: VirtualCameraBody
    video_format: VideoFormatBody
    process: ProcessBody
    quality: QualityBody | None
    dev_tools: bool
    controls: ControlsBody


class VideoFormatRequest(CamelModel):
    format: VideoFormat


class PreviewRequest(CamelModel):
    sdp: str


class PreviewResponse(CamelModel):
    sdp: str


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
        virtual_camera=virtual_camera_body(pipeline, status.video_format.camera),
        video_format=video_format_body(status.video_format),
        process=ProcessBody(cpu_percent=cpu_percent),
        quality=None if quality is None else quality_body(quality),
        dev_tools=dev_tools,
        controls=controls_body(status.controls),
    )


def controls_body(controls: Controls) -> ControlsBody:
    return ControlsBody(
        frozen=controls.frozen,
        camera_off=controls.camera_off,
        mirror=controls.mirror,
        facing=controls.facing,
    )


def video_format_body(state: VideoFormatState) -> VideoFormatBody:
    return VideoFormatBody(
        selected=state.selected,
        available=list(state.available),
        camera=state.camera,
        pending=state.pending,
    )


def virtual_camera_body(pipeline: FramePipeline, camera_format: VideoFormat) -> VirtualCameraBody:
    sink_status = pipeline.sink.status
    size = camera_format.size
    return VirtualCameraBody(
        state=sink_status.state,
        backend=pipeline.sink.backend,
        reason=sink_status.reason,
        fallback_reason=pipeline.fallback_reason,
        output=OutputBody(width=size.width, height=size.height, fps=size.fps),
        source=pipeline.source,
        streaming_apps=pipeline.output.streaming_apps if sink_status.state is CameraState.ACTIVE else None,
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
        confirmations=ConfirmationsBody(pc=session.confirmations.pc, phone=session.confirmations.phone),
        rtp_packets_before_live=session.rtp_packets_before_live,
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
        color_space=None if capabilities.color_space is None else color_space_body(capabilities.color_space),
        modes=None if capabilities.modes is None else modes_body(capabilities.modes),
    )


def color_space_body(color_space: CameraColorSpaceMessage) -> CameraColorSpaceBody:
    return CameraColorSpaceBody(
        primaries=color_space.primaries,
        transfer=color_space.transfer,
        matrix=color_space.matrix,
        full_range=color_space.full_range,
    )


def modes_body(modes: CameraModesMessage) -> CameraModesBody:
    return CameraModesBody(
        exposure_mode=modes.exposure_mode,
        white_balance_mode=modes.white_balance_mode,
        focus_mode=modes.focus_mode,
    )


def video_body(video: VideoStats) -> VideoBody:
    return VideoBody(
        width=video.width,
        height=video.height,
        fps=video.fps,
        bitrate_kbps=video.bitrate_kbps,
        codec=video.codec,
        frames_scaled=video.frames_scaled,
        orientation=video.orientation,
        color_range=video.color_range,
        color_matrix=video.color_matrix,
        color_correction=color_correction_body(video.color_correction),
    )


def color_correction_body(correction: ColorCorrection | None) -> ColorCorrectionBody:
    if correction is None:
        return ColorCorrectionBody(state=CorrectionState.DEFAULT, transfer=None, display=DisplayConvention.STANDARD)
    return ColorCorrectionBody(state=correction.state, transfer=correction.transfer, display=correction.display)


def last_ended_body(last_ended: LastEnded) -> LastEndedBody:
    return LastEndedBody(
        reason=last_ended.reason,
        at=iso_utc(last_ended.at),
        rtp_packets_before_live=last_ended.rtp_packets_before_live,
    )


def create_session_response(offer: SessionOffer) -> CreateSessionResponse:
    return CreateSessionResponse(
        session_id=offer.session_id,
        sdp=offer.answer_sdp,
        confirmation_nonce=offer.confirmation_nonce,
    )

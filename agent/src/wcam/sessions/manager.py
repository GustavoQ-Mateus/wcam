import asyncio
import logging
import secrets
from collections.abc import Awaitable, Callable, Coroutine, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

from wcam.clock import Clock, utc_now
from wcam.media.color_correction import ColorCorrection, DisplayConvention, color_correction, default_correction
from wcam.media.metrics import VideoStats
from wcam.media.sdp_filter import is_publishable_offer, sha256_fingerprint
from wcam.media.video_format import (
    DEFAULT_VIDEO_FORMAT,
    CameraLimits,
    VideoFormat,
    available_formats,
    format_after_capabilities,
)
from wcam.pairing.attempts import AttemptLimiter
from wcam.pairing.confirmation_code import confirmation_code
from wcam.pairing.errors import PairingTokenExpiredError, PairingTokenInvalidError, PairingWindowClosedError
from wcam.pairing.tokens import PairingTicket, PairingWindow
from wcam.sessions.comparisons import ComparisonNotFoundError, ComparisonStore
from wcam.sessions.errors import (
    InvalidOfferError,
    NoActiveSessionError,
    NoLiveSessionError,
    NoSessionAwaitingConfirmationError,
    SessionAlreadyActiveError,
    TooManyAttemptsError,
    UnavailableVideoFormatError,
)
from wcam.sessions.phone_messages import (
    AnyPhoneMessage,
    CameraCapabilitiesMessage,
    ConfirmCodeMessage,
    RejectCodeMessage,
    ScreenshotBeginMessage,
    ScreenshotChunkMessage,
    SetVideoFormatMessage,
    SnapshotBeginMessage,
    SnapshotChunkMessage,
    parse_phone_message,
)

CONFIRMATION_TIMEOUT_SECONDS = 120.0
ID_BYTES = 16
COUNTED_FAILURES = (PairingTokenInvalidError, PairingTokenExpiredError, PairingWindowClosedError)
IGNORED_PHONE_MESSAGE = "Ignored a phone message outside the contract"
MESSAGE_BEFORE_LIVE = "Ignored a phone message sent before both sides confirmed the code"
CONFIRMATION_AFTER_LIVE = "Ignored a code confirmation from a phone that is already live"
UNAVAILABLE_FORMAT_FROM_PHONE = "Ignored a video format the phone camera does not offer"
PHONE_IMAGE_WITHOUT_DEV_TOOLS = "Ignored a phone image because development tools are off"

type PhoneImageMessage = SnapshotBeginMessage | SnapshotChunkMessage | ScreenshotBeginMessage | ScreenshotChunkMessage
PHONE_IMAGE_MESSAGES = (SnapshotBeginMessage, SnapshotChunkMessage, ScreenshotBeginMessage, ScreenshotChunkMessage)
CONFIRMATION_MESSAGES = (ConfirmCodeMessage, RejectCodeMessage)

logger = logging.getLogger(__name__)


class SessionState(StrEnum):
    CONNECTING = "connecting"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    LIVE = "live"


class EndReason(StrEnum):
    REJECTED = "rejected"
    DISCONNECTED_BY_PC = "disconnected_by_pc"
    DISCONNECTED_BY_PHONE = "disconnected_by_phone"
    CONNECTION_FAILED = "connection_failed"
    CONFIRMATION_TIMEOUT = "confirmation_timeout"


@dataclass(frozen=True, slots=True)
class PeerEvents:
    on_connected: Callable[[], None]
    on_lost: Callable[[EndReason], None]
    on_message: Callable[[str | bytes], None]


class MediaPeer(Protocol):
    @property
    def answer_sdp(self) -> str: ...

    @property
    def video(self) -> VideoStats | None: ...

    @property
    def rtp_packets_before_live(self) -> int: ...

    def open_gate(self) -> None: ...

    def limit_bitrate(self, max_bitrate_bps: int) -> None: ...

    def set_color_correction(self, correction: ColorCorrection) -> None: ...

    def send(self, message: Mapping[str, object]) -> None: ...

    async def close(self) -> None: ...


class FormatCamera(Protocol):
    @property
    def camera_format(self) -> VideoFormat | None: ...

    @property
    def pending(self) -> bool: ...

    def on_change(self, listener: Callable[[], None]) -> None: ...

    def request(self, video_format: VideoFormat) -> None: ...


type PeerFactory = Callable[[str, PeerEvents], Awaitable[MediaPeer]]


@dataclass(frozen=True, slots=True)
class SessionRequest:
    token: str
    offer_sdp: str
    remote_ip: str
    device_name: str | None
    display: DisplayConvention = DisplayConvention.STANDARD


@dataclass(frozen=True, slots=True)
class SessionOffer:
    session_id: str
    answer_sdp: str
    confirmation_nonce: str


@dataclass(frozen=True, slots=True)
class Confirmations:
    pc: bool
    phone: bool


@dataclass(frozen=True, slots=True)
class SessionView:
    id: str
    state: SessionState
    device_name: str | None
    remote_ip: str
    started_at: datetime
    confirmation_code: str | None
    confirmations: Confirmations
    rtp_packets_before_live: int
    video: VideoStats | None
    camera_capabilities: CameraCapabilitiesMessage | None


@dataclass(frozen=True, slots=True)
class LastEnded:
    reason: EndReason
    at: datetime
    rtp_packets_before_live: int


@dataclass(frozen=True, slots=True)
class VideoFormatState:
    selected: VideoFormat
    available: tuple[VideoFormat, ...]
    camera: VideoFormat
    pending: bool


@dataclass(frozen=True, slots=True)
class Status:
    pairing_expires_at: datetime | None
    session: SessionView | None
    last_ended: LastEnded | None
    video_format: VideoFormatState


@dataclass(slots=True)
class Session:
    id: str
    request: SessionRequest
    started_at: datetime
    confirmation_code: str
    peer: MediaPeer
    state: SessionState = SessionState.CONNECTING
    confirmations: Confirmations = Confirmations(pc=False, phone=False)
    camera_capabilities: CameraCapabilitiesMessage | None = None


class SessionManager:
    def __init__(
        self,
        peer_factory: PeerFactory,
        clock: Clock = utc_now,
        confirmation_timeout: float = CONFIRMATION_TIMEOUT_SECONDS,
        comparisons: ComparisonStore | None = None,
        camera: FormatCamera | None = None,
    ) -> None:
        self._peer_factory = peer_factory
        self._comparisons = comparisons
        self._camera = camera
        self._clock = clock
        self._confirmation_timeout = confirmation_timeout
        self._pairing = PairingWindow(clock)
        self._attempts = AttemptLimiter(clock)
        self._session: Session | None = None
        self._creating = False
        self._last_ended: LastEnded | None = None
        self._selected_format = DEFAULT_VIDEO_FORMAT
        self._available_formats = available_formats(None)
        self._confirmation_timer: asyncio.Task[None] | None = None
        self._background: set[asyncio.Task[None]] = set()
        self._change_listeners: list[Callable[[], None]] = []
        if camera is not None:
            camera.on_change(self._send_video_format)

    def on_change(self, listener: Callable[[], None]) -> None:
        self._change_listeners.append(listener)

    def open_pairing(self) -> PairingTicket:
        self._ensure_idle()
        return self._pairing.open()

    def close_pairing(self) -> None:
        self._pairing.close()

    def status(self) -> Status:
        return Status(self._pairing.expires_at, self._view(), self._last_ended, self._video_format_state())

    def set_video_format(self, video_format: VideoFormat) -> None:
        if video_format not in self._available_formats:
            raise UnavailableVideoFormatError
        self._select_format(video_format)

    def start_comparison(self) -> str:
        session = self._session
        comparisons = self._comparisons
        if comparisons is None:
            raise ComparisonNotFoundError
        if session is None or session.state is not SessionState.LIVE:
            raise NoLiveSessionError
        comparison = comparisons.create()
        session.peer.send(snapshot_request_message(comparison.id))
        return comparison.id

    async def create_session(self, request: SessionRequest) -> SessionOffer:
        if self._attempts.is_blocked(request.remote_ip):
            raise TooManyAttemptsError
        self._ensure_idle()
        phone_fingerprint = sha256_fingerprint(request.offer_sdp)
        if phone_fingerprint is None or not is_publishable_offer(request.offer_sdp):
            raise InvalidOfferError
        self._consume_token(request)
        self._creating = True
        try:
            return await self._start_session(request, phone_fingerprint)
        finally:
            self._creating = False

    def confirm(self) -> None:
        session = self._awaiting_session()
        self._record_confirmation(session, replace(session.confirmations, pc=True))

    async def reject(self) -> None:
        await self._end(self._awaiting_session(), EndReason.REJECTED)

    async def disconnect(self) -> None:
        if self._session is None:
            raise NoActiveSessionError
        await self._end(self._session, EndReason.DISCONNECTED_BY_PC)

    async def shutdown(self) -> None:
        if self._session is not None:
            await self._end(self._session, EndReason.DISCONNECTED_BY_PC)
        for task in list(self._background):
            task.cancel()
        await asyncio.gather(*self._background, return_exceptions=True)

    def _ensure_idle(self) -> None:
        if self._session is not None or self._creating:
            raise SessionAlreadyActiveError

    def _consume_token(self, request: SessionRequest) -> None:
        try:
            self._pairing.consume(request.token)
        except COUNTED_FAILURES:
            self._attempts.record_failure(request.remote_ip)
            raise

    async def _start_session(self, request: SessionRequest, phone_fingerprint: str) -> SessionOffer:
        nonce = secrets.token_hex(ID_BYTES)
        sessions: list[Session] = []
        events = PeerEvents(
            on_connected=lambda: self._handle_connected(sessions),
            on_lost=lambda reason: self._handle_lost(sessions, reason),
            on_message=lambda data: self._handle_message(sessions, data),
        )
        try:
            peer = await self._peer_factory(request.offer_sdp, events)
        except ValueError as error:
            raise InvalidOfferError from error
        peer.limit_bitrate(self._phone_format().size.max_bitrate_bps)
        peer.set_color_correction(default_correction(request.display))
        agent_fingerprint = sha256_fingerprint(peer.answer_sdp) or ""
        code = confirmation_code(nonce, phone_fingerprint, agent_fingerprint)
        session = Session(secrets.token_hex(ID_BYTES), request, self._clock(), code, peer)
        sessions.append(session)
        self._session = session
        return SessionOffer(session.id, peer.answer_sdp, nonce)

    def _handle_connected(self, sessions: list[Session]) -> None:
        session = self._current(sessions)
        if session is None or session.state is not SessionState.CONNECTING:
            return
        session.state = SessionState.AWAITING_CONFIRMATION
        session.peer.send(state_message(SessionState.AWAITING_CONFIRMATION))
        session.peer.send(confirmation_message(session.confirmations))
        self._confirmation_timer = asyncio.get_running_loop().create_task(self._expire_confirmation(session))
        self._notify_change()

    def _handle_lost(self, sessions: list[Session], reason: EndReason) -> None:
        session = self._current(sessions)
        if session is not None:
            self._run_in_background(self._end(session, reason))

    def _handle_message(self, sessions: list[Session], data: str | bytes) -> None:
        session = self._current(sessions)
        if session is None:
            return
        message = parse_phone_message(data)
        if session.state is not SessionState.LIVE:
            self._handle_message_before_live(session, message)
        elif isinstance(message, CONFIRMATION_MESSAGES):
            logger.warning(CONFIRMATION_AFTER_LIVE)
        elif isinstance(message, CameraCapabilitiesMessage):
            self._receive_capabilities(session, message)
        elif isinstance(message, PHONE_IMAGE_MESSAGES):
            self._receive_phone_image(message)
        elif isinstance(message, SetVideoFormatMessage):
            self._apply_phone_format(message.format)
        else:
            logger.warning(IGNORED_PHONE_MESSAGE)

    def _handle_message_before_live(self, session: Session, message: AnyPhoneMessage | None) -> None:
        if isinstance(message, ConfirmCodeMessage) and session.state is SessionState.AWAITING_CONFIRMATION:
            self._record_confirmation(session, replace(session.confirmations, phone=True))
        elif isinstance(message, RejectCodeMessage):
            self._run_in_background(self._end(session, EndReason.REJECTED))
        else:
            logger.warning(MESSAGE_BEFORE_LIVE)

    def _record_confirmation(self, session: Session, confirmations: Confirmations) -> None:
        if confirmations == session.confirmations:
            return
        session.confirmations = confirmations
        if confirmations.pc and confirmations.phone:
            self._go_live(session)
            return
        session.peer.send(confirmation_message(confirmations))

    def _go_live(self, session: Session) -> None:
        self._cancel_confirmation_timer()
        session.state = SessionState.LIVE
        session.peer.open_gate()
        session.peer.send(state_message(SessionState.LIVE))
        self._send_video_format()

    def _receive_capabilities(self, session: Session, message: CameraCapabilitiesMessage) -> None:
        session.camera_capabilities = message
        session.peer.set_color_correction(color_correction(message.camera_color_space(), session.request.display))
        self._available_formats = available_formats(CameraLimits(message.width, message.height, message.frame_rate))
        following = format_after_capabilities(self._selected_format, self._available_formats)
        if following is not self._selected_format:
            self._select_format(following)
        self._send_video_format()

    def _apply_phone_format(self, video_format: VideoFormat) -> None:
        if video_format not in self._available_formats:
            logger.warning(UNAVAILABLE_FORMAT_FROM_PHONE)
            self._send_video_format()
            return
        self._select_format(video_format)

    def _select_format(self, video_format: VideoFormat) -> None:
        self._selected_format = video_format
        if self._camera is None:
            self._send_video_format()
            return
        self._camera.request(video_format)

    def _phone_format(self) -> VideoFormat:
        camera_format = None if self._camera is None else self._camera.camera_format
        return camera_format or self._selected_format

    def _send_video_format(self) -> None:
        session = self._session
        if session is None:
            return
        phone_format = self._phone_format()
        session.peer.limit_bitrate(phone_format.size.max_bitrate_bps)
        if session.state is SessionState.LIVE:
            session.peer.send(video_format_message(phone_format, self._available_formats))

    def _video_format_state(self) -> VideoFormatState:
        pending = self._camera is not None and self._camera.pending
        return VideoFormatState(self._selected_format, self._available_formats, self._phone_format(), pending)

    def _receive_phone_image(self, message: PhoneImageMessage) -> None:
        comparisons = self._comparisons
        if comparisons is None:
            logger.warning(PHONE_IMAGE_WITHOUT_DEV_TOOLS)
            return
        if isinstance(message, SnapshotBeginMessage):
            comparisons.receive_begin(message)
        elif isinstance(message, SnapshotChunkMessage):
            comparisons.receive_chunk(message)
        elif isinstance(message, ScreenshotBeginMessage):
            comparisons.receive_screenshot_begin(message)
        else:
            comparisons.receive_screenshot_chunk(message)

    def _current(self, sessions: list[Session]) -> Session | None:
        return next((session for session in sessions if session is self._session), None)

    async def _expire_confirmation(self, session: Session) -> None:
        await asyncio.sleep(self._confirmation_timeout)
        self._confirmation_timer = None
        await self._end(session, EndReason.CONFIRMATION_TIMEOUT)

    async def _end(self, session: Session, reason: EndReason) -> None:
        if session is not self._session:
            return
        self._session = None
        self._cancel_confirmation_timer()
        self._last_ended = LastEnded(reason, self._clock(), session.peer.rtp_packets_before_live)
        if self._comparisons is not None:
            self._comparisons.end_session()
        session.peer.send({"type": "session_state", "state": "ended", "reason": reason})
        await session.peer.close()

    def _awaiting_session(self) -> Session:
        session = self._session
        if session is None or session.state is not SessionState.AWAITING_CONFIRMATION:
            raise NoSessionAwaitingConfirmationError
        return session

    def _cancel_confirmation_timer(self) -> None:
        timer = self._confirmation_timer
        self._confirmation_timer = None
        if timer is not None and timer is not asyncio.current_task():
            timer.cancel()

    def _notify_change(self) -> None:
        for listener in self._change_listeners:
            listener()

    def _run_in_background(self, work: Coroutine[Any, Any, None]) -> None:
        task = asyncio.get_running_loop().create_task(work)
        self._background.add(task)
        task.add_done_callback(self._background.discard)

    def _view(self) -> SessionView | None:
        session = self._session
        if session is None:
            return None
        code = None if session.state is SessionState.CONNECTING else session.confirmation_code
        return SessionView(
            session.id,
            session.state,
            session.request.device_name,
            session.request.remote_ip,
            session.started_at,
            code,
            session.confirmations,
            session.peer.rtp_packets_before_live,
            session.peer.video,
            session.camera_capabilities,
        )


def state_message(state: SessionState) -> dict[str, str]:
    return {"type": "session_state", "state": state}


def confirmation_message(confirmations: Confirmations) -> dict[str, object]:
    return {"type": "confirmation", "pc": confirmations.pc, "phone": confirmations.phone}


def snapshot_request_message(comparison_id: str) -> dict[str, str]:
    return {"type": "snapshot_request", "id": comparison_id}


def video_format_message(video_format: VideoFormat, available: tuple[VideoFormat, ...]) -> dict[str, object]:
    size = video_format.size
    return {
        "type": "video_format",
        "format": video_format,
        "width": size.width,
        "height": size.height,
        "fps": size.fps,
        "maxBitrate": size.max_bitrate_bps,
        "available": list(available),
    }

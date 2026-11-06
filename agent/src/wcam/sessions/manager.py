import asyncio
import logging
import secrets
from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

from wcam.clock import Clock, utc_now
from wcam.media.color_calibration import ColorSample
from wcam.media.metrics import VideoStats
from wcam.media.quality_preset import DEFAULT_QUALITY_PRESET, QualityPreset
from wcam.media.sdp_filter import is_publishable_offer, sha256_fingerprint
from wcam.pairing.attempts import AttemptLimiter
from wcam.pairing.confirmation_code import confirmation_code
from wcam.pairing.errors import PairingTokenExpiredError, PairingTokenInvalidError, PairingWindowClosedError
from wcam.pairing.tokens import PairingTicket, PairingWindow
from wcam.sessions.errors import (
    InvalidOfferError,
    NoActiveSessionError,
    NoSessionAwaitingConfirmationError,
    SessionAlreadyActiveError,
    TooManyAttemptsError,
)
from wcam.sessions.phone_messages import (
    CameraCapabilitiesMessage,
    ColorSampleMessage,
    SetQualityPresetMessage,
    parse_phone_message,
)

CONFIRMATION_TIMEOUT_SECONDS = 120.0
ID_BYTES = 16
COUNTED_FAILURES = (PairingTokenInvalidError, PairingTokenExpiredError, PairingWindowClosedError)
IGNORED_PHONE_MESSAGE = "Ignored a phone message outside the contract"
PRESET_BEFORE_LIVE = "Ignored a quality preset change from a phone that is not live yet"
COLOR_SAMPLE_BEFORE_LIVE = "Ignored a color sample from a phone that is not live yet"

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

    def open_gate(self) -> None: ...

    def limit_bitrate(self, max_bitrate_bps: int) -> None: ...

    def add_color_sample(self, sample: ColorSample) -> None: ...

    def restart_color_calibration(self) -> None: ...

    def send(self, message: dict[str, str]) -> None: ...

    async def close(self) -> None: ...


type PeerFactory = Callable[[str, PeerEvents], Awaitable[MediaPeer]]


@dataclass(frozen=True, slots=True)
class SessionRequest:
    token: str
    offer_sdp: str
    remote_ip: str
    device_name: str | None


@dataclass(frozen=True, slots=True)
class SessionOffer:
    session_id: str
    answer_sdp: str
    confirmation_nonce: str


@dataclass(frozen=True, slots=True)
class SessionView:
    id: str
    state: SessionState
    device_name: str | None
    remote_ip: str
    started_at: datetime
    confirmation_code: str | None
    video: VideoStats | None
    camera_capabilities: CameraCapabilitiesMessage | None


@dataclass(frozen=True, slots=True)
class LastEnded:
    reason: EndReason
    at: datetime


@dataclass(frozen=True, slots=True)
class Status:
    pairing_expires_at: datetime | None
    session: SessionView | None
    last_ended: LastEnded | None
    quality_preset: QualityPreset


@dataclass(slots=True)
class Session:
    id: str
    request: SessionRequest
    started_at: datetime
    confirmation_code: str
    peer: MediaPeer
    state: SessionState = SessionState.CONNECTING
    camera_capabilities: CameraCapabilitiesMessage | None = None


class SessionManager:
    def __init__(
        self,
        peer_factory: PeerFactory,
        clock: Clock = utc_now,
        confirmation_timeout: float = CONFIRMATION_TIMEOUT_SECONDS,
    ) -> None:
        self._peer_factory = peer_factory
        self._clock = clock
        self._confirmation_timeout = confirmation_timeout
        self._pairing = PairingWindow(clock)
        self._attempts = AttemptLimiter(clock)
        self._session: Session | None = None
        self._creating = False
        self._last_ended: LastEnded | None = None
        self._quality_preset = DEFAULT_QUALITY_PRESET
        self._confirmation_timer: asyncio.Task[None] | None = None
        self._background: set[asyncio.Task[None]] = set()

    def open_pairing(self) -> PairingTicket:
        self._ensure_idle()
        return self._pairing.open()

    def close_pairing(self) -> None:
        self._pairing.close()

    def status(self) -> Status:
        return Status(self._pairing.expires_at, self._view(), self._last_ended, self._quality_preset)

    def set_quality_preset(self, preset: QualityPreset) -> None:
        self._quality_preset = preset
        if self._session is not None:
            self._session.peer.limit_bitrate(preset.max_bitrate_bps)
            self._session.peer.send(quality_preset_message(preset))

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
        self._cancel_confirmation_timer()
        session.state = SessionState.LIVE
        session.peer.open_gate()
        session.peer.send(state_message(SessionState.LIVE))

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
        peer.limit_bitrate(self._quality_preset.max_bitrate_bps)
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
        session.peer.send(quality_preset_message(self._quality_preset))
        self._confirmation_timer = asyncio.get_running_loop().create_task(self._expire_confirmation(session))

    def _handle_lost(self, sessions: list[Session], reason: EndReason) -> None:
        session = self._current(sessions)
        if session is not None:
            self._run_in_background(self._end(session, reason))

    def _handle_message(self, sessions: list[Session], data: str | bytes) -> None:
        session = self._current(sessions)
        if session is None:
            return
        message = parse_phone_message(data)
        if isinstance(message, CameraCapabilitiesMessage):
            session.camera_capabilities = message
            session.peer.restart_color_calibration()
        elif isinstance(message, ColorSampleMessage):
            self._apply_color_sample(session, message)
        elif isinstance(message, SetQualityPresetMessage):
            self._apply_phone_preset(session, message.preset)
        else:
            logger.warning(IGNORED_PHONE_MESSAGE)

    def _apply_phone_preset(self, session: Session, preset: QualityPreset) -> None:
        if session.state is not SessionState.LIVE:
            logger.warning(PRESET_BEFORE_LIVE)
            return
        self.set_quality_preset(preset)

    def _apply_color_sample(self, session: Session, message: ColorSampleMessage) -> None:
        if session.state is not SessionState.LIVE:
            logger.warning(COLOR_SAMPLE_BEFORE_LIVE)
            return
        session.peer.add_color_sample(message.to_sample())

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
        self._last_ended = LastEnded(reason, self._clock())
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
            session.peer.video,
            session.camera_capabilities,
        )


def state_message(state: SessionState) -> dict[str, str]:
    return {"type": "session_state", "state": state}


def quality_preset_message(preset: QualityPreset) -> dict[str, str]:
    return {"type": "quality_preset", "preset": preset}

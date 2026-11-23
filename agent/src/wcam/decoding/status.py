import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum


class DecoderKind(StrEnum):
    HARDWARE = "hardware"
    SOFTWARE = "software"


class FallbackReason(StrEnum):
    UNSUPPORTED = "unsupported"
    OPEN_FAILED = "open_failed"
    STREAM_ERROR = "stream_error"
    DISABLED = "disabled"
    LIVE_PHONE = "live_phone"


class DecodingSource(StrEnum):
    PHONE = "phone"
    VIDEO = "video"


@dataclass(frozen=True, slots=True)
class DecoderChange:
    source: DecodingSource
    decoder: DecoderKind
    reason: FallbackReason | None


type DecoderListener = Callable[[DecoderChange], None]
type StatusListener = Callable[[], None]


class DecoderStatus:
    def __init__(self, source: DecodingSource) -> None:
        self.source = source
        self._lock = threading.Lock()
        self._decoder: DecoderKind | None = None
        self._change_listeners: list[DecoderListener] = []
        self._clear_listeners: list[StatusListener] = []

    @property
    def decoder(self) -> DecoderKind | None:
        return self._decoder

    def on_change(self, listener: DecoderListener) -> None:
        self._change_listeners.append(listener)

    def on_clear(self, listener: StatusListener) -> None:
        self._clear_listeners.append(listener)

    def report(self, decoder: DecoderKind, reason: FallbackReason | None) -> None:
        with self._lock:
            if decoder is self._decoder:
                return
            self._decoder = decoder
        change = DecoderChange(self.source, decoder, reason)
        for listener in self._change_listeners:
            listener(change)

    def clear(self) -> None:
        with self._lock:
            if self._decoder is None:
                return
            self._decoder = None
        for listener in self._clear_listeners:
            listener()

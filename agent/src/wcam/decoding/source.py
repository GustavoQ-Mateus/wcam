import threading
from collections.abc import Callable
from typing import Literal

from wcam.decoding.hardware import HardwareDecoder, HardwareStream
from wcam.decoding.status import DecoderStatus, DecodingSource, FallbackReason

type HardwareDecodeMode = Literal["auto", "on", "off"]
type HardwareFactory = Callable[[], HardwareDecoder]


class SourceDecoding:
    def __init__(
        self,
        mode: HardwareDecodeMode,
        status: DecoderStatus,
        start_hardware: HardwareFactory,
        *,
        live: bool = False,
    ) -> None:
        self.status = status
        self._software_reason = software_reason(mode, live=live)
        self._start_hardware = start_hardware
        self._lock = threading.Lock()
        self._hardware: HardwareDecoder | None = None

    def start(self) -> None:
        with self._lock:
            if self._software_reason is not None or self._hardware is not None:
                return
            self._hardware = self._start_hardware()

    def open(self, codec: str, extradata: bytes | None) -> HardwareStream | FallbackReason:
        if self._software_reason is not None:
            return self._software_reason
        with self._lock:
            hardware = self._hardware
        if hardware is None:
            return FallbackReason.OPEN_FAILED
        return hardware.open(codec, extradata)

    def stop(self) -> None:
        with self._lock:
            hardware, self._hardware = self._hardware, None
        if hardware is not None:
            hardware.close()
        self.status.clear()


def software_reason(mode: HardwareDecodeMode, *, live: bool) -> FallbackReason | None:
    if mode == "off":
        return FallbackReason.DISABLED
    if mode == "auto" and live:
        return FallbackReason.LIVE_PHONE
    return None


def software_decoding(source: DecodingSource) -> SourceDecoding:
    return SourceDecoding("off", DecoderStatus(source), unused_hardware)


def unused_hardware() -> HardwareDecoder:
    raise RuntimeError("software decoding never starts the hardware decoder")

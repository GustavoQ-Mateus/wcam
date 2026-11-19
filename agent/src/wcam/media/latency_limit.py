import time
from collections.abc import Callable

RTP_CLOCK_RATE = 90_000
RTP_TIMESTAMP_MODULUS = 1 << 32
MAX_LAG_SECONDS = 0.2
CLOCK_DRIFT_ALLOWANCE = 0.001

type Clock = Callable[[], float]


class LatencyLimit:
    def __init__(self, request_keyframe: Callable[[], None], clock: Clock = time.monotonic) -> None:
        self._request_keyframe = request_keyframe
        self._clock = clock
        self._last_timestamp: int | None = None
        self._media_seconds = 0.0
        self._baseline: float | None = None
        self._baseline_at = 0.0
        self._skipping = False

    def admits(self, timestamp: int, keyframe: bool) -> bool:
        now = self._clock()
        self._advance_media_clock(timestamp)
        offset = now - self._media_seconds
        if keyframe:
            if self._skipping or self._baseline is None:
                self._skipping = False
                self._anchor(offset, now)
            return True
        if self._skipping:
            return False
        if self._lag(offset, now) <= MAX_LAG_SECONDS:
            return True
        self._skipping = True
        self._request_keyframe()
        return False

    def _lag(self, offset: float, now: float) -> float:
        if self._baseline is None:
            self._anchor(offset, now)
            return 0.0
        allowed = self._baseline + CLOCK_DRIFT_ALLOWANCE * (now - self._baseline_at)
        if offset < allowed:
            self._anchor(offset, now)
            return 0.0
        return offset - allowed

    def _anchor(self, offset: float, now: float) -> None:
        self._baseline, self._baseline_at = offset, now

    def _advance_media_clock(self, timestamp: int) -> None:
        if self._last_timestamp is not None:
            step = (timestamp - self._last_timestamp) % RTP_TIMESTAMP_MODULUS
            if step >= RTP_TIMESTAMP_MODULUS // 2:
                step -= RTP_TIMESTAMP_MODULUS
            self._media_seconds += step / RTP_CLOCK_RATE
        self._last_timestamp = timestamp

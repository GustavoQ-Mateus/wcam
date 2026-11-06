import asyncio
import time
from collections import deque
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import StrEnum

from wcam.media.color_calibration import (
    CalibrationResult,
    ColorCorrection,
    ColorSample,
    ReducedFrame,
    SampleMatch,
    applied_tables,
    best_match,
    fit_correction,
    range_tables,
    reduced_frame,
)
from wcam.media.color_range import ColorRange
from wcam.media.color_trace import ColorTrace, TracedSample
from wcam.virtualcam.sink import I420Frame

SAMPLES_PER_MEASUREMENT = 5
MIN_VALID_SAMPLES = 3
MATCH_DELAY_SECONDS = 0.7
RING_FRAMES = 60
COLLECT_SECONDS = 30.0
DELTA_E_DIGITS = 2
MILLISECONDS = 1000
WORKER_NAME = "wcam-color"


class CalibrationState(StrEnum):
    MEASURING = "measuring"
    APPLIED = "applied"
    DEFAULT = "default"


@dataclass(frozen=True, slots=True)
class CalibrationStatus:
    state: CalibrationState
    delta_e: float | None


MEASURING = CalibrationStatus(CalibrationState.MEASURING, None)


class ColorCalibrator:
    def __init__(
        self,
        trace: ColorTrace | None = None,
        match_delay: float = MATCH_DELAY_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], float] = time.time,
    ) -> None:
        self._trace = trace
        self._match_delay = match_delay
        self._clock = clock
        self._wall_clock = wall_clock
        self._ring: deque[ReducedFrame] = deque(maxlen=RING_FRAMES)
        self._worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix=WORKER_NAME)
        self._tasks: set[asyncio.Task[None]] = set()
        self._matches: list[SampleMatch] = []
        self._received = 0
        self._unmatched = 0
        self._generation = 0
        self._collect_until = clock() + COLLECT_SECONDS
        self._color_range = ColorRange.UNSPECIFIED
        self.correction: ColorCorrection | None = None
        self.status = MEASURING

    @property
    def collecting(self) -> bool:
        wanted = self._received < SAMPLES_PER_MEASUREMENT or self._unmatched > 0
        return wanted and self._clock() < self._collect_until

    def restart(self) -> None:
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()
        self._ring.clear()
        self._matches = []
        self._received = 0
        self._unmatched = 0
        self._generation += 1
        self._collect_until = self._clock() + COLLECT_SECONDS
        self.correction = None
        self.status = MEASURING

    def close(self) -> None:
        self.restart()
        self._worker.shutdown(wait=True)

    def remember(self, planes: tuple[I420Frame, I420Frame, I420Frame], color_range: ColorRange) -> None:
        self._color_range = color_range
        if self.collecting:
            self._ring.append(reduced_frame(planes, color_range))

    def add_sample(self, sample: ColorSample) -> None:
        self._received += 1
        self._unmatched += 1
        self._collect_until = max(self._collect_until, self._clock() + COLLECT_SECONDS)
        traced = TracedSample(sample, self._wall_clock() * MILLISECONDS, self.status.state.value, None)
        task = asyncio.get_running_loop().create_task(self._measure(traced, self._generation))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _measure(self, traced: TracedSample, generation: int) -> None:
        await asyncio.sleep(self._match_delay)
        loop = asyncio.get_running_loop()
        match = await loop.run_in_executor(self._worker, best_match, tuple(self._ring), traced.sample)
        if generation != self._generation:
            return
        self._unmatched -= 1
        self._record(TracedSample(traced.sample, traced.received_at_ms, traced.state, match))
        if match is not None and match.accepted:
            self._matches.append(match)
        if self._unmatched > 0:
            return
        if len(self._matches) >= MIN_VALID_SAMPLES:
            result = await loop.run_in_executor(self._worker, fit_correction, tuple(self._matches))
            if generation == self._generation:
                self._apply(result)
            return
        if self._received >= SAMPLES_PER_MEASUREMENT:
            self._apply(None)

    def _apply(self, result: CalibrationResult | None) -> None:
        self.correction = None if result is None else result.correction
        state = CalibrationState.DEFAULT if self.correction is None else CalibrationState.APPLIED
        delta_e = None if result is None else round(result.delta_e, DELTA_E_DIGITS)
        self.status = CalibrationStatus(state, delta_e)
        if self._trace is not None:
            self._worker.submit(
                self._trace.record_calibration,
                state.value,
                delta_e,
                range_tables(self._color_range),
                applied_tables(self.correction, self._color_range),
            )

    def _record(self, traced: TracedSample) -> None:
        if self._trace is not None:
            self._worker.submit(self._trace.record_sample, traced)

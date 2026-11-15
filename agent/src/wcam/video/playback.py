import asyncio
import time
from collections.abc import Awaitable, Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import av
from av import VideoFrame
from av.container import InputContainer
from av.video.stream import VideoStream

from wcam.diagnostics.stage_times import Stage
from wcam.media.pipeline import elapsed_since
from wcam.video.frames import fitted_i420
from wcam.virtualcam.sink import AnnouncedFormat, I420Frame

WORKER_NAME = "wcam-video"
STREAM_THREADING = "AUTO"
TIME_TOLERANCE_SECONDS = 1e-6

type Sleep = Callable[[float], Awaitable[None]]


async def precise_sleep(seconds: float) -> None:
    # asyncio timers on Windows wake in steps of about 15.6 ms; time.sleep uses a high resolution timer.
    await asyncio.to_thread(time.sleep, max(seconds, 0.0))


def following_tick(tick: float, period: float, now: float) -> float:
    following = tick + period
    return now if following < now - period else following


class VideoOutput(Protocol):
    @property
    def output(self) -> AnnouncedFormat: ...

    @property
    def frozen(self) -> bool: ...

    def submit_video(self, image: I420Frame, *, replace_held: bool = False) -> None: ...

    def record_stage(self, stage: Stage, milliseconds: float) -> None: ...


@dataclass(frozen=True, slots=True)
class VideoImage:
    seconds: float
    image: I420Frame
    decode_milliseconds: float
    convert_milliseconds: float


class LoopingDecoder:
    def __init__(self, path: Path) -> None:
        self._container: InputContainer = av.open(str(path))
        self._stream: VideoStream = self._container.streams.video[0]
        self._stream.thread_type = STREAM_THREADING
        self._start = self._stream.start_time or 0
        self._frames: Iterator[VideoFrame] = self._container.decode(self._stream)
        self._current: VideoFrame | None = None
        self._upcoming: VideoFrame | None = None
        self._image: tuple[VideoFrame, int, int, I420Frame] | None = None
        self._requested = 0.0

    def frame_at(self, seconds: float, width: int, height: int) -> VideoImage:
        started = time.perf_counter()
        if seconds < self._requested - TIME_TOLERANCE_SECONDS:
            self._seek(0.0)
        self._advance_to(seconds)
        return self._converted(width, height, elapsed_since(started))

    def seek(self, seconds: float, width: int, height: int) -> VideoImage:
        started = time.perf_counter()
        self._seek(seconds)
        self._advance_to(seconds)
        return self._converted(width, height, elapsed_since(started))

    def close(self) -> None:
        self._container.close()

    def _seek(self, seconds: float) -> None:
        offset = self._start + round(seconds / self._time_base())
        self._container.seek(offset, stream=self._stream, backward=True, any_frame=False)
        self._frames = self._container.decode(self._stream)
        self._current = None
        self._upcoming = None

    def _advance_to(self, seconds: float) -> None:
        self._requested = seconds
        if self._upcoming is None:
            self._upcoming = self._next()
        while self._upcoming is not None and (
            self._current is None or self._seconds(self._upcoming) <= seconds + TIME_TOLERANCE_SECONDS
        ):
            self._current, self._upcoming = self._upcoming, self._next()

    def _next(self) -> VideoFrame | None:
        return next(self._frames, None)

    def _converted(self, width: int, height: int, decode_milliseconds: float) -> VideoImage:
        frame = self._current
        if frame is None:
            raise EOFError
        started = time.perf_counter()
        cached = self._image
        if cached is None or cached[0] is not frame or cached[1:3] != (width, height):
            cached = (frame, width, height, fitted_i420(frame, width, height))
            self._image = cached
        return VideoImage(self._seconds(frame), cached[3], decode_milliseconds, elapsed_since(started))

    def _seconds(self, frame: VideoFrame) -> float:
        pts = frame.pts if frame.pts is not None else self._start
        return max(0.0, float((pts - self._start) * self._time_base()))

    def _time_base(self) -> float:
        time_base = self._stream.time_base
        return 0.0 if time_base is None else float(time_base)


class VideoPlayback:
    def __init__(
        self,
        path: Path,
        duration_seconds: float,
        output: VideoOutput,
        clock: Callable[[], float] = time.monotonic,
        sleep: Sleep = precise_sleep,
    ) -> None:
        self._path = path
        self._duration = duration_seconds
        self._output = output
        self._clock = clock
        self._sleep = sleep
        self._position: float | None = None
        self._seek_to: float | None = None

    @property
    def position_seconds(self) -> float | None:
        return self._position

    def seek(self, seconds: float) -> None:
        self._seek_to = seconds

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix=WORKER_NAME)
        decoder = await loop.run_in_executor(worker, LoopingDecoder, self._path)
        try:
            await self._play(decoder, worker)
        finally:
            await loop.run_in_executor(worker, decoder.close)
            worker.shutdown(wait=False)

    async def _play(self, decoder: LoopingDecoder, worker: ThreadPoolExecutor) -> None:
        loop = asyncio.get_running_loop()
        media_time = 0.0
        previous = self._clock()
        next_tick = previous
        while True:
            now = self._clock()
            if not self._output.frozen:
                media_time = (media_time + now - previous) % self._duration
            previous = now
            seek_to, self._seek_to = self._seek_to, None
            output = self._output.output
            if seek_to is not None:
                shown = await loop.run_in_executor(worker, decoder.seek, seek_to, output.width, output.height)
                media_time, previous = seek_to, self._clock()
                self._show(shown, replace_held=True)
            elif not self._output.frozen:
                shown = await loop.run_in_executor(worker, decoder.frame_at, media_time, output.width, output.height)
                self._show(shown, replace_held=False)
            next_tick = following_tick(next_tick, 1 / output.fps, self._clock())
            await self._sleep(next_tick - self._clock())

    def _show(self, shown: VideoImage, *, replace_held: bool) -> None:
        self._output.record_stage(Stage.DECODE, shown.decode_milliseconds)
        self._output.record_stage(Stage.COLOR, shown.convert_milliseconds)
        self._position = shown.seconds
        self._output.submit_video(shown.image, replace_held=replace_held)

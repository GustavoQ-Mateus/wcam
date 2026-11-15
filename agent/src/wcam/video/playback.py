import asyncio
import contextlib
import math
import threading
import time
from collections import deque
from collections.abc import Awaitable, Callable, Iterator, Mapping
from concurrent.futures import Future, ThreadPoolExecutor
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
from wcam.video.timeline import Clip, Timeline
from wcam.virtualcam.sink import AnnouncedFormat, I420Frame

PRODUCER_NAME = "wcam-video"
PREPARER_NAME = "wcam-video-next"
STREAM_THREADING = "AUTO"
READ_AHEAD_FRAMES = 4
LATE_JUMP_SECONDS = 0.5
EMIT_SHARE_OF_PERIOD = 0.75
NEAREST_FRAME_SHARE = 0.5
MAX_FRAMES_BEHIND = 2
TIME_TOLERANCE_SECONDS = 1e-6
SETTLE_TIMEOUT_SECONDS = 10.0

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
class PlayRequest:
    generation: int
    timeline: Timeline
    paths: Mapping[str, Path]
    start_seconds: float


@dataclass(frozen=True, slots=True)
class TimelineFrame:
    generation: int
    play_seconds: float
    image: I420Frame
    decode_milliseconds: float
    convert_milliseconds: float


class ReadAhead:
    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._frames: deque[TimelineFrame] = deque()
        self._condition = threading.Condition()
        self._request: PlayRequest | None = None
        self._idle = True
        self._stopped = False

    def restart(self, timeline: Timeline, paths: Mapping[str, Path], start_seconds: float) -> PlayRequest:
        with self._condition:
            generation = 0 if self._request is None else self._request.generation + 1
            self._request = PlayRequest(generation, timeline, paths, start_seconds)
            self._idle = False
            self._frames.clear()
            self._condition.notify_all()
            return self._request

    def stop(self) -> None:
        with self._condition:
            self._stopped = True
            self._frames.clear()
            self._condition.notify_all()

    def is_empty(self) -> bool:
        with self._condition:
            return not self._frames

    def is_current(self, generation: int) -> bool:
        with self._condition:
            return self._current(generation)

    def next_request(self, after: int | None) -> PlayRequest | None:
        with self._condition:
            self._idle = True
            self._condition.notify_all()
            self._condition.wait_for(lambda: self._stopped or self._has_request_after(after))
            self._idle = False
            return None if self._stopped else self._request

    def put(self, frame: TimelineFrame) -> None:
        with self._condition:
            self._condition.wait_for(lambda: not self._current(frame.generation) or len(self._frames) < self._capacity)
            if self._current(frame.generation):
                self._frames.append(frame)
                self._condition.notify_all()

    def take_first(self) -> TimelineFrame | None:
        with self._condition:
            if not self._frames:
                return None
            self._condition.notify_all()
            return self._frames.popleft()

    def take_due(self, play_seconds: float) -> TimelineFrame | None:
        with self._condition:
            due = sum(1 for frame in self._frames if frame.play_seconds <= play_seconds + TIME_TOLERANCE_SECONDS)
            if due == 0:
                return None
            for _ in range(due - 1 if due > MAX_FRAMES_BEHIND else 0):
                self._frames.popleft()
            self._condition.notify_all()
            return self._frames.popleft()

    def wait_settled(self) -> None:
        with self._condition:
            self._condition.wait_for(
                lambda: self._stopped or self._idle or len(self._frames) >= self._capacity,
                SETTLE_TIMEOUT_SECONDS,
            )

    def _current(self, generation: int) -> bool:
        return not self._stopped and self._request is not None and self._request.generation == generation

    def _has_request_after(self, generation: int | None) -> bool:
        return self._request is not None and self._request.generation != generation


class ClipDecoder:
    def __init__(self, path: Path, clip: Clip) -> None:
        self.clip = clip
        self._container: InputContainer = av.open(str(path))
        self._stream: VideoStream = self._container.streams.video[0]
        self._stream.thread_type = STREAM_THREADING
        self._start = self._stream.start_time or 0
        self._time_base = float(self._stream.time_base or 0)
        self._from = clip.in_seconds
        self._frames: Iterator[VideoFrame] = iter(())

    def start_at(self, offset_seconds: float) -> None:
        self._from = self.clip.in_seconds + offset_seconds
        self._seek(self._from, backward=True)

    def jump_to_keyframe_after(self, offset_seconds: float) -> None:
        self._from = self.clip.in_seconds
        self._seek(self.clip.in_seconds + offset_seconds, backward=False)

    def decoded(self) -> Iterator[tuple[float, VideoFrame, float]]:
        while True:
            started = time.perf_counter()
            frame = next(self._frames, None)
            if frame is None:
                return
            seconds = self._seconds(frame)
            if seconds >= self.clip.out_seconds - TIME_TOLERANCE_SECONDS:
                return
            if seconds >= self._from - TIME_TOLERANCE_SECONDS:
                yield seconds - self.clip.in_seconds, frame, elapsed_since(started)

    def close(self) -> None:
        self._container.close()

    def _seek(self, seconds: float, *, backward: bool) -> None:
        target = self._start + round(seconds / self._time_base)
        self._container.seek(target, stream=self._stream, backward=backward, any_frame=False)
        self._frames = self._container.decode(self._stream)

    def _seconds(self, frame: VideoFrame) -> float:
        pts = frame.pts if frame.pts is not None else self._start
        return max(0.0, (pts - self._start) * self._time_base)


@dataclass(slots=True)
class PreparedClip:
    decoder: ClipDecoder
    frames: Iterator[tuple[float, VideoFrame, float]]
    first: tuple[float, VideoFrame, float] | None
    image: I420Frame | None
    size: tuple[int, int]
    convert_milliseconds: float


def prepared_clip(path: Path, clip: Clip, size: tuple[int, int]) -> PreparedClip:
    decoder = ClipDecoder(path, clip)
    decoder.start_at(0.0)
    frames = decoder.decoded()
    first = next(frames, None)
    if first is None:
        return PreparedClip(decoder, frames, None, None, size, 0.0)
    started = time.perf_counter()
    image = fitted_i420(first[1], *size)
    return PreparedClip(decoder, frames, first, image, size, elapsed_since(started))


def close_prepared(future: Future[PreparedClip]) -> None:
    if future.cancelled() or future.exception() is not None:
        return
    future.result().decoder.close()


class TimelineReader:
    def __init__(
        self,
        read_ahead: ReadAhead,
        output: VideoOutput,
        preparer: ThreadPoolExecutor,
        target: Callable[[], float | None],
    ) -> None:
        self._read_ahead = read_ahead
        self._output = output
        self._preparer = preparer
        self._target = target
        self._last_emitted = -math.inf
        self.late_jumps = 0

    def run(self) -> None:
        generation = None
        while (request := self._read_ahead.next_request(generation)) is not None:
            generation = request.generation
            self._play(request)

    def _play(self, request: PlayRequest) -> None:
        timeline = request.timeline
        index, offset = timeline.locate(request.start_seconds)
        clip_start = timeline.start_of(index)
        self._last_emitted = -math.inf
        current = self._opened(request, index, offset)
        upcoming = self._prepare(request, index + 1)
        try:
            while self._read_ahead.is_current(request.generation):
                self._play_clip(request, current, clip_start)
                current.decoder.close()
                clip_start += timeline.clips[index].duration_seconds
                index = (index + 1) % len(timeline.clips)
                current = upcoming.result()
                upcoming = self._prepare(request, index + 1)
        finally:
            current.decoder.close()
            upcoming.add_done_callback(close_prepared)

    def _opened(self, request: PlayRequest, index: int, offset: float) -> PreparedClip:
        clip = request.timeline.clips[index]
        decoder = ClipDecoder(request.paths[clip.video_id], clip)
        decoder.start_at(offset)
        return PreparedClip(decoder, decoder.decoded(), None, None, self._size(), 0.0)

    def _prepare(self, request: PlayRequest, index: int) -> Future[PreparedClip]:
        clip = request.timeline.clips[index % len(request.timeline.clips)]
        return self._preparer.submit(prepared_clip, request.paths[clip.video_id], clip, self._size())

    def _play_clip(self, request: PlayRequest, prepared: PreparedClip, clip_start: float) -> None:
        if prepared.first is not None:
            ready = prepared.image if prepared.size == self._size() else None
            self._offer(request, clip_start, prepared.first, ready, prepared.convert_milliseconds)
        for decoded in prepared.frames:
            if not self._read_ahead.is_current(request.generation) or self._jumped_ahead(prepared, clip_start):
                return
            self._offer(request, clip_start, decoded)

    def _offer(
        self,
        request: PlayRequest,
        clip_start: float,
        decoded: tuple[float, VideoFrame, float],
        ready: I420Frame | None = None,
        ready_milliseconds: float = 0.0,
    ) -> None:
        offset, frame, decode_milliseconds = decoded
        play_seconds = clip_start + offset
        if not self._wanted(play_seconds):
            return
        started = time.perf_counter()
        image = fitted_i420(frame, *self._size()) if ready is None else ready
        convert_milliseconds = elapsed_since(started) if ready is None else ready_milliseconds
        self._emit(TimelineFrame(request.generation, play_seconds, image, decode_milliseconds, convert_milliseconds))

    def _wanted(self, play_seconds: float) -> bool:
        period = 1 / self._output.output.fps
        if play_seconds - self._last_emitted < period * EMIT_SHARE_OF_PERIOD:
            return False
        target = self._target()
        return target is None or play_seconds >= target - period or self._read_ahead.is_empty()

    def _emit(self, frame: TimelineFrame) -> None:
        self._last_emitted = frame.play_seconds
        self._read_ahead.put(frame)

    def _jumped_ahead(self, prepared: PreparedClip, clip_start: float) -> bool:
        target = self._target()
        if target is None or target - self._last_emitted < LATE_JUMP_SECONDS:
            return False
        offset = target - clip_start
        if offset < 0:
            return False
        self.late_jumps += 1
        if offset >= prepared.decoder.clip.duration_seconds:
            return True
        prepared.decoder.jump_to_keyframe_after(offset)
        self._last_emitted = target
        return False

    def _size(self) -> tuple[int, int]:
        output = self._output.output
        return output.width, output.height


class VideoPlayback:
    def __init__(
        self,
        timeline: Timeline,
        paths: Mapping[str, Path],
        output: VideoOutput,
        clock: Callable[[], float] = time.monotonic,
        sleep: Sleep = precise_sleep,
    ) -> None:
        self._timeline = timeline
        self._paths = paths
        self._output = output
        self._clock = clock
        self._sleep = sleep
        self._read_ahead = ReadAhead(READ_AHEAD_FRAMES)
        self._play_seconds: float | None = None
        self._position: float | None = None
        self._restart_at: float | None = 0.0
        self._reader: TimelineReader | None = None

    @property
    def position_seconds(self) -> float | None:
        return self._position

    @property
    def late_jumps(self) -> int:
        return 0 if self._reader is None else self._reader.late_jumps

    def seek(self, seconds: float) -> None:
        self._restart_at = seconds

    def change_timeline(self, timeline: Timeline, paths: Mapping[str, Path]) -> None:
        position = self._position or 0.0
        self._timeline = timeline
        self._paths = paths
        self._restart_at = position if position < timeline.duration_seconds else 0.0

    def wait_settled(self) -> None:
        self._read_ahead.wait_settled()

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        producer = ThreadPoolExecutor(max_workers=1, thread_name_prefix=PRODUCER_NAME)
        preparer = ThreadPoolExecutor(max_workers=1, thread_name_prefix=PREPARER_NAME)
        self._reader = TimelineReader(self._read_ahead, self._output, preparer, lambda: self._play_seconds)
        producing = loop.run_in_executor(producer, self._reader.run)
        try:
            await self._play(producing)
        finally:
            self._read_ahead.stop()
            with contextlib.suppress(Exception):
                await producing
            producer.shutdown(wait=False)
            preparer.shutdown(wait=False, cancel_futures=True)

    async def _play(self, producing: asyncio.Future[None]) -> None:
        previous = self._clock()
        next_tick = previous
        size = self._size()
        while True:
            if producing.done():
                producing.result()
                return
            now = self._clock()
            if self._play_seconds is not None and not self._output.frozen:
                self._play_seconds += now - previous
            previous = now
            if self._size() != size:
                size = self._size()
                self._restart_at = self._position or 0.0
            if self._restart_at is not None:
                self._restart(self._restart_at)
            if self._play_seconds is None:
                previous = self._show_first(previous)
            elif not self._output.frozen:
                self._show_due(self._play_seconds)
            next_tick = following_tick(next_tick, 1 / self._output.output.fps, self._clock())
            await self._sleep(next_tick - self._clock())

    def _restart(self, start_seconds: float) -> None:
        self._restart_at = None
        self._play_seconds = None
        self._read_ahead.restart(self._timeline, self._paths, start_seconds)

    def _show_first(self, previous: float) -> float:
        frame = self._read_ahead.take_first()
        if frame is None:
            return previous
        self._play_seconds = frame.play_seconds
        self._show(frame, replace_held=True)
        return self._clock()

    def _show_due(self, play_seconds: float) -> None:
        # Taking the nearest frame, not the last one already due, keeps tick jitter from pairing a skip with a repeat.
        frame = self._read_ahead.take_due(play_seconds + NEAREST_FRAME_SHARE / self._output.output.fps)
        if frame is not None:
            self._show(frame, replace_held=False)

    def _show(self, frame: TimelineFrame, *, replace_held: bool) -> None:
        self._output.record_stage(Stage.DECODE, frame.decode_milliseconds)
        self._output.record_stage(Stage.COLOR, frame.convert_milliseconds)
        self._position = frame.play_seconds % self._timeline.duration_seconds
        self._output.submit_video(frame.image, replace_held=replace_held)

    def _size(self) -> tuple[int, int]:
        output = self._output.output
        return output.width, output.height

import asyncio
import contextlib
from collections.abc import AsyncIterator, Callable
from pathlib import Path

import av
from av import VideoFrame

from wcam.diagnostics.stage_times import Stage
from wcam.tools.make_test_video import write_test_video
from wcam.video.playback import VideoPlayback
from wcam.virtualcam.sink import AnnouncedFormat, I420Frame

SMALL_WIDTH = 320
SMALL_HEIGHT = 180
CAMERA_FPS = 30
SHORT_SECONDS = 2.0
END_TOLERANCE_SECONDS = 1e-9
PORTRAIT_ROTATION = -90


def small_video(
    folder: Path,
    fps: int = CAMERA_FPS,
    rotation: int = 0,
    width: int = SMALL_WIDTH,
    height: int = SMALL_HEIGHT,
    name: str = "clip.mp4",
) -> Path:
    path = folder / name
    write_test_video(path, width, height, fps, SHORT_SECONDS, rotation)
    return path


def first_frame(path: Path) -> VideoFrame:
    with av.open(str(path)) as container:
        return next(container.decode(container.streams.video[0]))


async def chunks_of(data: bytes, size: int = 4096) -> AsyncIterator[bytes]:
    for start in range(0, len(data), size):
        yield data[start : start + size]


class PlaybackStoppedError(Exception):
    pass


class FakeVideoOutput:
    def __init__(self, width: int = SMALL_WIDTH, height: int = SMALL_HEIGHT, fps: int = CAMERA_FPS) -> None:
        self.output = AnnouncedFormat(width, height, fps, pending=False, running=True)
        self.frozen = False
        self.playback: VideoPlayback | None = None
        self.shown: list[tuple[float, I420Frame, bool]] = []
        self.shown_at: list[float] = []
        self.clock: Callable[[], float] = lambda: 0.0

    @property
    def positions(self) -> list[float]:
        return [position for position, _, _ in self.shown]

    def submit_video(self, image: I420Frame, *, replace_held: bool = False) -> None:
        position = None if self.playback is None else self.playback.position_seconds
        assert position is not None
        self.shown.append((position, image, replace_held))
        self.shown_at.append(self.clock())

    def record_stage(self, stage: Stage, milliseconds: float) -> None:
        pass


class FakeTime:
    def __init__(self, stop_at: float) -> None:
        self.now = 0.0
        self._stop_at = stop_at
        self._actions: list[tuple[float, Callable[[], None]]] = []

    def __call__(self) -> float:
        return self.now

    def at(self, moment: float, action: Callable[[], None]) -> None:
        self._actions.append((moment, action))

    async def sleep(self, seconds: float) -> None:
        self.now += max(seconds, 0.0)
        if self.now >= self._stop_at - END_TOLERANCE_SECONDS:
            raise PlaybackStoppedError
        for moment, action in [item for item in self._actions if item[0] <= self.now]:
            self._actions.remove((moment, action))
            action()
        await asyncio.sleep(0)


async def played(
    path: Path, seconds: float, setup: Callable[[FakeTime, FakeVideoOutput, VideoPlayback], None] | None = None
) -> FakeVideoOutput:
    clock = FakeTime(seconds)
    output = FakeVideoOutput()
    output.clock = clock
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        duration = float((stream.duration or 0) * (stream.time_base or 0))
    playback = VideoPlayback(path, duration, output, clock, clock.sleep)
    output.playback = playback
    if setup is not None:
        setup(clock, output, playback)
    with contextlib.suppress(PlaybackStoppedError):
        await playback.run()
    return output

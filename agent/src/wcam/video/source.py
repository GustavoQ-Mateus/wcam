import asyncio
import contextlib
import logging
from collections.abc import AsyncIterable, Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

from wcam.video.errors import (
    InvalidVideoPositionError,
    NoVideoFileToUseError,
    VideoSourceInactiveError,
)
from wcam.video.playback import VideoOutput, VideoPlayback
from wcam.video.store import StoredVideo, VideoFileInfo, VideoStore

PLAYBACK_FAILED = "The video stopped because it could not be played"

logger = logging.getLogger(__name__)

type EventListener = Callable[[str, Mapping[str, object]], None]
type PlaybackFactory = Callable[[StoredVideo, VideoOutput], VideoPlayback]


class VideoCamera(VideoOutput, Protocol):
    def start_video(self) -> None: ...

    def stop_video(self) -> None: ...


class PhoneSessions(Protocol):
    def start_video_source(self) -> Awaitable[None]: ...

    def stop_video_source(self) -> None: ...


@dataclass(frozen=True, slots=True)
class VideoSourceView:
    file: VideoFileInfo | None
    active: bool
    position_seconds: float | None


def default_playback(video: StoredVideo, output: VideoOutput) -> VideoPlayback:
    return VideoPlayback(video.path, video.info.duration_seconds, output)


class VideoSource:
    def __init__(
        self,
        store: VideoStore,
        camera: VideoCamera,
        sessions: PhoneSessions,
        playback_factory: PlaybackFactory = default_playback,
    ) -> None:
        self._store = store
        self._camera = camera
        self._sessions = sessions
        self._playback_factory = playback_factory
        self._playback: VideoPlayback | None = None
        self._task: asyncio.Task[None] | None = None
        self._change_listeners: list[Callable[[], None]] = []
        self._event_listeners: list[EventListener] = []

    @property
    def active(self) -> bool:
        return self._task is not None

    @property
    def has_file(self) -> bool:
        return self._store.current is not None

    def view(self) -> VideoSourceView:
        current = self._store.current
        position = None if self._playback is None else self._playback.position_seconds
        return VideoSourceView(None if current is None else current.info, self.active, position)

    def on_change(self, listener: Callable[[], None]) -> None:
        self._change_listeners.append(listener)

    def on_event(self, listener: EventListener) -> None:
        self._event_listeners.append(listener)

    async def save(self, chunks: AsyncIterable[bytes], name: str) -> VideoFileInfo:
        await self.deactivate()
        stored = await self._store.save(chunks, name)
        self._notify_change()
        return stored.info

    async def remove(self) -> None:
        await self.deactivate()
        self._store.remove()
        self._notify_change()

    async def activate(self) -> None:
        current = self._store.current
        if current is None:
            raise NoVideoFileToUseError
        if self.active:
            return
        await self._sessions.start_video_source()
        self._camera.start_video()
        self._playback = self._playback_factory(current, self._camera)
        self._task = asyncio.get_running_loop().create_task(self._play(self._playback))
        self._record_event(True, current.info.name)
        self._notify_change()

    async def deactivate(self) -> None:
        task = self._task
        if task is None:
            return
        self._task = None
        self._playback = None
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        self._camera.stop_video()
        self._sessions.stop_video_source()
        current = self._store.current
        self._record_event(False, None if current is None else current.info.name)
        self._notify_change()

    def seek(self, seconds: float) -> None:
        playback = self._playback
        current = self._store.current
        if playback is None or current is None:
            raise VideoSourceInactiveError
        if not 0 <= seconds < current.info.duration_seconds:
            raise InvalidVideoPositionError
        playback.seek(seconds)

    async def _play(self, playback: VideoPlayback) -> None:
        try:
            await playback.run()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(PLAYBACK_FAILED)
            asyncio.get_running_loop().call_soon(self._stop_after_failure)

    def _stop_after_failure(self) -> None:
        self._task = None
        self._playback = None
        self._camera.stop_video()
        self._sessions.stop_video_source()
        self._notify_change()

    def _record_event(self, active: bool, name: str | None) -> None:
        for listener in self._event_listeners:
            listener("video_source", {"active": active, "name": name})

    def _notify_change(self) -> None:
        for listener in self._change_listeners:
            listener()

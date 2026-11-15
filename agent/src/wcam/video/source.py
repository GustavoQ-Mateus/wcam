import asyncio
import contextlib
import logging
from collections.abc import AsyncIterable, Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from wcam.video.errors import InvalidVideoPositionError, TimelineEmptyError, VideoSourceInactiveError
from wcam.video.library import LibraryVideo, VideoLibrary
from wcam.video.playback import VideoOutput, VideoPlayback
from wcam.video.timeline import Clip, Timeline, TimelineStore, validated_timeline

DURATION_DECIMALS = 3
PLAYBACK_FAILED = "The video stopped because it could not be played"

logger = logging.getLogger(__name__)

type EventListener = Callable[[str, Mapping[str, object]], None]
type PlaybackFactory = Callable[[Timeline, Mapping[str, Path], VideoOutput], VideoPlayback]


class VideoCamera(VideoOutput, Protocol):
    def start_video(self) -> None: ...

    def stop_video(self) -> None: ...


class PhoneSessions(Protocol):
    def ensure_live(self) -> None: ...

    def start_video_source(self) -> None: ...

    def stop_video_source(self) -> None: ...


@dataclass(frozen=True, slots=True)
class VideoSourceView:
    videos: tuple[LibraryVideo, ...]
    timeline: Timeline
    active: bool
    position_seconds: float | None


def default_playback(timeline: Timeline, paths: Mapping[str, Path], output: VideoOutput) -> VideoPlayback:
    return VideoPlayback(timeline, paths, output)


class VideoSource:
    def __init__(
        self,
        library: VideoLibrary,
        timelines: TimelineStore,
        camera: VideoCamera,
        sessions: PhoneSessions,
        playback_factory: PlaybackFactory = default_playback,
    ) -> None:
        self._library = library
        self._timelines = timelines
        self._camera = camera
        self._sessions = sessions
        self._playback_factory = playback_factory
        self._timeline = timelines.load()
        self._playback: VideoPlayback | None = None
        self._task: asyncio.Task[None] | None = None
        self._change_listeners: list[Callable[[], None]] = []
        self._event_listeners: list[EventListener] = []

    @property
    def active(self) -> bool:
        return self._task is not None

    @property
    def has_clips(self) -> bool:
        return bool(self._timeline.clips)

    def view(self) -> VideoSourceView:
        position = None if self._playback is None else self._playback.position_seconds
        return VideoSourceView(self._library.videos, self._timeline, self.active, position)

    def filmstrip(self, video_id: str) -> Path:
        return self._library.find(video_id).filmstrip_path

    def on_change(self, listener: Callable[[], None]) -> None:
        self._change_listeners.append(listener)

    def on_event(self, listener: EventListener) -> None:
        self._event_listeners.append(listener)

    def ensure_can_add(self) -> None:
        self._sessions.ensure_live()
        self._library.ensure_room()

    async def add(self, chunks: AsyncIterable[bytes], name: str) -> LibraryVideo:
        video = await self._library.add(chunks, name)
        self._notify_change()
        return video

    async def remove(self, video_id: str) -> None:
        self._library.remove(video_id)
        remaining = self._timeline.without_video(video_id)
        if remaining != self._timeline:
            await self._apply_timeline(remaining)
        self._notify_change()

    async def set_timeline(self, clips: Sequence[Clip]) -> None:
        durations = {video.id: video.info.duration_seconds for video in self._library.videos}
        await self._apply_timeline(validated_timeline(clips, durations))
        self._notify_change()

    async def activate(self) -> None:
        if self.active:
            return
        self._sessions.ensure_live()
        if not self.has_clips:
            raise TimelineEmptyError
        self._sessions.start_video_source()
        self._camera.start_video()
        self._playback = self._playback_factory(self._timeline, self._paths(), self._camera)
        self._task = asyncio.get_running_loop().create_task(self._play(self._playback))
        self._record_event("video_source", {"active": True})
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
        self._stopped()

    def seek(self, seconds: float) -> None:
        playback = self._playback
        if playback is None:
            raise VideoSourceInactiveError
        if not 0 <= seconds < self._timeline.duration_seconds:
            raise InvalidVideoPositionError
        playback.seek(seconds)

    async def _apply_timeline(self, timeline: Timeline) -> None:
        self._timelines.save(timeline)
        self._timeline = timeline
        self._record_event(
            "timeline",
            {"clips": len(timeline.clips), "durationSeconds": round(timeline.duration_seconds, DURATION_DECIMALS)},
        )
        if not timeline.clips:
            await self.deactivate()
        elif self._playback is not None:
            self._playback.change_timeline(timeline, self._paths())

    def _paths(self) -> dict[str, Path]:
        return {video.id: video.path for video in self._library.videos}

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
        self._stopped()

    def _stopped(self) -> None:
        self._camera.stop_video()
        self._sessions.stop_video_source()
        self._record_event("video_source", {"active": False})
        self._notify_change()

    def _record_event(self, kind: str, data: Mapping[str, object]) -> None:
        for listener in self._event_listeners:
            listener(kind, data)

    def _notify_change(self) -> None:
        for listener in self._change_listeners:
            listener()

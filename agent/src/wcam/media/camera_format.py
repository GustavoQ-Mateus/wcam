import asyncio
from collections.abc import Callable

from wcam.media.pipeline import FramePipeline
from wcam.media.video_format import VideoFormat, format_of
from wcam.virtualcam.sink import AnnouncedFormat

FORMAT_POLL_SECONDS = 0.15


class CameraFormatControl:
    def __init__(self, pipeline: FramePipeline, poll_seconds: float = FORMAT_POLL_SECONDS) -> None:
        self._pipeline = pipeline
        self._poll_seconds = poll_seconds
        self._announced: AnnouncedFormat | None = None
        self._listeners: list[Callable[[], None]] = []
        self._requests: set[asyncio.Task[None]] = set()
        self._polling: asyncio.Task[None] | None = None

    @property
    def camera_format(self) -> VideoFormat | None:
        announced = self._announced
        return None if announced is None else format_of(announced.width, announced.height, announced.fps)

    @property
    def pending(self) -> bool:
        return self._announced is not None and self._announced.pending

    def on_change(self, listener: Callable[[], None]) -> None:
        self._listeners.append(listener)

    def start(self) -> None:
        self.refresh()
        if self._pipeline.sink.reports_format_changes:
            self._polling = asyncio.get_running_loop().create_task(self._poll())

    def request(self, video_format: VideoFormat) -> None:
        task = asyncio.get_running_loop().create_task(self._apply(video_format))
        self._requests.add(task)
        task.add_done_callback(self._requests.discard)

    def refresh(self) -> None:
        announced = self._pipeline.sink.announced_format()
        if announced == self._announced:
            return
        self._announced = announced
        self._pipeline.follow(announced)
        for listener in self._listeners:
            listener()

    async def close(self) -> None:
        tasks = [*self._requests, *([] if self._polling is None else [self._polling])]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _apply(self, video_format: VideoFormat) -> None:
        size = video_format.size
        await self._pipeline.request_format(size.width, size.height, size.fps)
        self.refresh()

    async def _poll(self) -> None:
        while True:
            await asyncio.sleep(self._poll_seconds)
            self.refresh()

import asyncio
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame

from wcam.media.loopback_ice import gather_only_on_loopback
from wcam.media.peer import peer_configuration
from wcam.media.pipeline import I420_FORMAT, REDUCTION_INTERPOLATION, FramePipeline, i420_planes
from wcam.media.sdp_filter import has_video
from wcam.virtualcam.sink import I420Frame, frame_size

PREVIEW_WIDTH = 960
PREVIEW_HEIGHT = 540
PREVIEW_WORKER_NAME = "wcam-preview"
CLOSED_CONNECTION_STATES = ("failed", "closed")
PREVIEW_ENDED = "The console preview connection ended"

logger = logging.getLogger(__name__)


def preview_size(output_width: int, output_height: int) -> tuple[int, int]:
    height = min(PREVIEW_HEIGHT, output_height)
    return height * 16 // 9 // 2 * 2, height


def reduced_frame(frame: I420Frame) -> VideoFrame:
    width, height = frame_size(frame)
    preview_width, preview_height = preview_size(width, height)
    step = max(1, height // (2 * preview_height))
    smaller = decimated(frame, width, height, step) if step > 1 else frame
    full = VideoFrame.from_ndarray(np.ascontiguousarray(smaller), format=I420_FORMAT)
    return full.reformat(width=preview_width, height=preview_height, interpolation=REDUCTION_INTERPOLATION)


def decimated(frame: I420Frame, width: int, height: int, step: int) -> I420Frame:
    # Skipping pixels first keeps the area reduction of a 2160p frame as cheap as that of a 1080p one.
    planes = [np.ascontiguousarray(plane[::step, ::step]).reshape(-1) for plane in i420_planes(frame, width, height)]
    return np.concatenate(planes).reshape(height // step * 3 // 2, width // step)


class PreviewTrack(VideoStreamTrack):
    def __init__(self, pipeline: FramePipeline, worker: ThreadPoolExecutor) -> None:
        super().__init__()
        self._pipeline = pipeline
        self._worker = worker
        self._source: I420Frame | None = None
        self._reduced: VideoFrame | None = None

    async def recv(self) -> VideoFrame:
        pts, time_base = await self.next_timestamp()
        frame = await self._current_frame()
        frame.pts = pts
        frame.time_base = time_base
        return frame

    async def _current_frame(self) -> VideoFrame:
        source = self._pipeline.last_sent
        if self._reduced is not None and source is self._source:
            return self._reduced
        if source is None:
            source = self._pipeline.placeholder
        loop = asyncio.get_running_loop()
        reduced = await loop.run_in_executor(self._worker, reduced_frame, source)
        self._reduced, self._source = reduced, source
        return reduced


class Preview:
    def __init__(self, pipeline: FramePipeline, on_change: Callable[[], None] = lambda: None) -> None:
        self._pipeline = pipeline
        self._on_change = on_change
        self._worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix=PREVIEW_WORKER_NAME)
        self._connection: RTCPeerConnection | None = None
        self._releasing: set[asyncio.Task[None]] = set()

    @property
    def is_open(self) -> bool:
        return self._connection is not None

    async def open(self, offer_sdp: str) -> str:
        if not has_video(offer_sdp):
            raise ValueError("the preview offer has no video")
        await self.close()
        connection = RTCPeerConnection(configuration=peer_configuration())
        try:
            answer = await self._answer(connection, offer_sdp)
        except Exception:
            await connection.close()
            raise
        self._connection = connection
        connection.on("connectionstatechange", lambda: self._release_when_closed(connection))
        self._on_change()
        return answer

    async def close(self) -> None:
        connection = self._connection
        if connection is None:
            return
        self._connection = None
        await connection.close()
        self._on_change()

    async def shutdown(self) -> None:
        for task in list(self._releasing):
            task.cancel()
        await asyncio.gather(*self._releasing, return_exceptions=True)
        await self.close()
        self._worker.shutdown(wait=True)

    async def _answer(self, connection: RTCPeerConnection, offer_sdp: str) -> str:
        await connection.setRemoteDescription(RTCSessionDescription(offer_sdp, "offer"))
        connection.addTrack(PreviewTrack(self._pipeline, self._worker))
        gather_only_on_loopback(connection)
        await connection.setLocalDescription(await connection.createAnswer())
        return connection.localDescription.sdp

    def _release_when_closed(self, connection: RTCPeerConnection) -> None:
        if connection is not self._connection or connection.connectionState not in CLOSED_CONNECTION_STATES:
            return
        logger.info(PREVIEW_ENDED)
        task = asyncio.get_running_loop().create_task(self.close())
        self._releasing.add(task)
        task.add_done_callback(self._releasing.discard)

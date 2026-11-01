import asyncio
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from enum import StrEnum

import numpy as np
from av import VideoFrame

from wcam.media.placeholder import black_i420
from wcam.media.quality import QualityMeter, QualityReport
from wcam.virtualcam.sink import OUTPUT_FPS, OUTPUT_HEIGHT, OUTPUT_WIDTH, CameraState, I420Frame, VirtualCameraSink

FRAME_INTERVAL_SECONDS = 1 / OUTPUT_FPS
PHONE_SILENCE_SECONDS = 1.0
I420_FORMAT = "yuv420p"
WORKER_NAME = "wcam-frames"
QUALITY_WORKER_NAME = "wcam-quality"


class FrameSource(StrEnum):
    PHONE = "phone"
    PLACEHOLDER = "placeholder"


class FramePipeline:
    def __init__(
        self,
        sink: VirtualCameraSink,
        quality: QualityMeter | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.sink = sink
        self.quality = quality
        self._clock = clock
        self._placeholder = black_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT)
        self._pending: asyncio.Queue[VideoFrame] = asyncio.Queue(maxsize=1)
        self._worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix=WORKER_NAME)
        self._quality_worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix=QUALITY_WORKER_NAME)
        self._measuring: Future[None] | None = None
        self._phone_active = False
        self._last_phone: I420Frame | None = None
        self._last_phone_at: float | None = None
        self.source = FrameSource.PLACEHOLDER
        self.frames_scaled = 0

    @property
    def quality_report(self) -> QualityReport | None:
        return None if self.quality is None else self.quality.report

    def open(self) -> None:
        self.sink.open(OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS)

    def start_phone(self) -> None:
        self.frames_scaled = 0
        self._last_phone = None
        self._last_phone_at = None
        self._phone_active = True
        if self.quality is not None:
            self.quality.restart(self._clock())

    def stop_phone(self) -> None:
        self._phone_active = False
        self._last_phone = None

    def submit(self, frame: VideoFrame) -> None:
        if self._pending.full():
            self._pending.get_nowait()
        self._pending.put_nowait(frame)

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        try:
            while True:
                frame = await self._next_frame()
                await loop.run_in_executor(self._worker, self.deliver, frame)
        finally:
            self._worker.shutdown(wait=True)
            self._quality_worker.shutdown(wait=True)
            self.sink.close()

    def deliver(self, frame: VideoFrame | None) -> None:
        now = self._clock()
        if frame is not None:
            self._accept_phone_frame(frame, now)
        elif self._last_phone_at is None or now - self._last_phone_at > PHONE_SILENCE_SECONDS:
            self._last_phone = None
        output = self._last_phone if self._phone_active else None
        self.source = FrameSource.PLACEHOLDER if output is None else FrameSource.PHONE
        if self.sink.status.state is CameraState.ACTIVE:
            self.sink.send(self._placeholder if output is None else output)
        if output is not None and frame is not None:
            self._measure(now, output)

    def _measure(self, now: float, output: I420Frame) -> None:
        if self.quality is None or (self._measuring is not None and not self._measuring.done()):
            return
        self._measuring = self._quality_worker.submit(self.quality.observe, now, output[:OUTPUT_HEIGHT])

    async def _next_frame(self) -> VideoFrame | None:
        try:
            return await asyncio.wait_for(self._pending.get(), FRAME_INTERVAL_SECONDS)
        except TimeoutError:
            return None

    def _accept_phone_frame(self, frame: VideoFrame, now: float) -> None:
        self._last_phone_at = now
        if frame.height > frame.width:
            self._last_phone = None
            return
        if (frame.width, frame.height) == (OUTPUT_WIDTH, OUTPUT_HEIGHT):
            self._last_phone = i420_array(frame)
            return
        self._last_phone = self._letterboxed(frame)
        self.frames_scaled += 1

    def _letterboxed(self, frame: VideoFrame) -> I420Frame:
        scale = min(OUTPUT_WIDTH / frame.width, OUTPUT_HEIGHT / frame.height)
        width = even(frame.width * scale)
        height = even(frame.height * scale)
        scaled = i420_array(frame.reformat(width=width, height=height, format=I420_FORMAT))
        canvas = self._placeholder.copy()
        paste_i420(canvas, scaled, width, height)
        return canvas


def i420_array(frame: VideoFrame) -> I420Frame:
    converted = frame if frame.format.name == I420_FORMAT else frame.reformat(format=I420_FORMAT)
    array: I420Frame = np.ascontiguousarray(converted.to_ndarray(), dtype=np.uint8)
    return array


def even(value: float) -> int:
    return max(2, int(value) // 2 * 2)


def paste_i420(canvas: I420Frame, image: I420Frame, width: int, height: int) -> None:
    top = even((OUTPUT_HEIGHT - height) / 2) if height < OUTPUT_HEIGHT else 0
    left = even((OUTPUT_WIDTH - width) / 2) if width < OUTPUT_WIDTH else 0
    for canvas_plane, image_plane, divisor in zip(
        i420_planes(canvas, OUTPUT_WIDTH, OUTPUT_HEIGHT),
        i420_planes(image, width, height),
        (1, 2, 2),
        strict=True,
    ):
        row = top // divisor
        column = left // divisor
        canvas_plane[row : row + height // divisor, column : column + width // divisor] = image_plane


def i420_planes(frame: I420Frame, width: int, height: int) -> tuple[I420Frame, I420Frame, I420Frame]:
    flat = frame.reshape(-1)
    luma_size = width * height
    chroma_size = luma_size // 4
    luma = flat[:luma_size].reshape(height, width)
    blue = flat[luma_size : luma_size + chroma_size].reshape(height // 2, width // 2)
    red = flat[luma_size + chroma_size : luma_size + 2 * chroma_size].reshape(height // 2, width // 2)
    return luma, blue, red

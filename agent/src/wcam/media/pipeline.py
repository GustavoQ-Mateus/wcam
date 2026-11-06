import asyncio
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from enum import StrEnum

import numpy as np
from av import VideoFrame
from av.video.reformatter import ColorRange as DeclaredRange

from wcam.media.color_calibration import ColorTables, applied_tables, can_reduce, correction_tables
from wcam.media.color_calibrator import CalibrationState, ColorCalibrator
from wcam.media.color_range import (
    UNSPECIFIED_MATRIX,
    ColorRange,
    declared_matrix,
    declared_range,
    translate_in_place,
)
from wcam.media.placeholder import black_i420
from wcam.media.quality import QualityMeter, QualityReport
from wcam.virtualcam.sink import OUTPUT_FPS, OUTPUT_HEIGHT, OUTPUT_WIDTH, CameraState, I420Frame, VirtualCameraSink

FRAME_INTERVAL_SECONDS = 1 / OUTPUT_FPS
STALE_FRAME_SECONDS = 0.5
FREEZE_SECONDS = 3.0
I420_FORMAT = "yuv420p"
RAW_I420_FORMATS = (I420_FORMAT, "yuvj420p")
WORKER_NAME = "wcam-frames"
QUALITY_WORKER_NAME = "wcam-quality"


class FrameSource(StrEnum):
    PHONE = "phone"
    FROZEN = "frozen"
    PLACEHOLDER = "placeholder"


class FramePipeline:
    def __init__(
        self,
        sink: VirtualCameraSink,
        quality: QualityMeter | None = None,
        clock: Callable[[], float] = time.monotonic,
        fallback_reason: str | None = None,
        color_calibrator: ColorCalibrator | None = None,
    ) -> None:
        self.sink = sink
        self.fallback_reason = fallback_reason
        self.quality = quality
        self.color_calibrator = color_calibrator or ColorCalibrator()
        self._clock = clock
        self._placeholder = black_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT)
        self._pending: asyncio.Queue[VideoFrame] = asyncio.Queue(maxsize=1)
        self._worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix=WORKER_NAME)
        self._quality_worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix=QUALITY_WORKER_NAME)
        self._measuring: Future[None] | None = None
        self._measured_calibration = CalibrationState.MEASURING
        self._phone_active = False
        self._last_phone: I420Frame | None = None
        self._last_phone_at: float | None = None
        self.portrait = False
        self.source = FrameSource.PLACEHOLDER
        self.frames_scaled = 0
        self.color_range = ColorRange.UNSPECIFIED
        self.color_matrix = UNSPECIFIED_MATRIX

    @property
    def quality_report(self) -> QualityReport | None:
        return None if self.quality is None else self.quality.report

    def open(self) -> None:
        self.sink.open(OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS)

    def start_phone(self) -> None:
        self.frames_scaled = 0
        self.color_range = ColorRange.UNSPECIFIED
        self.color_matrix = UNSPECIFIED_MATRIX
        self._last_phone = None
        self._last_phone_at = self._clock()
        self.portrait = False
        self.color_calibrator.restart()
        self._phone_active = True
        self._measured_calibration = CalibrationState.MEASURING
        if self.quality is not None:
            self.quality.restart(self._clock())

    def stop_phone(self) -> None:
        self._phone_active = False
        self._last_phone = None
        self.color_calibrator.restart()

    def phone_frame_age(self) -> float | None:
        if not self._phone_active or self._last_phone_at is None:
            return None
        return self._clock() - self._last_phone_at

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
            self.color_calibrator.close()
            self.sink.close()

    def deliver(self, frame: VideoFrame | None) -> None:
        now = self._clock()
        if frame is not None:
            self._accept_phone_frame(frame, now)
        elif self._last_phone_at is None or now - self._last_phone_at > FREEZE_SECONDS:
            self._last_phone = None
        output = self._last_phone if self._phone_active else None
        self.source = self._source_of(output, now)
        if self.sink.status.state is CameraState.ACTIVE:
            self.sink.send(self._placeholder if output is None else output)
        if output is not None and frame is not None:
            self._measure(now, output)

    def _source_of(self, output: I420Frame | None, now: float) -> FrameSource:
        if output is None:
            return FrameSource.PLACEHOLDER
        if self._last_phone_at is not None and now - self._last_phone_at > STALE_FRAME_SECONDS:
            return FrameSource.FROZEN
        return FrameSource.PHONE

    def _measure(self, now: float, output: I420Frame) -> None:
        if self.quality is None:
            return
        self._restart_quality_on_calibration_change(self.quality, now)
        if self._measuring is not None and not self._measuring.done():
            return
        self._measuring = self._quality_worker.submit(self.quality.observe, now, output[:OUTPUT_HEIGHT])

    def _restart_quality_on_calibration_change(self, quality: QualityMeter, now: float) -> None:
        state = self.color_calibrator.status.state
        if state is self._measured_calibration:
            return
        self._measured_calibration = state
        correction = self.color_calibrator.correction
        luma_table = None
        if state is CalibrationState.APPLIED and correction is not None:
            luma_table = correction_tables(correction, self.color_range)[0]
        self._quality_worker.submit(quality.restart, now, luma_table)

    async def _next_frame(self) -> VideoFrame | None:
        try:
            return await asyncio.wait_for(self._pending.get(), FRAME_INTERVAL_SECONDS)
        except TimeoutError:
            return None

    def _accept_phone_frame(self, frame: VideoFrame, now: float) -> None:
        self.color_range = declared_range(frame)
        self.color_matrix = declared_matrix(frame)
        self.portrait = frame.height > frame.width
        if self.portrait:
            self._last_phone = None
            return
        self._last_phone_at = now
        if (frame.width, frame.height) == (OUTPUT_WIDTH, OUTPUT_HEIGHT):
            self._last_phone = self._converted(frame, OUTPUT_WIDTH, OUTPUT_HEIGHT)
            return
        self._last_phone = self._letterboxed(frame)
        self.frames_scaled += 1

    def _letterboxed(self, frame: VideoFrame) -> I420Frame:
        scale = min(OUTPUT_WIDTH / frame.width, OUTPUT_HEIGHT / frame.height)
        width = even(frame.width * scale)
        height = even(frame.height * scale)
        scaled = self._converted(frame, width, height)
        canvas = self._placeholder.copy()
        paste_i420(canvas, scaled, width, height)
        return canvas

    def _converted(self, frame: VideoFrame, width: int, height: int) -> I420Frame:
        array = i420_array(frame, width, height, self.color_range)
        calibrator = self.color_calibrator
        if calibrator.collecting and can_reduce(width, height):
            calibrator.remember(i420_planes(array, width, height), self.color_range)
        apply_color_tables(array, height, applied_tables(calibrator.correction, self.color_range))
        return array


def apply_color_tables(frame: I420Frame, height: int, tables: ColorTables | None) -> None:
    if tables is None:
        return
    luma_table, chroma_table = tables
    translate_in_place(frame[:height], luma_table)
    translate_in_place(frame[height:], chroma_table)


def i420_array(frame: VideoFrame, width: int, height: int, color_range: ColorRange) -> I420Frame:
    source = frame
    if frame.format.name not in RAW_I420_FORMATS or (frame.width, frame.height) != (width, height):
        kept_range = DeclaredRange.JPEG if color_range is ColorRange.FULL else DeclaredRange.MPEG
        source = frame.reformat(
            width=width,
            height=height,
            format=I420_FORMAT,
            src_color_range=kept_range,
            dst_color_range=kept_range,
        )
    array: I420Frame = np.ascontiguousarray(source.to_ndarray(), dtype=np.uint8)
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

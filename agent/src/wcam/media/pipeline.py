import asyncio
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from enum import StrEnum

import numpy as np
from av import VideoFrame
from av.video.plane import VideoPlane
from av.video.reformatter import ColorRange as DeclaredRange

from wcam.media.color_correction import ColorCorrection, ColorTables, CorrectionState, correction_tables
from wcam.media.color_range import (
    UNSPECIFIED_MATRIX,
    ColorRange,
    declared_matrix,
    declared_range,
)
from wcam.media.placeholder import black_i420, camera_off_i420
from wcam.media.quality import QualityMeter, QualityReport
from wcam.media.video_format import DEFAULT_VIDEO_FORMAT
from wcam.virtualcam.sink import AnnouncedFormat, CameraState, I420Frame, VirtualCameraSink, frame_size

STALE_FRAME_SECONDS = 0.5
FREEZE_SECONDS = 3.0
I420_FORMAT = "yuv420p"
RAW_I420_FORMATS = (I420_FORMAT, "yuvj420p")
WORKER_NAME = "wcam-frames"
REDUCTION_INTERPOLATION = "AREA"
DEFAULT_OUTPUT = AnnouncedFormat(
    DEFAULT_VIDEO_FORMAT.size.width,
    DEFAULT_VIDEO_FORMAT.size.height,
    DEFAULT_VIDEO_FORMAT.size.fps,
    pending=False,
    running=False,
)
QUALITY_WORKER_NAME = "wcam-quality"
ALL_COLUMNS = slice(None)
MIRRORED_COLUMNS = slice(None, None, -1)


class FrameSource(StrEnum):
    PHONE = "phone"
    FROZEN = "frozen"
    HELD = "held"
    CAMERA_OFF = "camera_off"
    PLACEHOLDER = "placeholder"


class FramePipeline:
    def __init__(
        self,
        sink: VirtualCameraSink,
        quality: QualityMeter | None = None,
        clock: Callable[[], float] = time.monotonic,
        fallback_reason: str | None = None,
    ) -> None:
        self.sink = sink
        self.fallback_reason = fallback_reason
        self.quality = quality
        self.color_correction: ColorCorrection | None = None
        self._clock = clock
        self.output = DEFAULT_OUTPUT
        self._placeholder = black_i420(DEFAULT_OUTPUT.width, DEFAULT_OUTPUT.height)
        self._pending: asyncio.Queue[VideoFrame] = asyncio.Queue(maxsize=1)
        self._worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix=WORKER_NAME)
        self._quality_worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix=QUALITY_WORKER_NAME)
        self._measuring: Future[None] | None = None
        self._measured_correction = CorrectionState.DEFAULT
        self._phone_active = False
        self._last_phone: I420Frame | None = None
        self._last_phone_at: float | None = None
        self.portrait = False
        self.source = FrameSource.PLACEHOLDER
        self.frames_scaled = 0
        self.color_range = ColorRange.UNSPECIFIED
        self.color_matrix = UNSPECIFIED_MATRIX
        self.frozen = False
        self.camera_off = False
        self.mirror = False
        self._last_sent: I420Frame | None = None
        self._camera_off_frame: I420Frame | None = None

    @property
    def quality_report(self) -> QualityReport | None:
        return None if self.quality is None else self.quality.report

    def open(self) -> None:
        self.sink.open(DEFAULT_OUTPUT.width, DEFAULT_OUTPUT.height, DEFAULT_OUTPUT.fps)
        self.follow(self.sink.announced_format())

    def follow(self, announced: AnnouncedFormat | None) -> None:
        if announced is None:
            return
        if frame_size(self._placeholder) != (announced.width, announced.height):
            self._placeholder = black_i420(announced.width, announced.height)
        self.output = announced

    async def request_format(self, width: int, height: int, fps: int) -> bool:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._worker, self._change_format, width, height, fps)

    def start_phone(self) -> None:
        self.frames_scaled = 0
        self.color_range = ColorRange.UNSPECIFIED
        self.color_matrix = UNSPECIFIED_MATRIX
        self._last_phone = None
        self._last_phone_at = self._clock()
        self.portrait = False
        self._phone_active = True
        self._measured_correction = CorrectionState.DEFAULT
        if self.quality is not None:
            self.quality.restart(self._clock())

    def stop_phone(self) -> None:
        self._phone_active = False
        self._last_phone = None
        self.color_correction = None

    def apply_controls(self, frozen: bool, camera_off: bool, mirror: bool) -> None:
        if self.camera_off and not camera_off and self._phone_active:
            self._last_phone_at = self._clock()
        self.frozen = frozen
        self.camera_off = camera_off
        self.mirror = mirror

    def color_tables(self) -> ColorTables | None:
        return correction_tables(self.color_correction, self.color_range)

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
            self.sink.close()

    def deliver(self, frame: VideoFrame | None) -> None:
        now = self._clock()
        placeholder = self._placeholder
        if frame is not None:
            self._accept_phone_frame(frame, now, placeholder)
        elif self._last_phone_at is None or now - self._last_phone_at > FREEZE_SECONDS:
            self._last_phone = None
        output = self._last_phone if self._phone_active and fits(self._last_phone, placeholder) else None
        self.source, sent = self._chosen_frame(output, now, placeholder)
        self._last_sent = sent
        if self.sink.status.state is CameraState.ACTIVE:
            self.sink.send(sent)
        if output is not None and sent is output and frame is not None:
            self._measure(now, output)

    def _change_format(self, width: int, height: int, fps: int) -> bool:
        accepted = self.sink.request_format(width, height, fps)
        self.follow(self.sink.announced_format())
        return accepted

    def _chosen_frame(
        self, output: I420Frame | None, now: float, placeholder: I420Frame
    ) -> tuple[FrameSource, I420Frame]:
        if self.camera_off:
            return FrameSource.CAMERA_OFF, self._camera_off_like(placeholder)
        if self.frozen and self._last_sent is not None and fits(self._last_sent, placeholder):
            return FrameSource.HELD, self._last_sent
        return self._source_of(output, now), placeholder if output is None else output

    def _camera_off_like(self, placeholder: I420Frame) -> I420Frame:
        if self._camera_off_frame is None or not fits(self._camera_off_frame, placeholder):
            self._camera_off_frame = camera_off_i420(*frame_size(placeholder))
        return self._camera_off_frame

    def _source_of(self, output: I420Frame | None, now: float) -> FrameSource:
        if output is None:
            return FrameSource.PLACEHOLDER
        if self._last_phone_at is not None and now - self._last_phone_at > STALE_FRAME_SECONDS:
            return FrameSource.FROZEN
        return FrameSource.PHONE

    def _measure(self, now: float, output: I420Frame) -> None:
        if self.quality is None:
            return
        self._restart_quality_on_correction_change(self.quality, now)
        if self._measuring is not None and not self._measuring.done():
            return
        _, height = frame_size(output)
        self._measuring = self._quality_worker.submit(self.quality.observe, now, output[:height])

    def _restart_quality_on_correction_change(self, quality: QualityMeter, now: float) -> None:
        correction = self.color_correction
        state = CorrectionState.DEFAULT if correction is None else correction.state
        if state is self._measured_correction:
            return
        self._measured_correction = state
        tables = self.color_tables() if state is CorrectionState.APPLIED else None
        self._quality_worker.submit(quality.restart, now, None if tables is None else tables[0])

    async def _next_frame(self) -> VideoFrame | None:
        try:
            return await asyncio.wait_for(self._pending.get(), 1 / self.output.fps)
        except TimeoutError:
            return None

    def _accept_phone_frame(self, frame: VideoFrame, now: float, placeholder: I420Frame) -> None:
        self.color_range = declared_range(frame)
        self.color_matrix = declared_matrix(frame)
        self.portrait = frame.height > frame.width
        output_width, output_height = frame_size(placeholder)
        if self.portrait:
            self._last_phone = self._pillarboxed(frame, placeholder)
            self.frames_scaled += 1
        elif (frame.width, frame.height) == (output_width, output_height):
            self._last_phone = self._converted(frame, output_width, output_height)
        else:
            return
        self._last_phone_at = now

    def _pillarboxed(self, frame: VideoFrame, placeholder: I420Frame) -> I420Frame:
        _, output_height = frame_size(placeholder)
        width = even(frame.width * output_height / frame.height)
        reduced = self._converted(frame, width, output_height)
        canvas = placeholder.copy()
        paste_i420(canvas, reduced, width, output_height)
        return canvas

    def _converted(self, frame: VideoFrame, width: int, height: int) -> I420Frame:
        return i420_array(frame, width, height, self.color_range, self.color_tables(), mirror=self.mirror)


def i420_array(
    frame: VideoFrame,
    width: int,
    height: int,
    color_range: ColorRange,
    tables: ColorTables | None = None,
    *,
    mirror: bool = False,
) -> I420Frame:
    source = reformatted(frame, width, height, color_range)
    if tables is not None or mirror:
        return copied_i420(source, tables, mirror=mirror)
    array: I420Frame = np.ascontiguousarray(source.to_ndarray(), dtype=np.uint8)
    return array


def reformatted(frame: VideoFrame, width: int, height: int, color_range: ColorRange) -> VideoFrame:
    if frame.format.name in RAW_I420_FORMATS and (frame.width, frame.height) == (width, height):
        return frame
    kept_range = DeclaredRange.JPEG if color_range is ColorRange.FULL else DeclaredRange.MPEG
    return frame.reformat(
        width=width,
        height=height,
        format=I420_FORMAT,
        interpolation=REDUCTION_INTERPOLATION,
        src_color_range=kept_range,
        dst_color_range=kept_range,
    )


def copied_i420(frame: VideoFrame, tables: ColorTables | None, *, mirror: bool) -> I420Frame:
    output = np.empty(frame.width * frame.height * 3 // 2, dtype=np.uint8)
    columns = MIRRORED_COLUMNS if mirror else ALL_COLUMNS
    offset = 0
    for plane, table in zip(frame.planes, plane_tables(tables), strict=True):
        size = plane.width * plane.height
        rows = plane_rows(plane, table)[: plane.height, : plane.width]
        output[offset : offset + size].reshape(plane.height, plane.width)[:] = rows[:, columns]
        offset += size
    return output.reshape(frame.height * 3 // 2, frame.width)


def plane_tables(tables: ColorTables | None) -> tuple[bytes | None, bytes | None, bytes | None]:
    if tables is None:
        return None, None, None
    luma_table, chroma_table = tables
    return luma_table, chroma_table, chroma_table


def plane_rows(plane: VideoPlane, table: bytes | None) -> I420Frame:
    # bytes.translate reads a 256 entry table in C, about five times faster here than numpy.take.
    data = memoryview(plane) if table is None else bytes(plane).translate(table)
    rows: I420Frame = np.frombuffer(data, dtype=np.uint8).reshape(-1, plane.line_size)
    return rows


def fits(frame: I420Frame | None, placeholder: I420Frame) -> bool:
    return frame is not None and frame.shape == placeholder.shape


def even(value: float) -> int:
    return max(2, round(value / 2) * 2)


def paste_i420(canvas: I420Frame, image: I420Frame, width: int, height: int) -> None:
    canvas_width, canvas_height = frame_size(canvas)
    top = even((canvas_height - height) / 2) if height < canvas_height else 0
    left = even((canvas_width - width) / 2) if width < canvas_width else 0
    for canvas_plane, image_plane, divisor in zip(
        i420_planes(canvas, canvas_width, canvas_height),
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

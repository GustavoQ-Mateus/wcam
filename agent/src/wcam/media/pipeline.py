import asyncio
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from enum import StrEnum

import numpy as np
from av import VideoFrame
from av.video.plane import VideoPlane
from av.video.reformatter import ColorRange as DeclaredRange

from wcam.diagnostics.stage_times import Stage, StageTimes
from wcam.media.color_correction import ColorCorrection, ColorTables, CorrectionState, correction_tables
from wcam.media.color_range import (
    UNSPECIFIED_MATRIX,
    ColorRange,
    declared_matrix,
    declared_range,
)
from wcam.media.episodes import FrameGap
from wcam.media.placeholder import black_nv12, camera_off_nv12
from wcam.media.plane_translation import PlaneTranslator
from wcam.media.quality import QualityMeter, QualityReport
from wcam.media.video_format import DEFAULT_VIDEO_FORMAT
from wcam.process_priority import join_capture_task
from wcam.virtualcam.sink import AnnouncedFormat, CameraState, Nv12Frame, VirtualCameraSink, frame_size

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
MILLISECONDS_PER_SECOND = 1000
MIRRORED_COLUMNS = slice(None, None, -1)


class FrameSource(StrEnum):
    PHONE = "phone"
    VIDEO = "video"
    FROZEN = "frozen"
    HELD = "held"
    CAMERA_OFF = "camera_off"
    PLACEHOLDER = "placeholder"


@dataclass(frozen=True, slots=True)
class VideoImageFrame:
    image: Nv12Frame
    replace_held: bool


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
        self._placeholder = black_nv12(DEFAULT_OUTPUT.width, DEFAULT_OUTPUT.height)
        self._pending: asyncio.Queue[tuple[VideoFrame | VideoImageFrame, float]] = asyncio.Queue(maxsize=1)
        self._worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix=WORKER_NAME, initializer=join_capture_task)
        self._quality_worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix=QUALITY_WORKER_NAME)
        self._measuring: Future[None] | None = None
        self._measured_correction = CorrectionState.DEFAULT
        self._phone_active = False
        self._video_active = False
        self._last_video: Nv12Frame | None = None
        self._last_phone: Nv12Frame | None = None
        self._last_phone_at: float | None = None
        self.portrait = False
        self.source = FrameSource.PLACEHOLDER
        self.frames_scaled = 0
        self.color_range = ColorRange.UNSPECIFIED
        self.color_matrix = UNSPECIFIED_MATRIX
        self.frozen = False
        self.camera_off = False
        self.mirror = False
        self._last_sent: Nv12Frame | None = None
        self._camera_off_frame: Nv12Frame | None = None
        self._source_listeners: list[Callable[[], None]] = []
        self.stage_times = StageTimes()
        self.frames_delivered = 0
        self.frames_dropped = 0
        self._gap_lock = threading.Lock()
        self._longest_gap: FrameGap | None = None
        self._translator = PlaneTranslator()

    @property
    def last_sent(self) -> Nv12Frame | None:
        return self._last_sent

    @property
    def video_active(self) -> bool:
        return self._video_active

    @property
    def placeholder(self) -> Nv12Frame:
        return self._placeholder

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
            self._placeholder = black_nv12(announced.width, announced.height)
        self.output = announced

    async def request_format(self, width: int, height: int, fps: int) -> bool:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._worker, self._change_format, width, height, fps)

    def start_phone(self) -> None:
        self.frames_scaled = 0
        self.frames_delivered = 0
        self.frames_dropped = 0
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

    def start_video(self) -> None:
        self.frames_delivered = 0
        self.frames_dropped = 0
        self._last_video = None
        self._last_phone = None
        self._last_phone_at = None
        self._video_active = True

    def stop_video(self) -> None:
        self._video_active = False
        self._last_video = None
        self._last_phone_at = None

    def submit_video(self, image: Nv12Frame, *, replace_held: bool = False) -> None:
        self._enqueue(VideoImageFrame(image, replace_held))

    def record_stage(self, stage: Stage, milliseconds: float) -> None:
        self.stage_times.record(stage, milliseconds)

    def on_source_change(self, listener: Callable[[], None]) -> None:
        self._source_listeners.append(listener)

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

    def take_longest_gap(self) -> FrameGap | None:
        with self._gap_lock:
            gap, self._longest_gap = self._longest_gap, None
        return gap

    def submit(self, frame: VideoFrame) -> None:
        self._enqueue(frame)

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        try:
            while True:
                frame, submitted_at = await self._next_frame()
                await loop.run_in_executor(self._worker, self.deliver, frame, submitted_at)
        finally:
            self._worker.shutdown(wait=True)
            self._quality_worker.shutdown(wait=True)
            self.sink.close()

    def deliver(self, frame: VideoFrame | VideoImageFrame | None, submitted_at: float | None = None) -> None:
        now = self._clock()
        placeholder = self._placeholder
        if isinstance(frame, VideoImageFrame):
            self._accept_video_frame(frame)
        elif frame is not None:
            started = time.perf_counter()
            self._accept_phone_frame(frame, now, placeholder)
            self.stage_times.record(Stage.COLOR, elapsed_since(started))
        elif self._last_phone_at is None or now - self._last_phone_at > FREEZE_SECONDS:
            self._last_phone = None
        output = self._current_output(placeholder)
        source, sent = self._chosen_frame(output, now, placeholder)
        self._report_source(source)
        self._last_sent = sent
        if self.sink.status.state is CameraState.ACTIVE:
            sending = time.perf_counter()
            self.sink.send(sent)
            self.stage_times.record(Stage.DELIVER, elapsed_since(sending))
        if output is None or sent is not output or frame is None:
            return
        self.frames_delivered += 1
        if submitted_at is not None:
            self.stage_times.record(Stage.TOTAL, elapsed_since(submitted_at))
        if not self._video_active:
            self._measure(now, output)

    def _enqueue(self, frame: VideoFrame | VideoImageFrame) -> None:
        if self._pending.full():
            self._pending.get_nowait()
            self.frames_dropped += 1
        self._pending.put_nowait((frame, time.perf_counter()))

    def _current_output(self, placeholder: Nv12Frame) -> Nv12Frame | None:
        if self._video_active:
            return self._last_video if fits(self._last_video, placeholder) else None
        return self._last_phone if self._phone_active and fits(self._last_phone, placeholder) else None

    def _accept_video_frame(self, frame: VideoImageFrame) -> None:
        self._last_video = mirrored_nv12(frame.image) if self.mirror else frame.image
        if frame.replace_held and self.frozen:
            self._last_sent = self._last_video

    def _change_format(self, width: int, height: int, fps: int) -> bool:
        accepted = self.sink.request_format(width, height, fps)
        self.follow(self.sink.announced_format())
        return accepted

    def _chosen_frame(
        self, output: Nv12Frame | None, now: float, placeholder: Nv12Frame
    ) -> tuple[FrameSource, Nv12Frame]:
        if self.camera_off:
            return FrameSource.CAMERA_OFF, self._camera_off_like(placeholder)
        if self.frozen and self._last_sent is not None and fits(self._last_sent, placeholder):
            return FrameSource.HELD, self._last_sent
        return self._source_of(output, now), placeholder if output is None else output

    def _report_source(self, source: FrameSource) -> None:
        if source is self.source:
            return
        self.source = source
        for listener in self._source_listeners:
            listener()

    def _camera_off_like(self, placeholder: Nv12Frame) -> Nv12Frame:
        if self._camera_off_frame is None or not fits(self._camera_off_frame, placeholder):
            self._camera_off_frame = camera_off_nv12(*frame_size(placeholder))
        return self._camera_off_frame

    def _source_of(self, output: Nv12Frame | None, now: float) -> FrameSource:
        if output is None:
            return FrameSource.PLACEHOLDER
        if self._video_active:
            return FrameSource.VIDEO
        if self._last_phone_at is not None and now - self._last_phone_at > STALE_FRAME_SECONDS:
            return FrameSource.FROZEN
        return FrameSource.PHONE

    def _measure(self, now: float, output: Nv12Frame) -> None:
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

    async def _next_frame(self) -> tuple[VideoFrame | VideoImageFrame | None, float | None]:
        try:
            return await asyncio.wait_for(self._pending.get(), 1 / self.output.fps)
        except TimeoutError:
            return None, None

    def _accept_phone_frame(self, frame: VideoFrame, now: float, placeholder: Nv12Frame) -> None:
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
        self._record_gap(now)
        self._last_phone_at = now

    def _record_gap(self, now: float) -> None:
        if self._last_phone_at is None:
            return
        gap = FrameGap(now - self._last_phone_at, now)
        with self._gap_lock:
            if self._longest_gap is None or gap.seconds > self._longest_gap.seconds:
                self._longest_gap = gap

    def _pillarboxed(self, frame: VideoFrame, placeholder: Nv12Frame) -> Nv12Frame:
        _, output_height = frame_size(placeholder)
        width = even(frame.width * output_height / frame.height)
        reduced = self._converted(frame, width, output_height)
        canvas = placeholder.copy()
        paste_nv12(canvas, reduced, width, output_height)
        return canvas

    def _converted(self, frame: VideoFrame, width: int, height: int) -> Nv12Frame:
        tables = self.color_tables()
        return nv12_frame(
            frame, width, height, self.color_range, tables, mirror=self.mirror, translator=self._translator
        )


def mirrored_nv12(image: Nv12Frame) -> Nv12Frame:
    width, height = frame_size(image)
    mirrored = np.empty_like(image)
    for target, source in zip(nv12_planes(mirrored, width, height), nv12_planes(image, width, height), strict=True):
        target[:] = source[:, MIRRORED_COLUMNS]
    return mirrored


def nv12_frame(
    frame: VideoFrame,
    width: int,
    height: int,
    color_range: ColorRange,
    tables: ColorTables | None = None,
    *,
    mirror: bool = False,
    translator: PlaneTranslator | None = None,
) -> Nv12Frame:
    source = reformatted(frame, width, height, color_range)
    return (translator or PlaneTranslator()).translated(source, tables, mirror=mirror)


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


def plane_rows(plane: VideoPlane, table: bytes | None) -> Nv12Frame:
    # bytes.translate reads a 256 entry table in C, about five times faster here than numpy.take.
    data = memoryview(plane) if table is None else bytes(plane).translate(table)
    rows: Nv12Frame = np.frombuffer(data, dtype=np.uint8).reshape(-1, plane.line_size)
    return rows


def elapsed_since(started: float) -> float:
    return (time.perf_counter() - started) * MILLISECONDS_PER_SECOND


def fits(frame: Nv12Frame | None, placeholder: Nv12Frame) -> bool:
    return frame is not None and frame.shape == placeholder.shape


def even(value: float) -> int:
    return max(2, round(value / 2) * 2)


def paste_nv12(canvas: Nv12Frame, image: Nv12Frame, width: int, height: int) -> None:
    canvas_width, canvas_height = frame_size(canvas)
    top = even((canvas_height - height) / 2) if height < canvas_height else 0
    left = even((canvas_width - width) / 2) if width < canvas_width else 0
    for canvas_plane, image_plane, divisor in zip(
        nv12_planes(canvas, canvas_width, canvas_height),
        nv12_planes(image, width, height),
        (1, 2, 2),
        strict=True,
    ):
        row = top // divisor
        column = left // divisor
        canvas_plane[row : row + height // divisor, column : column + width // divisor] = image_plane


def nv12_planes(frame: Nv12Frame, width: int, height: int) -> tuple[Nv12Frame, Nv12Frame, Nv12Frame]:
    flat = frame.reshape(-1)
    luma_size = width * height
    luma = flat[:luma_size].reshape(height, width)
    chroma = flat[luma_size : luma_size + luma_size // 2].reshape(height // 2, width // 2, 2)
    return luma, chroma[:, :, 0], chroma[:, :, 1]

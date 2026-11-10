import asyncio
import ctypes
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import numpy as np
import pytest

from wcam.config import Settings
from wcam.media.pipeline import FramePipeline
from wcam.virtualcam.factory import FallbackReason, SinkChoice, select_sink
from wcam.virtualcam.fake_sink import FakeSink
from wcam.virtualcam.media_foundation_sink import (
    CameraLibrary,
    FormatState,
    IncompleteCameraLibrary,
    MediaFoundationSink,
    NativeCameraLibrary,
    Nv12Frame,
    i420_to_nv12,
    load_native_library,
)
from wcam.virtualcam.pyvirtualcam_sink import PyvirtualcamSink
from wcam.virtualcam.sink import (
    OUTPUT_FPS,
    OUTPUT_HEIGHT,
    OUTPUT_WIDTH,
    AnnouncedFormat,
    CameraState,
    I420Frame,
    UnavailableReason,
)

S_OK = 0
S_FALSE = 1
E_FAIL = -2147467259
SEED = 5
SMALL_WIDTH = 8
SMALL_HEIGHT = 4
WINDOWS_11_BUILD = 26200
WINDOWS_10_BUILD = 19045
PIPELINE_RUN_SECONDS = 0.2
REAL_VCAM_VARIABLE = "WCAM_TEST_REAL_VCAM"


@dataclass
class FakeCameraLibrary:
    start_result: int = S_OK
    publish_result: int = S_OK
    format_result: int = S_OK
    started: int = 0
    stopped: int = 0
    published: list[tuple[bytes, int, int]] = field(default_factory=list[tuple[bytes, int, int]])
    formats: list[tuple[int, int, int]] = field(default_factory=list[tuple[int, int, int]])
    announced: AnnouncedFormat | None = None

    def start(self) -> int:
        self.started += 1
        return self.start_result

    def stop(self) -> int:
        self.stopped += 1
        return S_OK

    def publish(self, frame: Nv12Frame, width: int, height: int) -> int:
        self.published.append((frame.tobytes(), width, height))
        return self.publish_result

    def set_format(self, width: int, height: int, fps: int) -> int:
        self.formats.append((width, height, fps))
        return self.format_result

    def get_format(self) -> AnnouncedFormat | None:
        return self.announced


def random_i420(width: int, height: int) -> I420Frame:
    generator = np.random.default_rng(SEED)
    return generator.integers(0, 256, size=(height * 3 // 2, width), dtype=np.uint8)


def converted(frame: I420Frame, width: int, height: int) -> Nv12Frame:
    output = np.empty(width * height * 3 // 2, dtype=np.uint8)
    i420_to_nv12(frame, width, height, output)
    return output


def test_nv12_keeps_luma_bytes_unchanged() -> None:
    frame = random_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT)

    nv12 = converted(frame, OUTPUT_WIDTH, OUTPUT_HEIGHT)

    luma_size = OUTPUT_WIDTH * OUTPUT_HEIGHT
    assert nv12[:luma_size].tobytes() == frame.reshape(-1)[:luma_size].tobytes()


def test_nv12_interleaves_each_chroma_pair_in_place() -> None:
    frame = random_i420(SMALL_WIDTH, SMALL_HEIGHT)
    luma_size = SMALL_WIDTH * SMALL_HEIGHT
    chroma_size = luma_size // 4
    flat = frame.reshape(-1)
    blue = flat[luma_size : luma_size + chroma_size].reshape(SMALL_HEIGHT // 2, SMALL_WIDTH // 2)
    red = flat[luma_size + chroma_size :].reshape(SMALL_HEIGHT // 2, SMALL_WIDTH // 2)

    pairs = converted(frame, SMALL_WIDTH, SMALL_HEIGHT)[luma_size:].reshape(SMALL_HEIGHT // 2, SMALL_WIDTH // 2, 2)

    assert (pairs[:, :, 0] == blue).all()
    assert (pairs[:, :, 1] == red).all()


def test_open_starts_the_native_camera() -> None:
    library = FakeCameraLibrary()
    sink = MediaFoundationSink(library)

    sink.open(OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS)
    sink.open(OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS)

    assert sink.status.state is CameraState.ACTIVE
    assert (sink.backend, sink.name, library.started) == ("media_foundation", "WCam", 1)


def test_send_publishes_nv12_with_output_size() -> None:
    library = FakeCameraLibrary(publish_result=S_FALSE)
    sink = MediaFoundationSink(library)
    sink.open(OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS)
    frame = random_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT)

    sink.send(frame)

    assert library.published == [(converted(frame, OUTPUT_WIDTH, OUTPUT_HEIGHT).tobytes(), OUTPUT_WIDTH, OUTPUT_HEIGHT)]


def test_close_stops_the_native_camera() -> None:
    library = FakeCameraLibrary()
    sink = MediaFoundationSink(library)
    sink.open(OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS)

    sink.close()
    sink.close()

    assert library.stopped == 1
    assert sink.status.state is CameraState.UNAVAILABLE


def test_failed_start_is_unavailable_with_error() -> None:
    sink = MediaFoundationSink(FakeCameraLibrary(start_result=E_FAIL))

    sink.open(OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS)
    sink.send(random_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT))
    sink.close()

    assert (sink.status.state, sink.status.reason) == (CameraState.UNAVAILABLE, UnavailableReason.ERROR)


def test_missing_library_is_unavailable_with_driver_missing() -> None:
    sink = MediaFoundationSink(None)

    sink.open(OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS)

    assert (sink.status.state, sink.status.reason) == (CameraState.UNAVAILABLE, UnavailableReason.DRIVER_MISSING)


def test_missing_dll_file_loads_nothing(tmp_path: Path) -> None:
    assert load_native_library(tmp_path / "Wcam.VirtualCamera.dll") is None


class RecordingExport:
    def __init__(self, result: int, record: Callable[..., None]) -> None:
        self.argtypes: list[object] = []
        self.restype: object = None
        self._result = result
        self._record = record

    def __call__(self, *arguments: object) -> int:
        self._record(*arguments)
        return self._result


def test_native_library_passes_frame_pointer_length_and_size() -> None:
    calls: list[tuple[bytes, int, int, int]] = []

    def record_publish(pointer: object, length: int, width: int, height: int) -> None:
        address = ctypes.cast(cast(ctypes.c_void_p, pointer), ctypes.c_void_p).value or 0
        calls.append((ctypes.string_at(address, length), length, width, height))

    exports = {
        "WcamCameraStart": RecordingExport(S_OK, lambda: None),
        "WcamCameraStop": RecordingExport(S_OK, lambda: None),
        "WcamFramePublish": RecordingExport(S_FALSE, record_publish),
        "WcamFormatSet": RecordingExport(S_OK, ignore_format),
        "WcamFormatGet": RecordingExport(S_OK, ignore_state),
    }
    library = NativeCameraLibrary(cast(ctypes.CDLL, type("Dll", (), exports)()))
    frame = np.arange(SMALL_WIDTH * SMALL_HEIGHT * 3 // 2, dtype=np.uint8)

    result = library.publish(frame, SMALL_WIDTH, SMALL_HEIGHT)

    assert result == S_FALSE
    assert calls == [(frame.tobytes(), frame.size, SMALL_WIDTH, SMALL_HEIGHT)]
    assert exports["WcamFramePublish"].restype is ctypes.c_int32


def ignore_format(width: int, height: int, fps: int) -> None:
    return None


def ignore_state(pointer: object) -> None:
    return None


def ignore_publish(pointer: object, length: int, width: int, height: int) -> None:
    return None


def library_loader(library: CameraLibrary | None) -> Callable[[], CameraLibrary | None]:
    return lambda: library


def test_auto_outside_windows_uses_fake_with_not_windows() -> None:
    selection = select_sink("auto", library_loader(FakeCameraLibrary()), platform="linux", windows_build=0)

    assert isinstance(selection.sink, FakeSink)
    assert selection.fallback_reason is FallbackReason.NOT_WINDOWS


def test_auto_on_old_windows_uses_obs_with_windows_too_old() -> None:
    selection = select_sink(
        "auto", library_loader(FakeCameraLibrary()), platform="win32", windows_build=WINDOWS_10_BUILD
    )

    assert isinstance(selection.sink, PyvirtualcamSink)
    assert selection.fallback_reason is FallbackReason.WINDOWS_TOO_OLD


def test_auto_without_dll_uses_obs_with_native_not_registered() -> None:
    selection = select_sink("auto", library_loader(None), platform="win32", windows_build=WINDOWS_11_BUILD)

    assert isinstance(selection.sink, PyvirtualcamSink)
    assert selection.fallback_reason is FallbackReason.NATIVE_NOT_REGISTERED


def test_auto_with_failing_dll_uses_obs_with_native_error() -> None:
    library = FakeCameraLibrary(start_result=E_FAIL)

    selection = select_sink("auto", library_loader(library), platform="win32", windows_build=WINDOWS_11_BUILD)

    assert isinstance(selection.sink, PyvirtualcamSink)
    assert selection.fallback_reason is FallbackReason.NATIVE_ERROR


def test_auto_with_working_dll_uses_the_native_camera() -> None:
    library = FakeCameraLibrary()

    selection = select_sink("auto", library_loader(library), platform="win32", windows_build=WINDOWS_11_BUILD)

    assert isinstance(selection.sink, MediaFoundationSink)
    assert selection.sink.status.state is CameraState.ACTIVE
    assert selection.fallback_reason is None


@pytest.mark.parametrize(
    ("choice", "sink_type"),
    [("fake", FakeSink), ("obs", PyvirtualcamSink), ("media_foundation", MediaFoundationSink)],
)
def test_explicit_backend_has_no_fallback_reason(choice: SinkChoice, sink_type: type) -> None:
    selection = select_sink(choice, library_loader(None), platform="win32", windows_build=WINDOWS_11_BUILD)

    assert isinstance(selection.sink, sink_type)
    assert selection.fallback_reason is None


async def test_stopping_the_pipeline_removes_the_native_camera() -> None:
    library = FakeCameraLibrary()
    pipeline = FramePipeline(MediaFoundationSink(library))
    pipeline.open()

    task = asyncio.create_task(pipeline.run())
    await asyncio.sleep(PIPELINE_RUN_SECONDS)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert library.published
    assert library.stopped == 1


@pytest.mark.skipif(os.environ.get(REAL_VCAM_VARIABLE) != "1", reason="creates the WCam camera on this computer")
def test_real_dll_starts_publishes_and_stops_the_camera() -> None:
    library = load_native_library(Settings().vcam_dll)
    assert library is not None
    sink = MediaFoundationSink(library)

    sink.open(OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS)
    published = library.publish(
        converted(random_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT), OUTPUT_WIDTH, OUTPUT_HEIGHT), OUTPUT_WIDTH, OUTPUT_HEIGHT
    )
    sink.close()

    assert sink.status.state is CameraState.UNAVAILABLE
    assert published in (S_OK, S_FALSE)


def test_open_announces_the_format_to_the_native_camera() -> None:
    library = FakeCameraLibrary()
    sink = MediaFoundationSink(library)

    sink.open(1280, 720, 60)

    assert library.formats == [(1280, 720, 60)]
    assert sink.status.state is CameraState.ACTIVE


def test_format_request_is_passed_on_and_publishing_follows_the_frame_size() -> None:
    library = FakeCameraLibrary()
    sink = MediaFoundationSink(library)
    sink.open(OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS)

    accepted = sink.request_format(SMALL_WIDTH, SMALL_HEIGHT, 60)
    sink.send(random_i420(SMALL_WIDTH, SMALL_HEIGHT))

    assert accepted
    assert library.formats[-1] == (SMALL_WIDTH, SMALL_HEIGHT, 60)
    assert library.published[-1][1:] == (SMALL_WIDTH, SMALL_HEIGHT)


def test_refused_format_request_is_reported() -> None:
    library = FakeCameraLibrary()
    sink = MediaFoundationSink(library)
    sink.open(OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS)
    library.format_result = E_FAIL

    assert not sink.request_format(SMALL_WIDTH, SMALL_HEIGHT, 60)


def test_announced_format_comes_from_the_native_camera() -> None:
    library = FakeCameraLibrary()
    sink = MediaFoundationSink(library)
    sink.open(OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS)
    pending = AnnouncedFormat(OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS, pending=True, running=True)

    opened = sink.announced_format()
    library.announced = pending

    assert opened == AnnouncedFormat(OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS, pending=False, running=True)
    assert sink.announced_format() == pending
    assert sink.reports_format_changes


def test_unreadable_format_keeps_the_last_announced() -> None:
    library = FakeCameraLibrary()
    sink = MediaFoundationSink(library)
    sink.open(OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS)
    library.announced = AnnouncedFormat(SMALL_WIDTH, SMALL_HEIGHT, 60, pending=False, running=True)
    sink.announced_format()
    library.announced = None

    assert sink.announced_format() == AnnouncedFormat(SMALL_WIDTH, SMALL_HEIGHT, 60, pending=False, running=True)


def test_native_library_reads_the_format_state_structure() -> None:
    def fill_state(pointer: object) -> None:
        state = ctypes.cast(cast(ctypes.c_void_p, pointer), ctypes.POINTER(FormatState)).contents
        state.width, state.height, state.fps = 1280, 720, 30
        state.requested_width, state.requested_height, state.requested_fps = 1920, 1080, 30
        state.pending, state.streaming_apps, state.running = 1, 2, 1

    exports = {
        "WcamCameraStart": RecordingExport(S_OK, lambda: None),
        "WcamCameraStop": RecordingExport(S_OK, lambda: None),
        "WcamFramePublish": RecordingExport(S_OK, ignore_publish),
        "WcamFormatSet": RecordingExport(S_OK, ignore_format),
        "WcamFormatGet": RecordingExport(S_OK, fill_state),
    }
    library = NativeCameraLibrary(cast(ctypes.CDLL, type("Dll", (), exports)()))

    assert library.get_format() == AnnouncedFormat(1280, 720, 30, pending=True, running=True)


def test_refused_first_format_makes_the_camera_unavailable_with_error() -> None:
    sink = MediaFoundationSink(FakeCameraLibrary(format_result=E_FAIL))

    sink.open(OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS)

    assert (sink.status.state, sink.status.reason) == (CameraState.UNAVAILABLE, UnavailableReason.ERROR)


def test_native_library_passes_width_height_and_fps_to_format_set() -> None:
    calls: list[tuple[int, int, int]] = []

    def record_format(width: int, height: int, fps: int) -> None:
        calls.append((width, height, fps))

    exports = {
        "WcamCameraStart": RecordingExport(S_OK, lambda: None),
        "WcamCameraStop": RecordingExport(S_OK, lambda: None),
        "WcamFramePublish": RecordingExport(S_OK, ignore_publish),
        "WcamFormatSet": RecordingExport(S_OK, record_format),
        "WcamFormatGet": RecordingExport(S_OK, ignore_state),
    }
    library = NativeCameraLibrary(cast(ctypes.CDLL, type("Dll", (), exports)()))

    result = library.set_format(3840, 2160, 30)

    assert result == S_OK
    assert calls == [(3840, 2160, 30)]
    assert exports["WcamFormatSet"].restype is ctypes.c_int32


def test_auto_with_dll_missing_format_set_uses_obs_with_native_error() -> None:
    selection = select_sink("auto", library_loader(IncompleteCameraLibrary()), "win32", WINDOWS_11_BUILD)

    assert selection.fallback_reason is FallbackReason.NATIVE_ERROR
    assert isinstance(selection.sink, PyvirtualcamSink)


def test_explicit_native_camera_with_dll_missing_format_set_is_unavailable_with_error() -> None:
    selection = select_sink("media_foundation", library_loader(IncompleteCameraLibrary()), "win32", WINDOWS_11_BUILD)
    selection.sink.open(OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS)

    assert selection.fallback_reason is None
    assert (selection.sink.status.state, selection.sink.status.reason) == (
        CameraState.UNAVAILABLE,
        UnavailableReason.ERROR,
    )


@pytest.mark.skipif(os.name != "nt", reason="needs a Windows system DLL")
def test_dll_without_the_wcam_exports_loads_as_incomplete() -> None:
    system_dll = Path(os.environ.get("SYSTEMROOT", r"C:\Windows")) / "System32" / "kernel32.dll"

    assert isinstance(load_native_library(system_dll), IncompleteCameraLibrary)

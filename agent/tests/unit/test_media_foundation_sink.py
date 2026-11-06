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
    MediaFoundationSink,
    NativeCameraLibrary,
    Nv12Frame,
    i420_to_nv12,
    load_native_library,
)
from wcam.virtualcam.pyvirtualcam_sink import PyvirtualcamSink
from wcam.virtualcam.sink import OUTPUT_FPS, OUTPUT_HEIGHT, OUTPUT_WIDTH, CameraState, I420Frame, UnavailableReason

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
    started: int = 0
    stopped: int = 0
    published: list[tuple[bytes, int, int]] = field(default_factory=list[tuple[bytes, int, int]])

    def start(self) -> int:
        self.started += 1
        return self.start_result

    def stop(self) -> int:
        self.stopped += 1
        return S_OK

    def publish(self, frame: Nv12Frame, width: int, height: int) -> int:
        self.published.append((frame.tobytes(), width, height))
        return self.publish_result


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
    }
    library = NativeCameraLibrary(cast(ctypes.CDLL, type("Dll", (), exports)()))
    frame = np.arange(SMALL_WIDTH * SMALL_HEIGHT * 3 // 2, dtype=np.uint8)

    result = library.publish(frame, SMALL_WIDTH, SMALL_HEIGHT)

    assert result == S_FALSE
    assert calls == [(frame.tobytes(), frame.size, SMALL_WIDTH, SMALL_HEIGHT)]
    assert exports["WcamFramePublish"].restype is ctypes.c_int32


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

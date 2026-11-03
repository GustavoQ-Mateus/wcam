import sys
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from wcam.virtualcam.fake_sink import FakeSink
from wcam.virtualcam.media_foundation_sink import CameraLibrary, MediaFoundationSink
from wcam.virtualcam.pyvirtualcam_sink import PyvirtualcamSink
from wcam.virtualcam.sink import OUTPUT_FPS, OUTPUT_HEIGHT, OUTPUT_WIDTH, CameraState, VirtualCameraSink

MINIMUM_NATIVE_WINDOWS_BUILD = 22000
WINDOWS_PLATFORM = "win32"

type SinkChoice = Literal["auto", "media_foundation", "obs", "fake"]


class FallbackReason(StrEnum):
    NATIVE_NOT_REGISTERED = "native_not_registered"
    WINDOWS_TOO_OLD = "windows_too_old"
    NATIVE_ERROR = "native_error"
    NOT_WINDOWS = "not_windows"


@dataclass(frozen=True, slots=True)
class SinkSelection:
    sink: VirtualCameraSink
    fallback_reason: FallbackReason | None = None


def select_sink(
    choice: SinkChoice,
    load_library: Callable[[], CameraLibrary | None],
    platform: str = sys.platform,
    windows_build: int | None = None,
) -> SinkSelection:
    if choice == "fake":
        return SinkSelection(FakeSink())
    if choice == "obs":
        return SinkSelection(PyvirtualcamSink())
    if choice == "media_foundation":
        return SinkSelection(MediaFoundationSink(load_library()))
    return select_automatically(
        load_library, platform, current_windows_build() if windows_build is None else windows_build
    )


def select_automatically(
    load_library: Callable[[], CameraLibrary | None],
    platform: str,
    windows_build: int,
) -> SinkSelection:
    if platform != WINDOWS_PLATFORM:
        return SinkSelection(FakeSink(), FallbackReason.NOT_WINDOWS)
    if windows_build < MINIMUM_NATIVE_WINDOWS_BUILD:
        return SinkSelection(PyvirtualcamSink(), FallbackReason.WINDOWS_TOO_OLD)
    library = load_library()
    if library is None:
        return SinkSelection(PyvirtualcamSink(), FallbackReason.NATIVE_NOT_REGISTERED)
    native = MediaFoundationSink(library)
    native.open(OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS)
    if native.status.state is not CameraState.ACTIVE:
        return SinkSelection(PyvirtualcamSink(), FallbackReason.NATIVE_ERROR)
    return SinkSelection(native)


def current_windows_build() -> int:
    if sys.platform == "win32":
        return sys.getwindowsversion().build
    return 0

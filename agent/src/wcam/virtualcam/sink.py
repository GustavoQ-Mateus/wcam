from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080
OUTPUT_FPS = 30

type I420Frame = NDArray[np.uint8]


class CameraState(StrEnum):
    ACTIVE = "active"
    UNAVAILABLE = "unavailable"


class UnavailableReason(StrEnum):
    DRIVER_MISSING = "driver_missing"
    DEVICE_IN_USE = "device_in_use"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class SinkStatus:
    state: CameraState
    reason: UnavailableReason | None = None


UNAVAILABLE_UNTIL_OPENED = SinkStatus(CameraState.UNAVAILABLE, UnavailableReason.ERROR)


@dataclass(frozen=True, slots=True)
class AnnouncedFormat:
    width: int
    height: int
    fps: int
    pending: bool
    running: bool
    streaming_apps: int | None = None


def frame_size(frame: I420Frame) -> tuple[int, int]:
    return int(frame.shape[1]), int(frame.shape[0]) * 2 // 3


class VirtualCameraSink(Protocol):
    @property
    def backend(self) -> str: ...

    @property
    def name(self) -> str: ...

    @property
    def status(self) -> SinkStatus: ...

    @property
    def reports_format_changes(self) -> bool: ...

    def open(self, width: int, height: int, fps: int) -> None: ...

    def request_format(self, width: int, height: int, fps: int) -> bool: ...

    def announced_format(self) -> AnnouncedFormat | None: ...

    def send(self, frame: I420Frame) -> None: ...

    def close(self) -> None: ...

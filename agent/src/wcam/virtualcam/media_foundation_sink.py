import ctypes
from pathlib import Path
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from wcam.virtualcam.sink import (
    UNAVAILABLE_UNTIL_OPENED,
    CameraState,
    I420Frame,
    SinkStatus,
    UnavailableReason,
)

BACKEND = "media_foundation"
CAMERA_NAME = "WCam"
FIRST_FAILURE_HRESULT = 0

type Nv12Frame = NDArray[np.uint8]


class CameraLibrary(Protocol):
    def start(self) -> int: ...

    def stop(self) -> int: ...

    def publish(self, frame: Nv12Frame, width: int, height: int) -> int: ...


class NativeCameraLibrary:
    def __init__(self, library: ctypes.CDLL) -> None:
        self._start = library.WcamCameraStart
        self._start.argtypes = []
        self._start.restype = ctypes.c_int32
        self._stop = library.WcamCameraStop
        self._stop.argtypes = []
        self._stop.restype = ctypes.c_int32
        self._publish = library.WcamFramePublish
        self._publish.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32]
        self._publish.restype = ctypes.c_int32

    def start(self) -> int:
        result: int = self._start()
        return result

    def stop(self) -> int:
        result: int = self._stop()
        return result

    def publish(self, frame: Nv12Frame, width: int, height: int) -> int:
        pointer = frame.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
        result: int = self._publish(pointer, frame.size, width, height)
        return result


class MediaFoundationSink:
    def __init__(self, library: CameraLibrary | None) -> None:
        self._library = library
        self._status = UNAVAILABLE_UNTIL_OPENED
        self._nv12: Nv12Frame | None = None
        self._width = 0
        self._height = 0

    @property
    def backend(self) -> str:
        return BACKEND

    @property
    def name(self) -> str:
        return CAMERA_NAME

    @property
    def status(self) -> SinkStatus:
        return self._status

    def open(self, width: int, height: int, fps: int) -> None:
        if self._status.state is CameraState.ACTIVE:
            return
        if self._library is None:
            self._status = SinkStatus(CameraState.UNAVAILABLE, UnavailableReason.DRIVER_MISSING)
            return
        if self._library.start() < FIRST_FAILURE_HRESULT:
            self._status = SinkStatus(CameraState.UNAVAILABLE, UnavailableReason.ERROR)
            return
        self._width = width
        self._height = height
        self._nv12 = np.empty(width * height * 3 // 2, dtype=np.uint8)
        self._status = SinkStatus(CameraState.ACTIVE)

    def send(self, frame: I420Frame) -> None:
        if self._library is None or self._nv12 is None:
            return
        i420_to_nv12(frame, self._width, self._height, self._nv12)
        self._library.publish(self._nv12, self._width, self._height)

    def close(self) -> None:
        if self._library is not None and self._status.state is CameraState.ACTIVE:
            self._library.stop()
        self._nv12 = None
        self._status = UNAVAILABLE_UNTIL_OPENED


def i420_to_nv12(frame: I420Frame, width: int, height: int, output: Nv12Frame) -> None:
    luma_size = width * height
    chroma_size = luma_size // 4
    flat = frame.reshape(-1)
    output[:luma_size] = flat[:luma_size]
    interleaved = output[luma_size:]
    interleaved[0::2] = flat[luma_size : luma_size + chroma_size]
    interleaved[1::2] = flat[luma_size + chroma_size : luma_size + 2 * chroma_size]


def load_native_library(path: Path) -> CameraLibrary | None:
    if not path.is_file():
        return None
    try:
        return NativeCameraLibrary(ctypes.CDLL(str(path)))
    except (OSError, AttributeError):
        return None

import ctypes
import logging
from pathlib import Path
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from wcam.virtualcam.sink import (
    UNAVAILABLE_UNTIL_OPENED,
    AnnouncedFormat,
    CameraState,
    I420Frame,
    SinkStatus,
    UnavailableReason,
    frame_size,
)

BACKEND = "media_foundation"
CAMERA_NAME = "WCam"
FIRST_FAILURE_HRESULT = 0
E_FAIL = -2147467259
FORMAT_REFUSED = "The WCam camera did not accept the new format"

logger = logging.getLogger(__name__)

type Nv12Frame = NDArray[np.uint8]


class FormatState(ctypes.Structure):
    _fields_ = (
        ("width", ctypes.c_uint32),
        ("height", ctypes.c_uint32),
        ("fps", ctypes.c_uint32),
        ("requested_width", ctypes.c_uint32),
        ("requested_height", ctypes.c_uint32),
        ("requested_fps", ctypes.c_uint32),
        ("pending", ctypes.c_uint32),
        ("streaming_apps", ctypes.c_uint32),
        ("running", ctypes.c_uint32),
    )


class CameraLibrary(Protocol):
    def start(self) -> int: ...

    def stop(self) -> int: ...

    def publish(self, frame: Nv12Frame, width: int, height: int) -> int: ...

    def set_format(self, width: int, height: int, fps: int) -> int: ...

    def get_format(self) -> AnnouncedFormat | None: ...


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
        self._format_set = library.WcamFormatSet
        self._format_set.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32]
        self._format_set.restype = ctypes.c_int32
        self._format_get = library.WcamFormatGet
        self._format_get.argtypes = [ctypes.POINTER(FormatState)]
        self._format_get.restype = ctypes.c_int32

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

    def set_format(self, width: int, height: int, fps: int) -> int:
        result: int = self._format_set(width, height, fps)
        return result

    def get_format(self) -> AnnouncedFormat | None:
        state = FormatState()
        result: int = self._format_get(ctypes.byref(state))
        if result < FIRST_FAILURE_HRESULT:
            return None
        return AnnouncedFormat(state.width, state.height, state.fps, bool(state.pending), bool(state.running))


class IncompleteCameraLibrary:
    def start(self) -> int:
        return E_FAIL

    def stop(self) -> int:
        return E_FAIL

    def publish(self, frame: Nv12Frame, width: int, height: int) -> int:
        return E_FAIL

    def set_format(self, width: int, height: int, fps: int) -> int:
        return E_FAIL

    def get_format(self) -> AnnouncedFormat | None:
        return None


class MediaFoundationSink:
    def __init__(self, library: CameraLibrary | None) -> None:
        self._library = library
        self._status = UNAVAILABLE_UNTIL_OPENED
        self._nv12: Nv12Frame | None = None
        self._announced: AnnouncedFormat | None = None

    @property
    def backend(self) -> str:
        return BACKEND

    @property
    def name(self) -> str:
        return CAMERA_NAME

    @property
    def status(self) -> SinkStatus:
        return self._status

    @property
    def reports_format_changes(self) -> bool:
        return True

    def open(self, width: int, height: int, fps: int) -> None:
        if self._status.state is CameraState.ACTIVE:
            return
        if self._library is None:
            self._status = SinkStatus(CameraState.UNAVAILABLE, UnavailableReason.DRIVER_MISSING)
            return
        refused = self._library.set_format(width, height, fps) < FIRST_FAILURE_HRESULT
        if refused or self._library.start() < FIRST_FAILURE_HRESULT:
            self._status = SinkStatus(CameraState.UNAVAILABLE, UnavailableReason.ERROR)
            return
        self._announced = AnnouncedFormat(width, height, fps, pending=False, running=True)
        self._status = SinkStatus(CameraState.ACTIVE)

    def request_format(self, width: int, height: int, fps: int) -> bool:
        if self._library is None or self._status.state is not CameraState.ACTIVE:
            return False
        if self._library.set_format(width, height, fps) < FIRST_FAILURE_HRESULT:
            logger.warning(FORMAT_REFUSED)
            return False
        return True

    def announced_format(self) -> AnnouncedFormat | None:
        if self._library is not None and self._status.state is CameraState.ACTIVE:
            self._announced = self._library.get_format() or self._announced
        return self._announced

    def send(self, frame: I420Frame) -> None:
        if self._library is None or self._status.state is not CameraState.ACTIVE:
            return
        width, height = frame_size(frame)
        buffer_size = width * height * 3 // 2
        if self._nv12 is None or self._nv12.size != buffer_size:
            self._nv12 = np.empty(buffer_size, dtype=np.uint8)
        i420_to_nv12(frame, width, height, self._nv12)
        self._library.publish(self._nv12, width, height)

    def close(self) -> None:
        if self._library is not None and self._status.state is CameraState.ACTIVE:
            self._library.stop()
        self._nv12 = None
        self._announced = None
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
        library = ctypes.CDLL(str(path))
    except OSError:
        return None
    try:
        return NativeCameraLibrary(library)
    except AttributeError:
        return IncompleteCameraLibrary()

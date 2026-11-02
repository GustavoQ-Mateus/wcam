import pyvirtualcam

from wcam.virtualcam.sink import (
    UNAVAILABLE_UNTIL_OPENED,
    CameraState,
    I420Frame,
    SinkStatus,
    UnavailableReason,
)

BACKEND = "obs"
DRIVER_MISSING_MARKER = "device not found"
DEVICE_IN_USE_MARKER = "could not be started"


class PyvirtualcamSink:
    def __init__(self) -> None:
        self._camera: pyvirtualcam.Camera | None = None
        self._status = UNAVAILABLE_UNTIL_OPENED

    @property
    def backend(self) -> str:
        return BACKEND

    @property
    def status(self) -> SinkStatus:
        return self._status

    def open(self, width: int, height: int, fps: int) -> None:
        try:
            self._camera = pyvirtualcam.Camera(width, height, fps, fmt=pyvirtualcam.PixelFormat.I420, backend=BACKEND)
        except (RuntimeError, KeyError) as error:
            self._status = SinkStatus(CameraState.UNAVAILABLE, unavailable_reason(str(error)))
            return
        self._status = SinkStatus(CameraState.ACTIVE)

    def send(self, frame: I420Frame) -> None:
        if self._camera is not None:
            self._camera.send(frame)

    def close(self) -> None:
        if self._camera is not None:
            self._camera.close()
            self._camera = None
        self._status = UNAVAILABLE_UNTIL_OPENED


def unavailable_reason(message: str) -> UnavailableReason:
    if DRIVER_MISSING_MARKER in message:
        return UnavailableReason.DRIVER_MISSING
    if DEVICE_IN_USE_MARKER in message:
        return UnavailableReason.DEVICE_IN_USE
    return UnavailableReason.ERROR

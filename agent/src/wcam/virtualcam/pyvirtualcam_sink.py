import logging

import pyvirtualcam

from wcam.virtualcam.sink import (
    UNAVAILABLE_UNTIL_OPENED,
    AnnouncedFormat,
    CameraState,
    I420Frame,
    SinkStatus,
    UnavailableReason,
)

BACKEND = "obs"
CAMERA_NAME = "OBS Virtual Camera"
DRIVER_MISSING_MARKER = "device not found"
DEVICE_IN_USE_MARKER = "could not be started"
FORMAT_REFUSED = "The OBS Virtual Camera did not accept the new format"

logger = logging.getLogger(__name__)


class PyvirtualcamSink:
    def __init__(self) -> None:
        self._camera: pyvirtualcam.Camera | None = None
        self._status = UNAVAILABLE_UNTIL_OPENED
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
        return False

    def open(self, width: int, height: int, fps: int) -> None:
        try:
            self._camera = pyvirtualcam.Camera(width, height, fps, fmt=pyvirtualcam.PixelFormat.I420, backend=BACKEND)
        except (RuntimeError, KeyError) as error:
            self._status = SinkStatus(CameraState.UNAVAILABLE, unavailable_reason(str(error)))
            return
        self._status = SinkStatus(CameraState.ACTIVE)
        self._announced = AnnouncedFormat(width, height, fps, pending=False, running=True)

    def request_format(self, width: int, height: int, fps: int) -> bool:
        self.close()
        self.open(width, height, fps)
        if self._status.state is not CameraState.ACTIVE:
            logger.warning(FORMAT_REFUSED)
            return False
        return True

    def announced_format(self) -> AnnouncedFormat | None:
        return self._announced

    def send(self, frame: I420Frame) -> None:
        if self._camera is not None:
            self._camera.send(frame)

    def close(self) -> None:
        if self._camera is not None:
            self._camera.close()
            self._camera = None
        self._status = UNAVAILABLE_UNTIL_OPENED
        self._announced = None


def unavailable_reason(message: str) -> UnavailableReason:
    if DRIVER_MISSING_MARKER in message:
        return UnavailableReason.DRIVER_MISSING
    if DEVICE_IN_USE_MARKER in message:
        return UnavailableReason.DEVICE_IN_USE
    return UnavailableReason.ERROR

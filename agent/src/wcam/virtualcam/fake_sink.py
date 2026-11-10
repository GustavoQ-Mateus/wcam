from wcam.virtualcam.sink import (
    UNAVAILABLE_UNTIL_OPENED,
    CameraState,
    I420Frame,
    SinkStatus,
    UnavailableReason,
)


class FakeSink:
    def __init__(self, failure: UnavailableReason | None = None) -> None:
        self._failure = failure
        self._status = UNAVAILABLE_UNTIL_OPENED
        self.frames_sent = 0
        self.last_frame: I420Frame | None = None
        self.formats: list[tuple[int, int, int]] = []
        self.accepts_formats = True

    @property
    def backend(self) -> str:
        return "fake"

    @property
    def name(self) -> str:
        return "fake"

    @property
    def status(self) -> SinkStatus:
        return self._status

    def open(self, width: int, height: int, fps: int) -> None:
        if self._failure is not None:
            self._status = SinkStatus(CameraState.UNAVAILABLE, self._failure)
            return
        self._status = SinkStatus(CameraState.ACTIVE)
        self.formats.append((width, height, fps))

    def set_format(self, width: int, height: int, fps: int) -> bool:
        if not self.accepts_formats:
            return False
        self.formats.append((width, height, fps))
        return True

    def send(self, frame: I420Frame) -> None:
        self.frames_sent += 1
        self.last_frame = frame

    def close(self) -> None:
        self._status = UNAVAILABLE_UNTIL_OPENED

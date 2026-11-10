from wcam.virtualcam.sink import (
    UNAVAILABLE_UNTIL_OPENED,
    AnnouncedFormat,
    CameraState,
    I420Frame,
    SinkStatus,
    UnavailableReason,
)


class FakeSink:
    def __init__(self, failure: UnavailableReason | None = None) -> None:
        self._failure = failure
        self._status = UNAVAILABLE_UNTIL_OPENED
        self._announced: AnnouncedFormat | None = None
        self._requested: tuple[int, int, int] | None = None
        self.frames_sent = 0
        self.last_frame: I420Frame | None = None
        self.requests: list[tuple[int, int, int]] = []
        self.accepts_formats = True
        self.holds_formats = False
        self.reports_changes = False

    @property
    def backend(self) -> str:
        return "fake"

    @property
    def name(self) -> str:
        return "fake"

    @property
    def status(self) -> SinkStatus:
        return self._status

    @property
    def reports_format_changes(self) -> bool:
        return self.reports_changes

    def open(self, width: int, height: int, fps: int) -> None:
        if self._failure is not None:
            self._status = SinkStatus(CameraState.UNAVAILABLE, self._failure)
            return
        self._status = SinkStatus(CameraState.ACTIVE)
        self._announced = AnnouncedFormat(width, height, fps, pending=False, running=True)

    def request_format(self, width: int, height: int, fps: int) -> bool:
        self.requests.append((width, height, fps))
        if not self.accepts_formats or self._announced is None:
            return False
        current = self._announced
        if self.holds_formats and (width, height, fps) != (current.width, current.height, current.fps):
            self._requested = (width, height, fps)
            self._announced = AnnouncedFormat(current.width, current.height, current.fps, pending=True, running=True)
            return True
        self._requested = None
        self._announced = AnnouncedFormat(width, height, fps, pending=False, running=True)
        return True

    def apply_held_format(self) -> None:
        if self._requested is not None:
            width, height, fps = self._requested
            self._announced = AnnouncedFormat(width, height, fps, pending=False, running=True)
            self._requested = None

    def announced_format(self) -> AnnouncedFormat | None:
        return self._announced

    def send(self, frame: I420Frame) -> None:
        self.frames_sent += 1
        self.last_frame = frame

    def close(self) -> None:
        self._status = UNAVAILABLE_UNTIL_OPENED

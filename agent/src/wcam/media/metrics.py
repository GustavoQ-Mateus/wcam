from dataclasses import dataclass
from enum import StrEnum

from wcam.media.color_correction import ColorCorrection

WINDOW_SECONDS = 1.0
BITS_PER_BYTE = 8
BITS_PER_KILOBIT = 1000


class Orientation(StrEnum):
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"


@dataclass(frozen=True, slots=True)
class VideoStats:
    width: int
    height: int
    fps: float
    bitrate_kbps: int
    codec: str | None = None
    frames_scaled: int = 0
    orientation: Orientation = Orientation.LANDSCAPE
    color_range: str = "unspecified"
    color_matrix: str = "unspecified"
    color_correction: ColorCorrection | None = None


class VideoMeter:
    def __init__(self) -> None:
        self._stats: VideoStats | None = None
        self._window_start: float | None = None
        self._window_start_bytes = 0
        self._window_frames = 0

    @property
    def stats(self) -> VideoStats | None:
        return self._stats

    def record_frame(self, now: float, width: int, height: int, bytes_received: int) -> None:
        if self._window_start is None:
            self._start_window(now, bytes_received)
            self._stats = VideoStats(width, height, 0.0, 0)
            return
        self._window_frames += 1
        elapsed = now - self._window_start
        if elapsed < WINDOW_SECONDS:
            return
        fps = self._window_frames / elapsed
        bitrate = (bytes_received - self._window_start_bytes) * BITS_PER_BYTE / elapsed / BITS_PER_KILOBIT
        self._stats = VideoStats(width, height, round(fps, 1), round(bitrate))
        self._start_window(now, bytes_received)

    def _start_window(self, now: float, bytes_received: int) -> None:
        self._window_start = now
        self._window_start_bytes = bytes_received
        self._window_frames = 0

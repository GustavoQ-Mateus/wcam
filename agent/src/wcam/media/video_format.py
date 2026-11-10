from dataclasses import dataclass
from enum import StrEnum


class VideoFormat(StrEnum):
    HD_30 = "720p30"
    HD_60 = "720p60"
    FULL_HD_30 = "1080p30"
    QHD_30 = "1440p30"
    UHD_30 = "2160p30"

    @property
    def size(self) -> "FormatSize":
        return FORMAT_SIZES[self]


@dataclass(frozen=True, slots=True)
class FormatSize:
    width: int
    height: int
    fps: int
    max_bitrate_bps: int

    @property
    def pixels(self) -> int:
        return self.width * self.height


@dataclass(frozen=True, slots=True)
class CameraLimits:
    width: int | None
    height: int | None
    frame_rate: float | None


FORMAT_SIZES = {
    VideoFormat.HD_30: FormatSize(1280, 720, 30, 5_000_000),
    VideoFormat.HD_60: FormatSize(1280, 720, 60, 8_000_000),
    VideoFormat.FULL_HD_30: FormatSize(1920, 1080, 30, 10_000_000),
    VideoFormat.QHD_30: FormatSize(2560, 1440, 30, 18_000_000),
    VideoFormat.UHD_30: FormatSize(3840, 2160, 30, 35_000_000),
}
DEFAULT_VIDEO_FORMAT = VideoFormat.FULL_HD_30
FPS_TOLERANCE = 0.5


def available_formats(limits: CameraLimits | None) -> tuple[VideoFormat, ...]:
    if limits is None:
        return (DEFAULT_VIDEO_FORMAT,)
    default = DEFAULT_VIDEO_FORMAT.size
    sides = (limits.width or default.width, limits.height or default.height)
    long_side, short_side = max(sides), min(sides)
    frame_rate = limits.frame_rate or default.fps
    fitting = tuple(
        video_format
        for video_format in VideoFormat
        if video_format.size.width <= long_side
        and video_format.size.height <= short_side
        and video_format.size.fps <= frame_rate + FPS_TOLERANCE
    )
    return fitting or (DEFAULT_VIDEO_FORMAT,)


def largest_format(formats: tuple[VideoFormat, ...]) -> VideoFormat:
    return max(formats, key=lambda video_format: (video_format.size.pixels, video_format.size.fps))


def format_after_capabilities(selected: VideoFormat, available: tuple[VideoFormat, ...]) -> VideoFormat:
    return selected if selected in available else largest_format(available)


def format_of(width: int, height: int, fps: int) -> VideoFormat | None:
    return next(
        (
            video_format
            for video_format, size in FORMAT_SIZES.items()
            if (size.width, size.height, size.fps) == (width, height, fps)
        ),
        None,
    )

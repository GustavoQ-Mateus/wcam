import sys
from pathlib import Path
from typing import Protocol, cast

import av
import numpy as np
from av import VideoFrame

from wcam.media.placeholder import NEUTRAL_CHROMA
from wcam.virtualcam.sink import I420Frame

ENCODER_NAME = "libx264"
I420_FORMAT = "yuv420p"
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
DEFAULT_FPS = 30
DEFAULT_SECONDS = 6.0
BACKGROUND_LUMA = 110
MARKER_LUMA = 235
BAR_LUMA = 180
MARKER_SHARE = 4
BAR_SHARE = 16
MARKER_CHROMA = 60
USAGE = "usage: python -m wcam.tools.make_test_video <output.mp4>"


class EncodingStream(Protocol):
    width: int
    height: int
    pix_fmt: str | None

    def set_display_rotation(self, degrees: float) -> None: ...

    def encode(self, frame: VideoFrame | None = None) -> list[object]: ...


class Muxer(Protocol):
    def add_stream(self, codec_name: str, rate: int) -> EncodingStream: ...

    def mux(self, packets: list[object]) -> None: ...


def pattern_frame(width: int, height: int, index: int, count: int) -> I420Frame:
    frame = np.full((height * 3 // 2, width), NEUTRAL_CHROMA, dtype=np.uint8)
    luma = frame[:height]
    luma[:] = BACKGROUND_LUMA
    luma[: height // MARKER_SHARE, : width // MARKER_SHARE] = MARKER_LUMA
    bar_width = max(2, width // BAR_SHARE)
    left = (width - bar_width) * index // max(1, count - 1)
    luma[height // 2 :, left : left + bar_width] = BAR_LUMA
    frame[height : height + height // 8, : width // (2 * MARKER_SHARE)] = MARKER_CHROMA
    return frame


def write_test_video(
    path: Path,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    fps: int = DEFAULT_FPS,
    seconds: float = DEFAULT_SECONDS,
    rotation: int = 0,
) -> None:
    count = round(fps * seconds)
    with av.open(str(path), "w") as opened:
        container = cast(Muxer, opened)
        stream = container.add_stream(ENCODER_NAME, rate=fps)
        stream.width = width
        stream.height = height
        stream.pix_fmt = I420_FORMAT
        if rotation:
            stream.set_display_rotation(rotation)
        for index in range(count):
            frame = VideoFrame.from_ndarray(pattern_frame(width, height, index, count), format=I420_FORMAT)
            frame.pts = index
            container.mux(stream.encode(frame))
        container.mux(stream.encode(None))


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(USAGE)
    write_test_video(Path(sys.argv[1]))


if __name__ == "__main__":
    main()

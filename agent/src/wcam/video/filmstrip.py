from pathlib import Path

import av
import numpy as np
from av import VideoFrame
from numpy.typing import NDArray
from PIL import Image

from wcam.media.pipeline import REDUCTION_INTERPOLATION
from wcam.video.errors import VideoUnsupportedError
from wcam.video.frames import quarter_turns, shown_size

FILMSTRIP_WIDTH = 160
MAX_FILMSTRIP_FRAMES = 60
FILMSTRIP_QUALITY = 80
RGB_FORMAT = "rgb24"
JPEG_FORMAT = "JPEG"
KEYFRAMES_ONLY = "NONKEY"
SLICE_THREADS = "SLICE"

type Thumbnail = NDArray[np.uint8]


def write_filmstrip(video: Path, target: Path, duration_seconds: float) -> int:
    keyframes = keyframe_thumbnails(video)
    if not keyframes:
        raise VideoUnsupportedError
    chosen = evenly_spaced(keyframes, duration_seconds, min(MAX_FILMSTRIP_FRAMES, len(keyframes)))
    Image.fromarray(np.hstack(chosen)).save(target, format=JPEG_FORMAT, quality=FILMSTRIP_QUALITY)
    return len(chosen)


def keyframe_thumbnails(video: Path) -> list[tuple[float, Thumbnail]]:
    with av.open(str(video)) as container:
        stream = container.streams.video[0]
        stream.thread_type = SLICE_THREADS
        stream.codec_context.skip_frame = KEYFRAMES_ONLY
        return [(frame.time or 0.0, thumbnail(frame)) for frame in container.decode(stream)]


def thumbnail(frame: VideoFrame) -> Thumbnail:
    shown_width, shown_height = shown_size(frame)
    height = max(1, round(FILMSTRIP_WIDTH * shown_height / shown_width))
    turns = quarter_turns(frame)
    coded_width, coded_height = (height, FILMSTRIP_WIDTH) if turns % 2 else (FILMSTRIP_WIDTH, height)
    reduced = frame.reformat(
        width=coded_width,
        height=coded_height,
        format=RGB_FORMAT,
        interpolation=REDUCTION_INTERPOLATION,
    )
    image: Thumbnail = np.ascontiguousarray(np.rot90(reduced.to_ndarray(), turns), dtype=np.uint8)
    return image


def evenly_spaced(keyframes: list[tuple[float, Thumbnail]], duration_seconds: float, count: int) -> list[Thumbnail]:
    times = np.array([seconds for seconds, _ in keyframes])
    targets = [duration_seconds * (index + 0.5) / count for index in range(count)]
    return [keyframes[int(np.abs(times - target).argmin())][1] for target in targets]

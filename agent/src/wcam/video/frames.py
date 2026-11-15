import numpy as np
from av import VideoFrame
from av.video.reformatter import ColorRange, Colorspace

from wcam.media.pipeline import I420_FORMAT, REDUCTION_INTERPOLATION, even, i420_planes, paste_i420, plane_rows
from wcam.media.placeholder import black_i420
from wcam.virtualcam.sink import I420Frame

QUARTER_TURN_DEGREES = 90
TURNS_PER_CIRCLE = 4
SINGLE_THREAD = 1

type Planes = tuple[I420Frame, I420Frame, I420Frame]


def quarter_turns(frame: VideoFrame) -> int:
    return round(frame.rotation / QUARTER_TURN_DEGREES) % TURNS_PER_CIRCLE


def shown_size(frame: VideoFrame) -> tuple[int, int]:
    if quarter_turns(frame) % 2:
        return frame.height, frame.width
    return frame.width, frame.height


def fitted_size(shown_width: int, shown_height: int, width: int, height: int) -> tuple[int, int]:
    scale = min(width / shown_width, height / shown_height)
    return min(width, even(shown_width * scale)), min(height, even(shown_height * scale))


def fitted_i420(frame: VideoFrame, width: int, height: int) -> I420Frame:
    turns = quarter_turns(frame)
    fit_width, fit_height = fitted_size(*shown_size(frame), width, height)
    coded_width, coded_height = (fit_height, fit_width) if turns % 2 else (fit_width, fit_height)
    image = assembled_i420(source_planes(frame, coded_width, coded_height), turns, fit_width, fit_height)
    if (fit_width, fit_height) == (width, height):
        return image
    canvas = black_i420(width, height)
    paste_i420(canvas, image, fit_width, fit_height)
    return canvas


def source_planes(frame: VideoFrame, width: int, height: int) -> Planes:
    source = frame if passes_through(frame, width, height) else converted_frame(frame, width, height)
    luma, blue, red = (plane_rows(plane, None)[: plane.height, : plane.width] for plane in source.planes)
    return luma, blue, red


def passes_through(frame: VideoFrame, width: int, height: int) -> bool:
    return (
        frame.format.name == I420_FORMAT
        and (frame.width, frame.height) == (width, height)
        and frame.colorspace == Colorspace.ITU709
        and frame.color_range == ColorRange.MPEG
    )


def converted_frame(frame: VideoFrame, width: int, height: int) -> VideoFrame:
    # Threaded swscale leaves chroma rows unwritten at slice edges when it copies without scaling.
    threads = SINGLE_THREAD if (frame.width, frame.height) == (width, height) else None
    return frame.reformat(
        width=width,
        height=height,
        format=I420_FORMAT,
        dst_colorspace=Colorspace.ITU709,
        interpolation=REDUCTION_INTERPOLATION,
        dst_color_range=ColorRange.MPEG,
        threads=threads,
    )


def assembled_i420(planes: Planes, turns: int, width: int, height: int) -> I420Frame:
    image = np.empty((height * 3 // 2, width), dtype=np.uint8)
    for target, source in zip(i420_planes(image, width, height), planes, strict=True):
        target[:] = np.rot90(source, turns)
    return image

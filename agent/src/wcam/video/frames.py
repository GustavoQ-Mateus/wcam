import numpy as np
from av import VideoFrame
from av.video.reformatter import ColorRange, Colorspace

from wcam.media.pipeline import I420_FORMAT, REDUCTION_INTERPOLATION, even, i420_planes, paste_i420
from wcam.media.placeholder import black_i420
from wcam.virtualcam.sink import I420Frame

QUARTER_TURN_DEGREES = 90
TURNS_PER_CIRCLE = 4


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
    image = converted_i420(frame, coded_width, coded_height)
    if turns:
        image = rotated_i420(image, coded_width, coded_height, turns)
    if (fit_width, fit_height) == (width, height):
        return image
    canvas = black_i420(width, height)
    paste_i420(canvas, image, fit_width, fit_height)
    return canvas


def converted_i420(frame: VideoFrame, width: int, height: int) -> I420Frame:
    reduced = frame.reformat(
        width=width,
        height=height,
        format=I420_FORMAT,
        dst_colorspace=Colorspace.ITU709,
        interpolation=REDUCTION_INTERPOLATION,
        dst_color_range=ColorRange.MPEG,
    )
    image: I420Frame = np.ascontiguousarray(reduced.to_ndarray(), dtype=np.uint8)
    return image


def rotated_i420(image: I420Frame, width: int, height: int, turns: int) -> I420Frame:
    planes = [np.rot90(plane, turns) for plane in i420_planes(image, width, height)]
    rotated_width = height if turns % 2 else width
    flat = np.concatenate([plane.reshape(-1) for plane in planes])
    return flat.reshape(-1, rotated_width)

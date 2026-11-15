import numpy as np
from numpy.typing import NDArray

from wcam.virtualcam.sink import I420Frame

BLACK_LUMA = 16
NEUTRAL_CHROMA = 128
ICON_LUMA = 200
ICON_HEIGHT_SHARE = 0.25
STROKE = 0.06
BODY = (0.06, 0.28, 0.68, 0.78)
LENS = (0.72, 0.4, 0.94, 0.66)
SLASH_START = 0.06
SLASH_END = 0.94

type Grid = NDArray[np.float32]
type Mask = NDArray[np.bool_]


def black_i420(width: int, height: int) -> I420Frame:
    frame = np.full((height * 3 // 2, width), NEUTRAL_CHROMA, dtype=np.uint8)
    frame[:height] = BLACK_LUMA
    return frame


def camera_off_i420(width: int, height: int) -> I420Frame:
    frame = black_i420(width, height)
    side = min(width, max(1, round(height * ICON_HEIGHT_SHARE)))
    top = (height - side) // 2
    left = (width - side) // 2
    rows, columns = np.indices((side, side), dtype=np.float32) / side
    icon = frame[top : top + side, left : left + side]
    icon[crossed_camera(columns, rows)] = ICON_LUMA
    return frame


def crossed_camera(x: Grid, y: Grid) -> Mask:
    return outline(x, y, BODY) | inside(x, y, LENS) | slash(x, y)


def outline(x: Grid, y: Grid, box: tuple[float, float, float, float]) -> Mask:
    left, top, right, bottom = box
    inner = (left + STROKE, top + STROKE, right - STROKE, bottom - STROKE)
    return inside(x, y, box) & ~inside(x, y, inner)


def inside(x: Grid, y: Grid, box: tuple[float, float, float, float]) -> Mask:
    left, top, right, bottom = box
    return (x >= left) & (x <= right) & (y >= top) & (y <= bottom)


def slash(x: Grid, y: Grid) -> Mask:
    near_diagonal = np.abs(y - x) <= STROKE * np.sqrt(2) / 2
    return near_diagonal & (x >= SLASH_START) & (x <= SLASH_END)

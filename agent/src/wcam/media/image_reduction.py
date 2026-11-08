from typing import Any, cast

import numpy as np

from wcam.media.color_difference import FloatArray
from wcam.virtualcam.sink import I420Frame

REDUCED_WIDTH = 320
REDUCED_HEIGHT = 180
MAX_DETAIL = 0.04
BT709_RED_WEIGHT = 0.2126
BT709_BLUE_WEIGHT = 0.0722
BT709_GREEN_WEIGHT = 1 - BT709_RED_WEIGHT - BT709_BLUE_WEIGHT
BT709_LUMA_WEIGHTS = np.array([BT709_RED_WEIGHT, BT709_GREEN_WEIGHT, BT709_BLUE_WEIGHT])


def block_mean(plane: np.ndarray[Any, Any], width: int, height: int) -> FloatArray:
    row_factor, row_rest = divmod(plane.shape[0], height)
    column_factor, column_rest = divmod(plane.shape[1], width)
    if row_rest == 0 and column_rest == 0:
        accumulator = np.uint16 if plane.dtype == np.uint8 else np.float64
        rows = plane.reshape(height, row_factor, plane.shape[1]).sum(axis=1, dtype=accumulator)
        summed = rows.reshape(height, width, column_factor).sum(axis=2, dtype=np.float64)
        return summed / float(row_factor * column_factor)
    row_starts = np.arange(height) * plane.shape[0] // height
    column_starts = np.arange(width) * plane.shape[1] // width
    sums = np.add.reduceat(np.add.reduceat(plane, row_starts, axis=0, dtype=np.float64), column_starts, axis=1)
    row_counts = np.diff(np.append(row_starts, plane.shape[0])).astype(np.float64)
    column_counts = np.diff(np.append(column_starts, plane.shape[1])).astype(np.float64)
    return cast(FloatArray, sums / (row_counts[:, None] * column_counts[None, :]))


def can_reduce(width: int, height: int) -> bool:
    return width >= 2 * REDUCED_WIDTH and height >= 2 * REDUCED_HEIGHT


def fine_detail(luma: I420Frame) -> FloatArray:
    row_stride = luma.shape[0] // REDUCED_HEIGHT
    column_stride = luma.shape[1] // REDUCED_WIDTH
    rows = slice(0, row_stride * REDUCED_HEIGHT, row_stride)
    columns = slice(0, column_stride * REDUCED_WIDTH, column_stride)
    next_rows = slice(1, row_stride * REDUCED_HEIGHT, row_stride)
    next_columns = slice(1, column_stride * REDUCED_WIDTH, column_stride)
    corner = luma[rows, columns].astype(np.int16)
    horizontal = np.abs(corner - luma[rows, next_columns])
    vertical = np.abs(corner - luma[next_rows, columns])
    return np.maximum(horizontal, vertical).astype(np.float64)


def correlation(first: FloatArray, second: FloatArray) -> float:
    first_centered = first - first.mean()
    second_centered = second - second.mean()
    norm = float(np.sqrt((first_centered**2).sum() * (second_centered**2).sum()))
    if norm == 0:
        return 0.0
    return float((first_centered * second_centered).sum() / norm)

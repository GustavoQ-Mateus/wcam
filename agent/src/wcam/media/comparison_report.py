import io
from dataclasses import dataclass
from typing import Any, cast

import av
import numpy as np
from av.error import FFmpegError

from wcam.media.color_difference import FloatArray, RgbSpace, delta_e_2000, to_lab
from wcam.media.image_reduction import (
    BT709_LUMA_WEIGHTS,
    MAX_DETAIL,
    REDUCED_HEIGHT,
    REDUCED_WIDTH,
    block_mean,
    can_reduce,
    correlation,
    fine_detail,
)
from wcam.virtualcam.sink import I420Frame

type BoolArray = np.ndarray[Any, np.dtype[np.bool_]]

PNG_FORMAT = "png_pipe"
RGB_FORMAT = "rgb24"
FULL_SCALE = 255
GRID_COLUMNS = 8
GRID_ROWS = 4
CHROMA_FLOOR = 10.0
P90 = 90
DIGITS = 3


@dataclass(frozen=True, slots=True)
class DecodedImage:
    rgb: I420Frame

    @property
    def width(self) -> int:
        return int(self.rgb.shape[1])

    @property
    def height(self) -> int:
        return int(self.rgb.shape[0])


@dataclass(frozen=True, slots=True)
class ImageDifference:
    correlation: float
    mirrored: bool
    delta_e_mean: float
    delta_e_median: float
    delta_e_p90: float
    delta_l: float
    chroma_ratio: float | None
    hue_shift_degrees: float | None
    grid: tuple[float, ...]


def decoded_png(png: bytes) -> DecodedImage:
    try:
        with av.open(io.BytesIO(png), mode="r", format=PNG_FORMAT) as container:
            frame = next(container.decode(video=0))
    except (FFmpegError, StopIteration) as error:
        raise ValueError("not a png image") from error
    return DecodedImage(np.ascontiguousarray(cast(I420Frame, frame.to_ndarray(format=RGB_FORMAT))))


def image_difference(
    reference: DecodedImage, reference_space: RgbSpace, compared: DecodedImage, compared_space: RgbSpace
) -> ImageDifference:
    reference_small = reduced_rgb(reference.rgb)
    compared_small = reduced_rgb(compared.rgb)
    score, mirrored = best_orientation(reference_small, compared_small)
    if mirrored:
        compared_small = compared_small[:, ::-1]
    reference_lab = to_lab(reference_small, reference_space)
    compared_lab = to_lab(compared_small, compared_space)
    error = delta_e_2000(reference_lab, compared_lab)
    smooth = smooth_cells(reference.rgb, compared.rgb, mirrored)
    return ImageDifference(
        correlation=round(score, DIGITS),
        mirrored=mirrored,
        delta_e_mean=round(float(error[smooth].mean()), DIGITS),
        delta_e_median=round(float(np.median(error[smooth])), DIGITS),
        delta_e_p90=round(float(np.percentile(error[smooth], P90)), DIGITS),
        delta_l=round(float((compared_lab[..., 0] - reference_lab[..., 0])[smooth].mean()), DIGITS),
        chroma_ratio=chroma_ratio(reference_lab[smooth], compared_lab[smooth]),
        hue_shift_degrees=hue_shift(reference_lab[smooth], compared_lab[smooth]),
        grid=region_means(error, smooth),
    )


def reduced_rgb(rgb: I420Frame) -> FloatArray:
    channels = [block_mean(rgb[..., channel], REDUCED_WIDTH, REDUCED_HEIGHT) for channel in range(3)]
    return np.stack(channels, axis=-1) / FULL_SCALE


def best_orientation(phone_small: FloatArray, pc_small: FloatArray) -> tuple[float, bool]:
    phone_luma = phone_small @ BT709_LUMA_WEIGHTS
    pc_luma = pc_small @ BT709_LUMA_WEIGHTS
    straight = correlation(phone_luma, pc_luma)
    mirrored = correlation(phone_luma, pc_luma[:, ::-1])
    return (mirrored, True) if mirrored > straight else (straight, False)


def smooth_cells(phone_rgb: I420Frame, pc_rgb: I420Frame, mirrored: bool) -> BoolArray:
    smooth = np.ones((REDUCED_HEIGHT, REDUCED_WIDTH), dtype=np.bool_)
    for rgb, flip in ((phone_rgb, False), (pc_rgb, mirrored)):
        if not can_reduce(rgb.shape[1], rgb.shape[0]):
            continue
        detail = fine_detail(np.rint(rgb @ BT709_LUMA_WEIGHTS).astype(np.uint8)) / FULL_SCALE
        smooth &= (detail[:, ::-1] if flip else detail) <= MAX_DETAIL
    if not smooth.any():
        smooth[:] = True
    return smooth


def chroma_ratio(phone_lab: FloatArray, pc_lab: FloatArray) -> float | None:
    phone_chroma = np.hypot(phone_lab[:, 1], phone_lab[:, 2])
    colored = phone_chroma > CHROMA_FLOOR
    if not colored.any():
        return None
    pc_chroma = np.hypot(pc_lab[:, 1], pc_lab[:, 2])
    return round(float(np.median(pc_chroma[colored] / phone_chroma[colored])), DIGITS)


def hue_shift(phone_lab: FloatArray, pc_lab: FloatArray) -> float | None:
    phone_chroma = np.hypot(phone_lab[:, 1], phone_lab[:, 2])
    colored = phone_chroma > CHROMA_FLOOR
    if not colored.any():
        return None
    phone_hue = np.arctan2(phone_lab[colored, 2], phone_lab[colored, 1])
    pc_hue = np.arctan2(pc_lab[colored, 2], pc_lab[colored, 1])
    shift = (np.degrees(pc_hue - phone_hue) + 180) % 360 - 180
    return round(float(np.average(shift, weights=phone_chroma[colored])), DIGITS)


def region_means(error: FloatArray, smooth: BoolArray) -> tuple[float, ...]:
    means: list[float] = []
    row_size = REDUCED_HEIGHT // GRID_ROWS
    column_size = REDUCED_WIDTH // GRID_COLUMNS
    for row in range(GRID_ROWS):
        for column in range(GRID_COLUMNS):
            rows = slice(row * row_size, (row + 1) * row_size)
            columns = slice(column * column_size, (column + 1) * column_size)
            region, region_smooth = error[rows, columns], smooth[rows, columns]
            values = region[region_smooth] if region_smooth.any() else region
            means.append(round(float(values.mean()), DIGITS))
    return tuple(means)

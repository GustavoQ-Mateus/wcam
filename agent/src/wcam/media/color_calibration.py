from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, cast

import numpy as np

from wcam.media.color_difference import FloatArray, RgbSpace, delta_e_2000, to_lab, to_srgb
from wcam.media.color_range import (
    CHROMA_CENTER,
    CHROMA_TRANSLATION,
    FULL_SCALE,
    LIMITED_CHROMA_SPAN,
    LIMITED_LUMA_FLOOR,
    LIMITED_LUMA_SPAN,
    LUMA_TRANSLATION,
    ColorRange,
)
from wcam.virtualcam.sink import I420Frame

type BoolArray = np.ndarray[Any, np.dtype[np.bool_]]
type ColorTables = tuple[bytes, bytes]

REDUCED_WIDTH = 320
REDUCED_HEIGHT = 180
MIN_CORRELATION = 0.8
EDGE_QUANTILE = 0.7
CURVE_KNOTS = 9
KNOT_POSITIONS = np.linspace(0.0, 1.0, CURVE_KNOTS)
KNOT_HALF_WIDTH = 0.5 / (CURVE_KNOTS - 1)
MIN_KNOT_CELLS = 20
FIT_CELLS = 6000
KNOT_STEP = 0.02
SATURATION_STEP = 0.05
STEP_SHRINK = 0.5
MIN_KNOT_STEP = 0.0025
MAX_FIT_ROUNDS = 60
MIN_SATURATION = 0.5
MAX_SATURATION = 2.0
CHROMA_LIMIT = 0.5
BT709_RED_WEIGHT = 0.2126
BT709_BLUE_WEIGHT = 0.0722
BT709_GREEN_WEIGHT = 1 - BT709_RED_WEIGHT - BT709_BLUE_WEIGHT
BT709_LUMA_WEIGHTS = np.array([BT709_RED_WEIGHT, BT709_GREEN_WEIGHT, BT709_BLUE_WEIGHT])
RED_DIFFERENCE_SCALE = 2 * (1 - BT709_RED_WEIGHT)
BLUE_DIFFERENCE_SCALE = 2 * (1 - BT709_BLUE_WEIGHT)
TABLE_ENTRIES = FULL_SCALE + 1
IDENTITY_TABLE = bytes(range(TABLE_ENTRIES))


@dataclass(frozen=True, slots=True)
class ColorSample:
    color_space: RgbSpace
    pixels: I420Frame
    captured_at: float

    @property
    def width(self) -> int:
        return int(self.pixels.shape[1])

    @property
    def height(self) -> int:
        return int(self.pixels.shape[0])


@dataclass(frozen=True, slots=True)
class ReducedFrame:
    luma: FloatArray
    blue: FloatArray
    red: FloatArray
    color_range: ColorRange


@dataclass(frozen=True, slots=True)
class SampleMatch:
    frame: ReducedFrame
    sample: ColorSample
    correlation: float
    mirrored: bool

    @property
    def accepted(self) -> bool:
        return self.correlation >= MIN_CORRELATION


@dataclass(frozen=True, slots=True)
class ColorCorrection:
    curve: tuple[float, ...]
    saturation: float

    def tone(self, luma: FloatArray) -> FloatArray:
        return np.interp(luma, KNOT_POSITIONS, np.array(self.curve))


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    correction: ColorCorrection | None
    delta_e: float


@dataclass(frozen=True, slots=True)
class FitCells:
    luma: FloatArray
    blue: FloatArray
    red: FloatArray
    target_lab: FloatArray
    target_srgb: FloatArray

    def every(self, stride: int) -> "FitCells":
        return FitCells(
            self.luma[::stride],
            self.blue[::stride],
            self.red[::stride],
            self.target_lab[::stride],
            self.target_srgb[::stride],
        )


IDENTITY_CORRECTION = ColorCorrection(tuple(float(position) for position in KNOT_POSITIONS), 1.0)


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


def reduced_frame(planes: tuple[I420Frame, I420Frame, I420Frame], color_range: ColorRange) -> ReducedFrame:
    luma, blue, red = (block_mean(plane, REDUCED_WIDTH, REDUCED_HEIGHT) for plane in planes)
    luma_floor, luma_span, chroma_span = range_scale(color_range)
    return ReducedFrame(
        (luma - luma_floor) / luma_span,
        (blue - CHROMA_CENTER) / chroma_span,
        (red - CHROMA_CENTER) / chroma_span,
        color_range,
    )


def range_scale(color_range: ColorRange) -> tuple[int, int, int]:
    if color_range is ColorRange.FULL:
        return 0, FULL_SCALE, FULL_SCALE
    return LIMITED_LUMA_FLOOR, LIMITED_LUMA_SPAN, LIMITED_CHROMA_SPAN


def resized_frame(frame: ReducedFrame, width: int, height: int, mirrored: bool) -> ReducedFrame:
    planes = (block_mean(plane, width, height) for plane in (frame.luma, frame.blue, frame.red))
    luma, blue, red = (plane[:, ::-1] if mirrored else plane for plane in planes)
    return ReducedFrame(luma, blue, red, frame.color_range)


def correlation(first: FloatArray, second: FloatArray) -> float:
    first_centered = first - first.mean()
    second_centered = second - second.mean()
    norm = float(np.sqrt((first_centered**2).sum() * (second_centered**2).sum()))
    if norm == 0:
        return 0.0
    return float((first_centered * second_centered).sum() / norm)


def sample_rgb(sample: ColorSample) -> FloatArray:
    return sample.pixels.astype(np.float64) / FULL_SCALE


def best_match(frames: Sequence[ReducedFrame], sample: ColorSample) -> SampleMatch | None:
    sample_luma = sample_rgb(sample) @ BT709_LUMA_WEIGHTS
    best: SampleMatch | None = None
    for frame in frames:
        luma = block_mean(frame.luma, sample.width, sample.height)
        for mirrored in (False, True):
            score = correlation(luma[:, ::-1] if mirrored else luma, sample_luma)
            if best is None or score > best.correlation:
                best = SampleMatch(frame, sample, score, mirrored)
    if best is None:
        return None
    resized = resized_frame(best.frame, sample.width, sample.height, best.mirrored)
    return SampleMatch(resized, sample, best.correlation, best.mirrored)


def rendered_rgb(correction: ColorCorrection, luma: FloatArray, blue: FloatArray, red: FloatArray) -> FloatArray:
    corrected_luma = np.clip(correction.tone(luma), 0, 1)
    corrected_blue = np.clip(correction.saturation * blue, -CHROMA_LIMIT, CHROMA_LIMIT)
    corrected_red = np.clip(correction.saturation * red, -CHROMA_LIMIT, CHROMA_LIMIT)
    red_channel = corrected_luma + RED_DIFFERENCE_SCALE * corrected_red
    blue_channel = corrected_luma + BLUE_DIFFERENCE_SCALE * corrected_blue
    green_channel = (
        corrected_luma - BT709_RED_WEIGHT * red_channel - BT709_BLUE_WEIGHT * blue_channel
    ) / BT709_GREEN_WEIGHT
    return np.clip(np.stack([red_channel, green_channel, blue_channel], axis=-1), 0, 1)


def mean_delta_e(correction: ColorCorrection, cells: FitCells) -> float:
    rendered = to_lab(rendered_rgb(correction, cells.luma, cells.blue, cells.red), RgbSpace.SRGB)
    return float(delta_e_2000(cells.target_lab, rendered).mean())


def flat_edges_mask(lab: FloatArray) -> BoolArray:
    row_gradient, column_gradient = cast(tuple[FloatArray, FloatArray], np.gradient(lab[..., 0]))
    gradient: FloatArray = np.hypot(row_gradient, column_gradient)
    return gradient <= float(np.quantile(gradient, EDGE_QUANTILE))


def fit_cells(matches: Sequence[SampleMatch]) -> FitCells:
    parts: list[tuple[FloatArray, FloatArray, FloatArray, FloatArray, FloatArray]] = []
    for match in matches:
        rgb = sample_rgb(match.sample)
        lab = to_lab(rgb, match.sample.color_space)
        mask = flat_edges_mask(lab)
        srgb = to_srgb(rgb, match.sample.color_space)
        parts.append((match.frame.luma[mask], match.frame.blue[mask], match.frame.red[mask], lab[mask], srgb[mask]))
    luma, blue, red, lab, srgb = (np.concatenate([part[index] for part in parts]) for index in range(5))
    return FitCells(luma, blue, red, lab, srgb)


def fit_correction(matches: Sequence[SampleMatch]) -> CalibrationResult:
    cells = fit_cells(matches)
    before = mean_delta_e(IDENTITY_CORRECTION, cells)
    stride = max(1, len(cells.luma) // FIT_CELLS)
    correction = refined_correction(initial_correction(cells), cells.every(stride))
    after = mean_delta_e(correction, cells)
    if after < before:
        return CalibrationResult(correction, after)
    return CalibrationResult(None, before)


def initial_correction(cells: FitCells) -> ColorCorrection:
    target_luma = cells.target_srgb @ BT709_LUMA_WEIGHTS
    target_blue = (cells.target_srgb[:, 2] - target_luma) / BLUE_DIFFERENCE_SCALE
    target_red = (cells.target_srgb[:, 0] - target_luma) / RED_DIFFERENCE_SCALE
    chroma_energy = float((cells.blue**2 + cells.red**2).sum())
    saturation = 1.0
    if chroma_energy > 0:
        saturation = float((target_blue * cells.blue + target_red * cells.red).sum()) / chroma_energy
    return ColorCorrection(
        initial_curve(cells.luma, target_luma), float(np.clip(saturation, MIN_SATURATION, MAX_SATURATION))
    )


def initial_curve(luma: FloatArray, target_luma: FloatArray) -> tuple[float, ...]:
    supported: list[float] = []
    offsets: list[float] = []
    for position in KNOT_POSITIONS:
        near = np.abs(luma - position) <= KNOT_HALF_WIDTH
        if int(near.sum()) >= MIN_KNOT_CELLS:
            supported.append(float(position))
            offsets.append(float(np.median(target_luma[near] - luma[near])))
    if not supported:
        return IDENTITY_CORRECTION.curve
    curve = np.clip(KNOT_POSITIONS + np.interp(KNOT_POSITIONS, supported, offsets), 0, 1)
    return tuple(float(value) for value in np.maximum.accumulate(curve))


def refined_correction(start: ColorCorrection, cells: FitCells) -> ColorCorrection:
    parameters = [*start.curve, start.saturation]
    steps = [KNOT_STEP] * CURVE_KNOTS + [SATURATION_STEP]
    best = mean_delta_e(start, cells)
    for _ in range(MAX_FIT_ROUNDS):
        improvement = first_improvement(parameters, steps, best, cells)
        if improvement is not None:
            parameters, best = improvement
            continue
        steps = [step * STEP_SHRINK for step in steps]
        if steps[0] < MIN_KNOT_STEP:
            break
    return correction_from(parameters)


def first_improvement(
    parameters: list[float], steps: list[float], best: float, cells: FitCells
) -> tuple[list[float], float] | None:
    for candidate in neighbours(parameters, steps):
        cost = mean_delta_e(correction_from(candidate), cells)
        if cost < best:
            return candidate, cost
    return None


def neighbours(parameters: list[float], steps: list[float]) -> Iterator[list[float]]:
    for index, step in enumerate(steps):
        for direction in (1.0, -1.0):
            candidate = parameters.copy()
            candidate[index] += direction * step
            if is_valid(candidate):
                yield candidate


def is_valid(parameters: list[float]) -> bool:
    curve = np.array(parameters[:CURVE_KNOTS])
    saturation = parameters[CURVE_KNOTS]
    in_bounds = bool(curve.min() >= 0 and curve.max() <= 1)
    return in_bounds and bool(np.all(np.diff(curve) >= 0)) and MIN_SATURATION <= saturation <= MAX_SATURATION


def correction_from(parameters: list[float]) -> ColorCorrection:
    return ColorCorrection(tuple(parameters[:CURVE_KNOTS]), parameters[CURVE_KNOTS])


@lru_cache(maxsize=8)
def correction_tables(correction: ColorCorrection, color_range: ColorRange) -> ColorTables:
    values = np.arange(TABLE_ENTRIES, dtype=np.float64)
    if color_range is ColorRange.FULL:
        luma, chroma = values / FULL_SCALE, (values - CHROMA_CENTER) / FULL_SCALE
    else:
        luma = (values - LIMITED_LUMA_FLOOR) / LIMITED_LUMA_SPAN
        chroma = (values - CHROMA_CENTER) / LIMITED_CHROMA_SPAN
    corrected_luma = np.clip(correction.tone(luma), 0, 1)
    corrected_chroma = np.clip(correction.saturation * chroma, -CHROMA_LIMIT, CHROMA_LIMIT)
    luma_table = np.rint(LIMITED_LUMA_FLOOR + LIMITED_LUMA_SPAN * corrected_luma).astype(np.uint8)
    chroma_table = np.rint(CHROMA_CENTER + LIMITED_CHROMA_SPAN * corrected_chroma).astype(np.uint8)
    return luma_table.tobytes(), chroma_table.tobytes()


def applied_tables(correction: ColorCorrection | None, color_range: ColorRange) -> ColorTables | None:
    if correction is not None:
        return correction_tables(correction, color_range)
    return range_tables(color_range)


def range_tables(color_range: ColorRange) -> ColorTables | None:
    if color_range is ColorRange.FULL:
        return LUMA_TRANSLATION, CHROMA_TRANSLATION
    return None


def decoded_planes(frame: ReducedFrame) -> tuple[I420Frame, I420Frame, I420Frame]:
    luma_floor, luma_span, chroma_span = range_scale(frame.color_range)
    luma = luma_floor + luma_span * frame.luma
    blue = CHROMA_CENTER + chroma_span * frame.blue
    red = CHROMA_CENTER + chroma_span * frame.red
    return to_bytes(luma), to_bytes(blue), to_bytes(red)


def to_bytes(plane: FloatArray) -> I420Frame:
    return np.clip(np.rint(plane), 0, FULL_SCALE).astype(np.uint8)

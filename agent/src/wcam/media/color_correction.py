import logging
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache

import numpy as np

from wcam.media.color_difference import FloatArray, encode_srgb_curve
from wcam.media.color_range import (
    CHROMA_TRANSLATION,
    FULL_SCALE,
    LIMITED_LUMA_FLOOR,
    LIMITED_LUMA_SPAN,
    LUMA_TRANSLATION,
    ColorRange,
)
from wcam.virtualcam.sink import I420Frame

type ColorTables = tuple[bytes, bytes]

APPLE_DISPLAY_GAMMA = 1.961
DISPLAY_CURVE_TRANSFERS = frozenset({"bt709", "smpte170m"})
HDR_TRANSFERS = frozenset({"pq", "hlg"})
LIMITED_LUMA_CEILING = 235
TABLE_ENTRIES = FULL_SCALE + 1
IDENTITY_TABLE = bytes(range(TABLE_ENTRIES))
HDR_LEFT_UNCORRECTED = "Left an HDR camera without color correction"

logger = logging.getLogger(__name__)


class DisplayConvention(StrEnum):
    APPLE = "apple"
    STANDARD = "standard"


class CorrectionState(StrEnum):
    APPLIED = "applied"
    DEFAULT = "default"


@dataclass(frozen=True, slots=True)
class CameraColorSpace:
    primaries: str | None
    transfer: str | None
    matrix: str | None
    full_range: bool | None


@dataclass(frozen=True, slots=True)
class ColorCorrection:
    state: CorrectionState
    transfer: str | None
    display: DisplayConvention
    full_range: bool | None


def color_correction(color_space: CameraColorSpace | None, display: DisplayConvention) -> ColorCorrection:
    transfer = None if color_space is None else color_space.transfer
    full_range = None if color_space is None else color_space.full_range
    if transfer in HDR_TRANSFERS:
        logger.warning(HDR_LEFT_UNCORRECTED)
    applies = display is DisplayConvention.APPLE and transfer in DISPLAY_CURVE_TRANSFERS
    state = CorrectionState.APPLIED if applies else CorrectionState.DEFAULT
    return ColorCorrection(state, transfer, display, full_range)


def default_correction(display: DisplayConvention) -> ColorCorrection:
    return color_correction(None, display)


def effective_range(correction: ColorCorrection | None, frame_range: ColorRange) -> ColorRange:
    if correction is None or correction.full_range is None:
        return frame_range
    return ColorRange.FULL if correction.full_range else ColorRange.LIMITED


def correction_tables(correction: ColorCorrection | None, frame_range: ColorRange) -> ColorTables | None:
    color_range = effective_range(correction, frame_range)
    if correction is None or correction.state is CorrectionState.DEFAULT:
        return range_tables(color_range)
    return apple_display_tables(color_range)


def range_tables(color_range: ColorRange) -> ColorTables | None:
    if color_range is ColorRange.FULL:
        return LUMA_TRANSLATION, CHROMA_TRANSLATION
    return None


@lru_cache(maxsize=4)
def apple_display_tables(color_range: ColorRange) -> ColorTables:
    values = np.arange(TABLE_ENTRIES, dtype=np.float64)
    if color_range is ColorRange.FULL:
        luma = values / FULL_SCALE
        chroma_table = CHROMA_TRANSLATION
    else:
        luma = (values - LIMITED_LUMA_FLOOR) / LIMITED_LUMA_SPAN
        chroma_table = IDENTITY_TABLE
    displayed = apple_display_curve(np.clip(luma, 0, 1))
    luma_table = without_fixed_points(LIMITED_LUMA_FLOOR + LIMITED_LUMA_SPAN * displayed)
    return luma_table.tobytes(), chroma_table


def apple_display_curve(luma: FloatArray) -> FloatArray:
    return encode_srgb_curve(luma**APPLE_DISPLAY_GAMMA)


def without_fixed_points(exact: FloatArray) -> I420Frame:
    # bytes.translate branches on whether each byte changed; entries that map to themselves make that branch
    # unpredictable on noisy content and up to four times slower, so each one moves one code towards its exact value.
    rounded = np.rint(exact)
    indexes = np.arange(TABLE_ENTRIES)
    step = np.where(exact >= rounded, 1.0, -1.0)
    nudged = rounded + step
    nudged = np.where((nudged < LIMITED_LUMA_FLOOR) | (nudged > LIMITED_LUMA_CEILING), rounded - step, nudged)
    fixed = (rounded == indexes) & ~np.isclose(exact, indexes)
    return np.where(fixed, nudged, rounded).astype(np.uint8)

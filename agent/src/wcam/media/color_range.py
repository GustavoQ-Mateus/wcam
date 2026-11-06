from enum import StrEnum

import numpy as np
from av import VideoFrame
from av.video.reformatter import ColorRange as DeclaredRange

from wcam.virtualcam.sink import I420Frame

FULL_RANGE_FORMAT = "yuvj420p"
FULL_SCALE = 255
LIMITED_LUMA_FLOOR = 16
LIMITED_LUMA_SPAN = 219
CHROMA_CENTER = 128
LIMITED_CHROMA_SPAN = 224
UNSPECIFIED_MATRIX = "unspecified"
MATRIX_NAMES = {
    0: "gbr",
    1: "bt709",
    4: "fcc",
    5: "bt601",
    6: "bt601",
    7: "smpte240m",
    8: "ycgco",
    9: "bt2020nc",
    10: "bt2020c",
    11: "smpte2085",
    12: "chroma-derived-nc",
    13: "chroma-derived-c",
    14: "ictcp",
}


class ColorRange(StrEnum):
    FULL = "full"
    LIMITED = "limited"
    UNSPECIFIED = "unspecified"


def full_to_limited_tables() -> tuple[I420Frame, I420Frame]:
    values = np.arange(FULL_SCALE + 1, dtype=np.float64)
    luma = np.rint(LIMITED_LUMA_FLOOR + values * LIMITED_LUMA_SPAN / FULL_SCALE).astype(np.uint8)
    chroma = np.rint(CHROMA_CENTER + (values - CHROMA_CENTER) * LIMITED_CHROMA_SPAN / FULL_SCALE).astype(np.uint8)
    return luma, chroma


LUMA_TABLE, CHROMA_TABLE = full_to_limited_tables()
LUMA_TRANSLATION = LUMA_TABLE.tobytes()
CHROMA_TRANSLATION = CHROMA_TABLE.tobytes()


def declared_range(frame: VideoFrame) -> ColorRange:
    if frame.format.name == FULL_RANGE_FORMAT or frame.color_range == DeclaredRange.JPEG:
        return ColorRange.FULL
    if frame.color_range == DeclaredRange.MPEG:
        return ColorRange.LIMITED
    return ColorRange.UNSPECIFIED


def declared_matrix(frame: VideoFrame) -> str:
    return MATRIX_NAMES.get(frame.colorspace, UNSPECIFIED_MATRIX)


def translate_in_place(plane: I420Frame, translation: bytes) -> None:
    # bytes.translate looks up 256 entries in C, about twice as fast as numpy fancy indexing with intp indices.
    view = memoryview(plane.reshape(-1))
    view[:] = bytes(view).translate(translation)

import zlib
from dataclasses import dataclass

import numpy as np

from wcam.media.color_difference import FloatArray, RgbSpace
from wcam.media.comparison_report import DecodedImage
from wcam.media.image_reduction import BT709_LUMA_WEIGHTS, block_mean

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
CHUNK_LENGTH_BYTES = 4
CHUNK_HEADER_BYTES = 8
CHUNK_CRC_BYTES = 4
ICC_CHUNK = b"iCCP"
SRGB_CHUNK = b"sRGB"
IMAGE_DATA_CHUNK = b"IDAT"
DISPLAY_P3_NAMES = (b"Display P3", "Display P3".encode("utf-16-be"))
COARSE_WIDTH = 640
FINE_WIDTH = 1280
COARSE_SCALES = np.arange(0.70, 1.0201, 0.01)
FINE_SCALE_SPAN = 0.02
FINE_SCALE_STEP = 0.005
MIN_TEMPLATE_PIXELS = 32
BASE_MARGIN = 1.05
VARIANCE_FLOOR = 1e-9


@dataclass(frozen=True, slots=True)
class Placement:
    left: int
    top: int
    width: int
    height: int
    mirrored: bool
    score: float


@dataclass(frozen=True, slots=True)
class Candidate:
    score: float
    top: int
    left: int
    width: int
    height: int
    scale: float
    mirrored: bool


def png_color_space(png: bytes) -> RgbSpace:
    if not png.startswith(PNG_SIGNATURE):
        raise ValueError("not a png image")
    position = len(PNG_SIGNATURE)
    while position + CHUNK_HEADER_BYTES <= len(png):
        length = int.from_bytes(png[position : position + CHUNK_LENGTH_BYTES], "big")
        kind = png[position + CHUNK_LENGTH_BYTES : position + CHUNK_HEADER_BYTES]
        if kind == ICC_CHUNK:
            return icc_space(png[position + CHUNK_HEADER_BYTES : position + CHUNK_HEADER_BYTES + length])
        if kind in (SRGB_CHUNK, IMAGE_DATA_CHUNK):
            return RgbSpace.SRGB
        position += CHUNK_HEADER_BYTES + length + CHUNK_CRC_BYTES
    return RgbSpace.SRGB


def icc_space(chunk: bytes) -> RgbSpace:
    name, _, rest = chunk.partition(b"\x00")
    try:
        profile = zlib.decompress(rest[1:])
    except zlib.error:
        profile = b""
    if any(marker in name or marker in profile for marker in DISPLAY_P3_NAMES):
        return RgbSpace.DISPLAY_P3
    return RgbSpace.SRGB


def aligned_screen(reference: DecodedImage, screen: DecodedImage) -> tuple[DecodedImage, Placement]:
    placement = locate(luminance(reference), luminance(screen))
    crop = screen.rgb[
        placement.top : placement.top + placement.height, placement.left : placement.left + placement.width
    ]
    if placement.mirrored:
        crop = crop[:, ::-1]
    return DecodedImage(np.ascontiguousarray(crop)), placement


def luminance(image: DecodedImage) -> FloatArray:
    return image.rgb.astype(np.float64) @ BT709_LUMA_WEIGHTS


def locate(reference: FloatArray, screen: FloatArray) -> Placement:
    contain = min(screen.shape[1] / reference.shape[1], screen.shape[0] / reference.shape[0])
    coarse = search(reference, screen, COARSE_WIDTH, contain * COARSE_SCALES, (False, True))
    fine_scales = np.arange(coarse.scale - FINE_SCALE_SPAN, coarse.scale + FINE_SCALE_SPAN + 1e-9, FINE_SCALE_STEP)
    fine = search(reference, screen, FINE_WIDTH, fine_scales, (coarse.mirrored,))
    best = fine if fine.score >= coarse.score else coarse
    return Placement(best.left, best.top, best.width, best.height, best.mirrored, round(best.score, 3))


def search(
    reference: FloatArray, screen: FloatArray, work_width: int, scales: FloatArray, mirrors: tuple[bool, ...]
) -> Candidate:
    factor = min(1.0, work_width / screen.shape[1])
    work_screen = resized(screen, round(screen.shape[1] * factor), round(screen.shape[0] * factor))
    best = Candidate(-2.0, 0, 0, reference.shape[1], reference.shape[0], 1.0, False)
    for mirrored in mirrors:
        base = reduced_reference(reference[:, ::-1] if mirrored else reference, work_screen.shape[1])
        for scale in scales:
            candidate = placed(base, work_screen, reference.shape, float(scale), factor, mirrored)
            if candidate is not None and candidate.score > best.score:
                best = candidate
    return best


def reduced_reference(reference: FloatArray, work_width: int) -> FloatArray:
    width = min(reference.shape[1], round(work_width * BASE_MARGIN))
    return resized(reference, width, round(reference.shape[0] * width / reference.shape[1]))


def placed(
    base: FloatArray,
    work_screen: FloatArray,
    reference_shape: tuple[int, ...],
    scale: float,
    factor: float,
    mirrored: bool,
) -> Candidate | None:
    width = round(reference_shape[1] * scale * factor)
    height = round(reference_shape[0] * scale * factor)
    fits = width <= min(work_screen.shape[1], base.shape[1]) and height <= min(work_screen.shape[0], base.shape[0])
    if not fits or min(width, height) < MIN_TEMPLATE_PIXELS:
        return None
    score, top, left = normalized_correlation(work_screen, resized(base, width, height))
    return Candidate(
        score,
        round(top / factor),
        round(left / factor),
        round(width / factor),
        round(height / factor),
        scale,
        mirrored,
    )


def resized(plane: FloatArray, width: int, height: int) -> FloatArray:
    if (plane.shape[1], plane.shape[0]) == (width, height):
        return plane
    return block_mean(plane, width, height)


def normalized_correlation(image: FloatArray, template: FloatArray) -> tuple[float, int, int]:
    template_height, template_width = template.shape
    image_height, image_width = image.shape
    centered = template - template.mean()
    norm = float(np.sqrt((centered**2).sum()))
    if norm == 0:
        return -1.0, 0, 0
    spectrum = np.fft.rfft2(image) * np.conj(np.fft.rfft2(centered, image.shape))
    correlation = np.fft.irfft2(spectrum, image.shape)[
        : image_height - template_height + 1, : image_width - template_width + 1
    ]
    count = template_height * template_width
    sums = window_sums(image, template_height, template_width)
    squares = window_sums(image**2, template_height, template_width)
    deviation = np.sqrt(np.maximum(squares - sums**2 / count, VARIANCE_FLOOR))
    score = correlation / (deviation * norm)
    top, left = np.unravel_index(int(np.argmax(score)), score.shape)
    return float(score[top, left]), int(top), int(left)


def window_sums(image: FloatArray, height: int, width: int) -> FloatArray:
    table = np.pad(image, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    return table[height:, width:] - table[:-height, width:] - table[height:, :-width] + table[:-height, :-width]

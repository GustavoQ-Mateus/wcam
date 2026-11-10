from enum import StrEnum
from typing import Any

import numpy as np

type FloatArray = np.ndarray[Any, np.dtype[np.float64]]

D65_WHITE = np.array([0.95047, 1.0, 1.08883])
SRGB_TO_XYZ = np.array(
    [[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]]
)
DISPLAY_P3_TO_XYZ = np.array(
    [[0.4865709, 0.2656677, 0.1982173], [0.2289746, 0.6917385, 0.0792869], [0.0, 0.0451134, 1.0439444]]
)
SRGB_LINEAR_LIMIT = 0.04045
SRGB_LINEAR_SLOPE = 12.92
SRGB_ENCODED_LIMIT = 0.0031308
SRGB_OFFSET = 0.055
SRGB_EXPONENT = 2.4
LAB_DELTA = 6 / 29
CHROMA_REFERENCE = 25**7


class RgbSpace(StrEnum):
    SRGB = "srgb"
    DISPLAY_P3 = "display-p3"


TO_XYZ = {RgbSpace.SRGB: SRGB_TO_XYZ, RgbSpace.DISPLAY_P3: DISPLAY_P3_TO_XYZ}
XYZ_TO_SRGB = np.linalg.inv(SRGB_TO_XYZ)


def decode_srgb_curve(encoded: FloatArray) -> FloatArray:
    return np.where(
        encoded <= SRGB_LINEAR_LIMIT,
        encoded / SRGB_LINEAR_SLOPE,
        ((encoded + SRGB_OFFSET) / (1 + SRGB_OFFSET)) ** SRGB_EXPONENT,
    )


def encode_srgb_curve(linear: FloatArray) -> FloatArray:
    clipped = np.clip(linear, 0, 1)
    return np.where(
        clipped <= SRGB_ENCODED_LIMIT,
        clipped * SRGB_LINEAR_SLOPE,
        (1 + SRGB_OFFSET) * clipped ** (1 / SRGB_EXPONENT) - SRGB_OFFSET,
    )


def to_srgb(encoded: FloatArray, space: RgbSpace) -> FloatArray:
    xyz = decode_srgb_curve(encoded) @ TO_XYZ[space].T
    return encode_srgb_curve(xyz @ XYZ_TO_SRGB.T)


def to_lab(encoded: FloatArray, space: RgbSpace) -> FloatArray:
    xyz = decode_srgb_curve(encoded) @ TO_XYZ[space].T / D65_WHITE
    f = np.where(xyz > LAB_DELTA**3, np.cbrt(xyz), xyz / (3 * LAB_DELTA**2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def delta_e_2000(reference: FloatArray, candidate: FloatArray) -> FloatArray:
    l1, a1, b1 = reference[..., 0], reference[..., 1], reference[..., 2]
    l2, a2, b2 = candidate[..., 0], candidate[..., 1], candidate[..., 2]
    chroma_mean = (np.hypot(a1, b1) + np.hypot(a2, b2)) / 2
    g = 0.5 * (1 - np.sqrt(chroma_mean**7 / (chroma_mean**7 + CHROMA_REFERENCE)))
    a1_prime, a2_prime = (1 + g) * a1, (1 + g) * a2
    c1, c2 = np.hypot(a1_prime, b1), np.hypot(a2_prime, b2)
    h1 = np.degrees(np.arctan2(b1, a1_prime)) % 360
    h2 = np.degrees(np.arctan2(b2, a2_prime)) % 360
    no_chroma = c1 * c2 == 0
    hue_step = h2 - h1
    hue_step = np.where(hue_step > 180, hue_step - 360, np.where(hue_step < -180, hue_step + 360, hue_step))
    hue_step = np.where(no_chroma, 0, hue_step)
    hue_difference = 2 * np.sqrt(c1 * c2) * np.sin(np.radians(hue_step / 2))
    lightness_mean = (l1 + l2) / 2
    chroma_prime_mean = (c1 + c2) / 2
    hue_sum = h1 + h2
    hue_mean = np.where(
        no_chroma,
        hue_sum,
        np.where(
            np.abs(h1 - h2) <= 180, hue_sum / 2, np.where(hue_sum < 360, (hue_sum + 360) / 2, (hue_sum - 360) / 2)
        ),
    )
    t = (
        1
        - 0.17 * np.cos(np.radians(hue_mean - 30))
        + 0.24 * np.cos(np.radians(2 * hue_mean))
        + 0.32 * np.cos(np.radians(3 * hue_mean + 6))
        - 0.20 * np.cos(np.radians(4 * hue_mean - 63))
    )
    lightness_scale = 1 + 0.015 * (lightness_mean - 50) ** 2 / np.sqrt(20 + (lightness_mean - 50) ** 2)
    chroma_scale = 1 + 0.045 * chroma_prime_mean
    hue_scale = 1 + 0.015 * chroma_prime_mean * t
    rotation_angle = 60 * np.exp(-(((hue_mean - 275) / 25) ** 2))
    rotation = -2 * np.sqrt(chroma_prime_mean**7 / (chroma_prime_mean**7 + CHROMA_REFERENCE))
    rotation = rotation * np.sin(np.radians(rotation_angle))
    lightness_term = (l2 - l1) / lightness_scale
    chroma_term = (c2 - c1) / chroma_scale
    hue_term = hue_difference / hue_scale
    return np.sqrt(lightness_term**2 + chroma_term**2 + hue_term**2 + rotation * chroma_term * hue_term)

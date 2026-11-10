from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

WINDOW = 8
BLOCK_PIXELS = np.float32(WINDOW * WINDOW)
DYNAMIC_RANGE = 255.0
C1 = (0.01 * DYNAMIC_RANGE) ** 2
C2 = (0.03 * DYNAMIC_RANGE) ** 2
WARMUP_SECONDS = 3.0
Y4M_SIGNATURE = b"YUV4MPEG2"
Y4M_FRAME_MARKER = b"FRAME"

type Luma = NDArray[np.uint8]


@dataclass(frozen=True, slots=True)
class QualityReport:
    ssim: float | None
    minimum: float | None
    frames: int


def ssim(reference: Luma, measured: Luma) -> float:
    reference_blocks = blocks(reference)
    measured_blocks = blocks(measured)
    reference_mean = reference_blocks.mean(axis=(1, 3))
    measured_mean = measured_blocks.mean(axis=(1, 3))
    reference_square = block_mean_of_products(reference_blocks, reference_blocks)
    measured_square = block_mean_of_products(measured_blocks, measured_blocks)
    cross = block_mean_of_products(reference_blocks, measured_blocks)
    reference_variance = reference_square - reference_mean**2
    measured_variance = measured_square - measured_mean**2
    covariance = cross - reference_mean * measured_mean
    numerator = (2 * reference_mean * measured_mean + C1) * (2 * covariance + C2)
    denominator = (reference_mean**2 + measured_mean**2 + C1) * (reference_variance + measured_variance + C2)
    return float((numerator / denominator).mean())


def blocks(luma: Luma) -> NDArray[np.float32]:
    rows = luma.shape[0] // WINDOW * WINDOW
    columns = luma.shape[1] // WINDOW * WINDOW
    cropped = luma[:rows, :columns].astype(np.float32)
    return cropped.reshape(rows // WINDOW, WINDOW, columns // WINDOW, WINDOW)


def block_mean_of_products(first: NDArray[np.float32], second: NDArray[np.float32]) -> NDArray[np.float32]:
    products: NDArray[np.float32] = np.einsum("ijkl,ijkl->ik", first, second)
    return products / BLOCK_PIXELS


def read_y4m_luma(path: Path) -> Luma:
    with path.open("rb") as stream:
        header = stream.readline().split()
        if not header or header[0] != Y4M_SIGNATURE:
            raise ValueError(path)
        width = int(next(field[1:] for field in header if field.startswith(b"W")))
        height = int(next(field[1:] for field in header if field.startswith(b"H")))
        if not stream.readline().startswith(Y4M_FRAME_MARKER):
            raise ValueError(path)
        luma = np.frombuffer(stream.read(width * height), dtype=np.uint8)
    return luma.reshape(height, width)


class QualityMeter:
    def __init__(self, reference: Luma) -> None:
        self._original = reference
        self._reference = reference
        self._started_at: float | None = None
        self._total = 0.0
        self._minimum: float | None = None
        self._frames = 0

    @property
    def report(self) -> QualityReport:
        average = self._total / self._frames if self._frames else None
        return QualityReport(average, self._minimum, self._frames)

    def restart(self, now: float, luma_table: bytes | None = None) -> None:
        self._reference = self._original if luma_table is None else translated(self._original, luma_table)
        self._started_at = now
        self._total = 0.0
        self._minimum = None
        self._frames = 0

    def observe(self, now: float, luma: Luma) -> None:
        if self._started_at is None or now - self._started_at < WARMUP_SECONDS:
            return
        if luma.shape != self._reference.shape:
            return
        value = ssim(self._reference, luma)
        self._total += value
        self._minimum = value if self._minimum is None else min(self._minimum, value)
        self._frames += 1


def translated(luma: Luma, table: bytes) -> Luma:
    return np.frombuffer(luma.tobytes().translate(table), dtype=np.uint8).reshape(luma.shape)

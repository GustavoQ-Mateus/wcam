import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np

from wcam.media.quality import WARMUP_SECONDS, Luma, QualityMeter, read_y4m_luma, ssim
from wcam.tools.make_reference import HEIGHT, WIDTH, reference_frame

SEED = 11
NOISE_AMPLITUDE = 40
MINIMUM_ACCEPTED_SSIM = 0.98


def detailed_luma() -> Luma:
    generator = np.random.default_rng(SEED)
    return generator.integers(0, 256, size=(HEIGHT, WIDTH), dtype=np.uint8)


def test_ssim_of_identical_frames_is_one() -> None:
    luma = detailed_luma()

    assert ssim(luma, luma.copy()) == 1.0


def test_ssim_drops_with_noise() -> None:
    luma = detailed_luma()

    light = ssim(luma, with_noise(luma, NOISE_AMPLITUDE // 4))
    heavy = ssim(luma, with_noise(luma, NOISE_AMPLITUDE))

    assert heavy < light < 1.0
    assert heavy < MINIMUM_ACCEPTED_SSIM


def with_noise(luma: Luma, amplitude: int) -> Luma:
    generator = np.random.default_rng(SEED + 1)
    noise = generator.integers(-amplitude, amplitude + 1, size=luma.shape)
    return np.clip(luma.astype(np.int32) + noise, 0, 255).astype(np.uint8)


def test_reference_generator_is_deterministic() -> None:
    first = hashlib.sha256(reference_frame()).hexdigest()
    second = hashlib.sha256(reference_frame()).hexdigest()

    assert first == second


def test_reference_file_has_one_full_hd_frame(tmp_path: Path) -> None:
    output = tmp_path / "reference.y4m"

    subprocess.run([sys.executable, "-m", "wcam.tools.make_reference", str(output)], check=True)  # noqa: S603

    luma = read_y4m_luma(output)
    assert luma.shape == (HEIGHT, WIDTH)
    assert output.stat().st_size == len(reference_frame())
    assert output.read_bytes().startswith(b"YUV4MPEG2 W1920 H1080 F30:1")


def test_quality_ignores_warmup_and_reports_average_and_minimum() -> None:
    reference = detailed_luma()
    meter = QualityMeter(reference)
    meter.restart(0.0)

    meter.observe(WARMUP_SECONDS - 0.1, np.zeros_like(reference))
    meter.observe(WARMUP_SECONDS, reference)
    meter.observe(WARMUP_SECONDS + 0.1, reference)

    report = meter.report
    assert (report.ssim, report.minimum, report.frames) == (1.0, 1.0, 2)


def test_quality_without_measured_frames_is_null() -> None:
    meter = QualityMeter(detailed_luma())

    report = meter.report

    assert (report.ssim, report.minimum, report.frames) == (None, None, 0)

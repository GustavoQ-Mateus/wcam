import hashlib
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pytest

from tests.unit.test_pipeline import SteppingClock, phone_frame
from wcam.media.color_correction import (
    ColorCorrection,
    CorrectionState,
    DisplayConvention,
    apple_display_tables,
    correction_tables,
)
from wcam.media.color_range import ColorRange
from wcam.media.pipeline import FramePipeline
from wcam.media.quality import WARMUP_SECONDS, Luma, QualityMeter, read_y4m_luma, ssim, translated
from wcam.tools.make_reference import HEIGHT, WIDTH, reference_frame
from wcam.virtualcam.fake_sink import FakeSink

SEED = 11
NOISE_AMPLITUDE = 40
MINIMUM_ACCEPTED_SSIM = 0.98
RESTART_WAIT_SECONDS = 1.0
RESTART_POLL_SECONDS = 0.01


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


def test_reference_file_follows_the_requested_format(tmp_path: Path) -> None:
    output = tmp_path / "reference-2160p60.y4m"
    arguments = ["--width", "3840", "--height", "2160", "--fps", "60"]

    subprocess.run([sys.executable, "-m", "wcam.tools.make_reference", str(output), *arguments], check=True)  # noqa: S603

    assert read_y4m_luma(output).shape == (2160, 3840)
    assert output.read_bytes().startswith(b"YUV4MPEG2 W3840 H2160 F60:1")
    assert output.stat().st_size == len(reference_frame(3840, 2160, 60))


def test_reference_rejects_odd_sizes() -> None:
    with pytest.raises(ValueError, match="even"):
        reference_frame(1279, 720)


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


class RecordingMeter(QualityMeter):
    def __init__(self) -> None:
        super().__init__(detailed_luma())
        self.restarts: list[float] = []
        self.luma_tables: list[bytes | None] = []

    def restart(self, now: float, luma_table: bytes | None = None) -> None:
        self.restarts.append(now)
        self.luma_tables.append(luma_table)
        super().restart(now, luma_table)


def restarts_after_delivery(pipeline: FramePipeline, meter: RecordingMeter, count: int) -> list[float]:
    pipeline.deliver(phone_frame())
    deadline = time.monotonic() + RESTART_WAIT_SECONDS
    while len(meter.restarts) < count and time.monotonic() < deadline:
        time.sleep(RESTART_POLL_SECONDS)
    return meter.restarts


APPLE_CORRECTION = ColorCorrection(CorrectionState.APPLIED, "bt709", DisplayConvention.APPLE, True)
STANDARD_CORRECTION = ColorCorrection(CorrectionState.DEFAULT, "bt709", DisplayConvention.STANDARD, True)


def live_quality_pipeline(clock: SteppingClock) -> tuple[FramePipeline, RecordingMeter]:
    meter = RecordingMeter()
    pipeline = FramePipeline(FakeSink(), meter, clock=clock)
    pipeline.open()
    pipeline.start_phone()
    return pipeline, meter


def test_quality_restarts_when_the_color_correction_changes_state() -> None:
    clock = SteppingClock()
    pipeline, meter = live_quality_pipeline(clock)
    assert restarts_after_delivery(pipeline, meter, 1) == [clock.now]

    clock.now += 1.0
    pipeline.color_correction = APPLE_CORRECTION
    assert restarts_after_delivery(pipeline, meter, 2)[-1] == clock.now
    clock.now += 1.0
    pipeline.color_correction = STANDARD_CORRECTION
    assert restarts_after_delivery(pipeline, meter, 3)[-1] == clock.now
    assert len(restarts_after_delivery(pipeline, meter, 4)) == 3


def test_reference_through_the_applied_luma_table_matches_video_through_it() -> None:
    reference = detailed_luma()
    luma_table, _ = apple_display_tables(ColorRange.FULL)
    meter = QualityMeter(reference)
    meter.restart(0.0, luma_table)

    meter.observe(WARMUP_SECONDS, translated(reference, luma_table))

    assert meter.report.ssim == 1.0


def test_applied_correction_restarts_quality_with_its_luma_table_and_default_without() -> None:
    pipeline, meter = live_quality_pipeline(SteppingClock())
    pipeline.color_correction = APPLE_CORRECTION
    restarts_after_delivery(pipeline, meter, 2)
    pipeline.color_correction = STANDARD_CORRECTION
    restarts_after_delivery(pipeline, meter, 3)

    applied_table = correction_tables(APPLE_CORRECTION, pipeline.color_range)
    assert applied_table is not None
    assert meter.luma_tables == [None, applied_table[0], None]

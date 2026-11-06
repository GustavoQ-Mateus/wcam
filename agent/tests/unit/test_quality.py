import hashlib
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pytest

from tests.unit.test_color_calibration import KNOWN_CORRECTION
from tests.unit.test_pipeline import SteppingClock, phone_frame
from wcam.media.color_calibration import correction_tables
from wcam.media.color_calibrator import MEASURING, CalibrationState, CalibrationStatus
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


@pytest.mark.parametrize(
    "settled", [CalibrationStatus(CalibrationState.APPLIED, 0.5), CalibrationStatus(CalibrationState.DEFAULT, None)]
)
def test_quality_restarts_when_color_calibration_settles_and_measures_again(settled: CalibrationStatus) -> None:
    clock = SteppingClock()
    meter = RecordingMeter()
    pipeline = FramePipeline(FakeSink(), meter, clock=clock)
    pipeline.open()
    pipeline.start_phone()
    assert restarts_after_delivery(pipeline, meter, 1) == [clock.now]

    clock.now += 1.0
    pipeline.color_calibrator.status = settled
    assert restarts_after_delivery(pipeline, meter, 2)[-1] == clock.now

    clock.now += 1.0
    pipeline.color_calibrator.status = MEASURING
    assert restarts_after_delivery(pipeline, meter, 3)[-1] == clock.now
    assert len(restarts_after_delivery(pipeline, meter, 4)) == 3


def test_reference_through_the_applied_luma_table_matches_video_through_it() -> None:
    reference = detailed_luma()
    luma_table, _ = correction_tables(KNOWN_CORRECTION, ColorRange.FULL)
    meter = QualityMeter(reference)
    meter.restart(0.0, luma_table)

    meter.observe(WARMUP_SECONDS, translated(reference, luma_table))

    assert meter.report.ssim == 1.0


def test_applied_calibration_restarts_quality_with_its_luma_table_and_default_without() -> None:
    meter = RecordingMeter()
    pipeline = FramePipeline(FakeSink(), meter, clock=SteppingClock())
    pipeline.open()
    pipeline.start_phone()
    pipeline.color_calibrator.correction = KNOWN_CORRECTION
    pipeline.color_calibrator.status = CalibrationStatus(CalibrationState.APPLIED, 0.5)
    restarts_after_delivery(pipeline, meter, 2)
    pipeline.color_calibrator.correction = None
    pipeline.color_calibrator.status = CalibrationStatus(CalibrationState.DEFAULT, None)
    restarts_after_delivery(pipeline, meter, 3)

    assert meter.luma_tables == [None, correction_tables(KNOWN_CORRECTION, pipeline.color_range)[0], None]

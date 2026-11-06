import asyncio
import base64
import json
import logging
from pathlib import Path

import numpy as np
import pytest
from av import VideoFrame

from tests.fakes import FakePeerFactory
from tests.unit.test_pipeline import live_pipeline, random_i420
from tests.unit.test_quality_preset import live_manager
from tests.unit.test_session_manager import connected_manager
from wcam.media.color_calibration import (
    IDENTITY_CORRECTION,
    KNOT_POSITIONS,
    MIN_CORRELATION,
    ColorCorrection,
    ColorSample,
    SampleMatch,
    applied_tables,
    best_match,
    block_mean,
    correction_tables,
    fit_correction,
    reduced_frame,
    rendered_rgb,
    resized_frame,
)
from wcam.media.color_calibrator import CalibrationState, ColorCalibrator
from wcam.media.color_difference import (
    DISPLAY_P3_TO_XYZ,
    SRGB_TO_XYZ,
    FloatArray,
    RgbSpace,
    decode_srgb_curve,
    encode_srgb_curve,
)
from wcam.media.color_range import CHROMA_TABLE, LUMA_TABLE, ColorRange
from wcam.media.color_trace import ColorTrace
from wcam.sessions.manager import COLOR_SAMPLE_BEFORE_LIVE, IGNORED_PHONE_MESSAGE
from wcam.virtualcam.sink import OUTPUT_HEIGHT, I420Frame

SCENE_WIDTH = 640
SCENE_HEIGHT = 360
SAMPLE_WIDTH = 160
SAMPLE_HEIGHT = 90
BLOCK_ROWS = 6
BLOCK_COLUMNS = 8
KNOWN_EXPONENT = 0.89
KNOWN_SATURATION = 1.15
CURVE_TOLERANCE = 0.03
SATURATION_TOLERANCE = 0.03
RECOVERED_DELTA_E = 1.0
APPLIED_DELTA_E = 2.0
SETTLE_SECONDS = 20.0
POLL_SECONDS = 0.02
CAPTURED_AT = 1793991387130.0
KNOWN_CORRECTION = ColorCorrection(tuple(float(value) for value in KNOT_POSITIONS**KNOWN_EXPONENT), KNOWN_SATURATION)

type Planes = tuple[I420Frame, I420Frame, I420Frame]


def scene_planes(seed: int, width: int = SCENE_WIDTH, height: int = SCENE_HEIGHT) -> Planes:
    generator = np.random.default_rng(seed)
    colors = generator.random((BLOCK_ROWS, BLOCK_COLUMNS, 3))
    rows, columns = np.mgrid[0:height, 0:width]
    rgb = colors[rows * BLOCK_ROWS // height, columns * BLOCK_COLUMNS // width]
    rgb = rgb * (0.4 + 0.6 * columns[..., None] / width)
    luma = rgb @ np.array([0.2126, 0.7152, 0.0722])
    blue = (rgb[..., 2] - luma) / 1.8556
    red = (rgb[..., 0] - luma) / 1.5748
    return (
        to_uint8(luma * 255),
        to_uint8(blue[::2, ::2] * 255 + 128),
        to_uint8(red[::2, ::2] * 255 + 128),
    )


def to_uint8(plane: FloatArray) -> I420Frame:
    return np.clip(np.rint(plane), 0, 255).astype(np.uint8)


def srgb_to(rgb: FloatArray, space: RgbSpace) -> FloatArray:
    if space is RgbSpace.SRGB:
        return rgb
    linear = decode_srgb_curve(rgb) @ SRGB_TO_XYZ.T @ np.linalg.inv(DISPLAY_P3_TO_XYZ).T
    return encode_srgb_curve(linear)


def phone_sample(
    planes: Planes,
    correction: ColorCorrection = KNOWN_CORRECTION,
    space: RgbSpace = RgbSpace.DISPLAY_P3,
    mirrored: bool = False,
    color_range: ColorRange = ColorRange.FULL,
) -> ColorSample:
    frame = resized_frame(reduced_frame(planes, color_range), SAMPLE_WIDTH, SAMPLE_HEIGHT, mirrored)
    shown = srgb_to(rendered_rgb(correction, frame.luma, frame.blue, frame.red), space)
    return ColorSample(space, to_uint8(shown * 255), CAPTURED_AT)


def known_matches(seeds: tuple[int, ...]) -> list[SampleMatch]:
    matches: list[SampleMatch] = []
    for seed in seeds:
        planes = scene_planes(seed)
        match = best_match([reduced_frame(planes, ColorRange.FULL)], phone_sample(planes))
        assert match is not None
        matches.append(match)
    return matches


def color_sample_message(sample: ColorSample) -> str:
    return json.dumps(
        {
            "type": "color_sample",
            "colorSpace": sample.color_space.value,
            "width": sample.width,
            "height": sample.height,
            "rgb": base64.b64encode(sample.pixels.tobytes()).decode(),
            "capturedAt": sample.captured_at,
        }
    )


async def settled(calibrator: ColorCalibrator, state: CalibrationState) -> None:
    async with asyncio.timeout(SETTLE_SECONDS):
        while True:
            if calibrator.status.state is state:
                return
            await asyncio.sleep(POLL_SECONDS)


def file_names(folder: Path) -> list[str]:
    return sorted(path.name for path in folder.iterdir())


def calibrator_with_scenes(seeds: tuple[int, ...], trace: ColorTrace | None = None) -> ColorCalibrator:
    calibrator = ColorCalibrator(trace, match_delay=0.0)
    for seed in seeds:
        calibrator.remember(scene_planes(seed), ColorRange.FULL)
    return calibrator


def test_fit_recovers_known_tone_curve_and_saturation() -> None:
    result = fit_correction(known_matches((1, 2, 3)))

    assert result.correction is not None
    assert np.abs(np.array(result.correction.curve) - np.array(KNOWN_CORRECTION.curve)).max() < CURVE_TOLERANCE
    assert abs(result.correction.saturation - KNOWN_SATURATION) < SATURATION_TOLERANCE
    assert result.delta_e < RECOVERED_DELTA_E


def test_sample_of_another_scene_is_discarded() -> None:
    match = best_match([reduced_frame(scene_planes(1), ColorRange.FULL)], phone_sample(scene_planes(2)))

    assert match is not None
    assert not match.accepted


def test_sample_is_matched_to_the_frame_it_shows() -> None:
    frames = [reduced_frame(scene_planes(seed), ColorRange.FULL) for seed in (1, 2, 3)]

    match = best_match(frames, phone_sample(scene_planes(2)))

    assert match is not None
    assert match.accepted
    assert not match.mirrored
    assert np.allclose(match.frame.luma, resized_frame(frames[1], SAMPLE_WIDTH, SAMPLE_HEIGHT, False).luma)


def test_mirrored_sample_is_matched_mirrored() -> None:
    planes = scene_planes(4)

    match = best_match([reduced_frame(planes, ColorRange.FULL)], phone_sample(planes, mirrored=True))

    assert match is not None
    assert match.accepted
    assert match.mirrored


def test_sample_without_frames_has_no_match() -> None:
    assert best_match([], phone_sample(scene_planes(1))) is None


def test_identity_correction_tables_equal_range_tables() -> None:
    assert correction_tables(IDENTITY_CORRECTION, ColorRange.FULL) == (LUMA_TABLE.tobytes(), CHROMA_TABLE.tobytes())


def test_correction_tables_apply_curve_and_saturation_on_limited_output() -> None:
    luma_table, chroma_table = correction_tables(KNOWN_CORRECTION, ColorRange.FULL)

    assert (luma_table[0], luma_table[255]) == (16, 235)
    assert luma_table[128] == round(16 + 219 * float(KNOWN_CORRECTION.tone(np.array(128 / 255))))
    assert chroma_table[128] == 128
    assert chroma_table[160] == round(128 + 224 * KNOWN_SATURATION * (160 - 128) / 255)
    assert (chroma_table[0], chroma_table[255]) == (16, 240)


def test_without_correction_limited_frames_are_not_translated() -> None:
    assert applied_tables(None, ColorRange.LIMITED) is None
    assert applied_tables(None, ColorRange.UNSPECIFIED) is None


async def test_three_valid_samples_apply_the_calibration() -> None:
    seeds = (1, 2, 3)
    calibrator = calibrator_with_scenes(seeds)

    for seed in seeds:
        calibrator.add_sample(phone_sample(scene_planes(seed)))
    await settled(calibrator, CalibrationState.APPLIED)

    assert calibrator.correction is not None
    assert calibrator.status.delta_e is not None
    assert calibrator.status.delta_e < APPLIED_DELTA_E


async def test_without_three_valid_samples_state_is_default() -> None:
    calibrator = calibrator_with_scenes((1, 2))

    for seed in (1, 2, 5, 6, 7):
        calibrator.add_sample(phone_sample(scene_planes(seed)))
    await settled(calibrator, CalibrationState.DEFAULT)

    assert calibrator.correction is None
    assert calibrator.status.delta_e is None


async def test_restart_discards_the_calibration_and_its_frames() -> None:
    seeds = (1, 2, 3)
    calibrator = calibrator_with_scenes(seeds)
    for seed in seeds:
        calibrator.add_sample(phone_sample(scene_planes(seed)))
    await settled(calibrator, CalibrationState.APPLIED)

    calibrator.restart()
    assert calibrator.status.state is CalibrationState.MEASURING
    assert calibrator.correction is None
    for seed in (*seeds, 1, 2):
        calibrator.add_sample(phone_sample(scene_planes(seed)))
    await settled(calibrator, CalibrationState.DEFAULT)

    assert calibrator.correction is None


def test_default_calibration_keeps_range_only_output_byte_for_byte() -> None:
    pipeline, sink = live_pipeline()
    image = random_i420(1920, 1080)

    pipeline.deliver(VideoFrame.from_ndarray(image, format="yuvj420p"))

    assert pipeline.color_calibrator.status.state is CalibrationState.MEASURING
    assert sink.last_frame is not None
    assert np.array_equal(sink.last_frame[:OUTPUT_HEIGHT], LUMA_TABLE[image[:OUTPUT_HEIGHT]])
    assert np.array_equal(sink.last_frame[OUTPUT_HEIGHT:], CHROMA_TABLE[image[OUTPUT_HEIGHT:]])


def test_applied_calibration_reaches_the_sink_through_the_composed_tables() -> None:
    pipeline, sink = live_pipeline()
    image = random_i420(1920, 1080)
    pipeline.color_calibrator.correction = KNOWN_CORRECTION
    luma_table, chroma_table = (
        np.frombuffer(table, dtype=np.uint8) for table in correction_tables(KNOWN_CORRECTION, ColorRange.FULL)
    )

    pipeline.deliver(VideoFrame.from_ndarray(image, format="yuvj420p"))

    assert sink.last_frame is not None
    assert np.array_equal(sink.last_frame[:OUTPUT_HEIGHT], luma_table[image[:OUTPUT_HEIGHT]])
    assert np.array_equal(sink.last_frame[OUTPUT_HEIGHT:], chroma_table[image[OUTPUT_HEIGHT:]])


def test_new_phone_session_starts_measuring_without_correction() -> None:
    pipeline, _ = live_pipeline()
    pipeline.color_calibrator.correction = KNOWN_CORRECTION

    pipeline.stop_phone()
    pipeline.start_phone()

    assert pipeline.color_calibrator.correction is None
    assert pipeline.color_calibrator.status.state is CalibrationState.MEASURING


async def test_color_sample_in_live_reaches_the_peer() -> None:
    factory = FakePeerFactory()
    await live_manager(factory)
    sample = phone_sample(scene_planes(1))

    factory.last.events.on_message(color_sample_message(sample))

    [received] = factory.last.color_samples
    assert received.color_space is RgbSpace.DISPLAY_P3
    assert np.array_equal(received.pixels, sample.pixels)
    assert received.captured_at == CAPTURED_AT


async def test_color_sample_before_live_is_ignored(caplog: pytest.LogCaptureFixture) -> None:
    factory = FakePeerFactory()
    await connected_manager(factory)

    with caplog.at_level(logging.WARNING):
        factory.last.events.on_message(color_sample_message(phone_sample(scene_planes(1))))

    assert factory.last.color_samples == []
    assert COLOR_SAMPLE_BEFORE_LIVE in caplog.text


async def test_color_sample_with_wrong_pixel_count_is_ignored(caplog: pytest.LogCaptureFixture) -> None:
    factory = FakePeerFactory()
    await live_manager(factory)
    message = json.loads(color_sample_message(phone_sample(scene_planes(1))))
    message["width"] = SAMPLE_WIDTH + 1

    with caplog.at_level(logging.WARNING):
        factory.last.events.on_message(json.dumps(message))

    assert factory.last.color_samples == []
    assert IGNORED_PHONE_MESSAGE in caplog.text


async def test_camera_switch_restarts_the_calibration() -> None:
    factory = FakePeerFactory()
    await live_manager(factory)
    capabilities = {
        "type": "camera_capabilities",
        "width": 3840,
        "height": 2160,
        "frameRate": 60.0,
        "facingMode": "environment",
        "codecs": ["video/H264"],
    }

    factory.last.events.on_message(json.dumps(capabilities))

    assert factory.last.color_calibration_restarts == 1


async def test_trace_records_each_sample_and_the_calibration(tmp_path: Path) -> None:
    seeds = (1, 2, 3)
    calibrator = calibrator_with_scenes(seeds, ColorTrace(tmp_path))

    for seed in seeds:
        calibrator.add_sample(phone_sample(scene_planes(seed)))
    await settled(calibrator, CalibrationState.APPLIED)
    correction = calibrator.correction
    calibrator.close()

    first = json.loads((tmp_path / "color-sample-1.json").read_text(encoding="utf-8"))
    calibration = json.loads((tmp_path / "color-calibration.json").read_text(encoding="utf-8"))
    decoded_luma = np.frombuffer(base64.b64decode(first["matchedFrame"]["y"]), dtype=np.uint8)
    expected_luma = np.rint(block_mean(scene_planes(1)[0], SAMPLE_WIDTH, SAMPLE_HEIGHT)).reshape(-1)
    assert (first["calibrationState"], first["colorRange"], first["mirrored"]) == ("measuring", "full", False)
    assert first["correlation"] >= MIN_CORRELATION
    assert first["capturedAt"] == CAPTURED_AT
    assert np.abs(decoded_luma.astype(int) - expected_luma).max() <= 1
    assert calibration["state"] == "applied"
    assert calibration["rangeTables"]["y"] == LUMA_TABLE.tolist()
    assert calibration["rangeTables"]["u"] == CHROMA_TABLE.tolist()
    assert correction is not None
    applied_luma, applied_chroma = correction_tables(correction, ColorRange.FULL)
    assert calibration["appliedTables"]["y"] == list(applied_luma)
    assert calibration["appliedTables"]["v"] == list(applied_chroma)
    assert file_names(tmp_path) == [
        "color-calibration.json",
        "color-sample-1.json",
        "color-sample-2.json",
        "color-sample-3.json",
    ]

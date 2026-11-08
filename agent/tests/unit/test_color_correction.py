import json
import logging

import numpy as np
import pytest
from av import VideoFrame

from tests.conftest import console_app, console_client
from tests.fakes import FakePeerFactory
from tests.unit.test_pipeline import live_pipeline, random_i420
from tests.unit.test_session_manager import connected_manager, session_request
from wcam.config import Settings
from wcam.media.color_correction import (
    HDR_LEFT_UNCORRECTED,
    CameraColorSpace,
    ColorCorrection,
    CorrectionState,
    DisplayConvention,
    apple_display_tables,
    color_correction,
    correction_tables,
)
from wcam.media.color_difference import encode_srgb_curve
from wcam.media.color_range import CHROMA_TABLE, LUMA_TABLE, ColorRange
from wcam.media.metrics import VideoStats
from wcam.sessions.device import display_convention
from wcam.sessions.manager import SessionManager, SessionRequest
from wcam.virtualcam.sink import OUTPUT_HEIGHT, OUTPUT_WIDTH

APPLE_GAMMA = 1.961
IPHONE_COLOR_SPACE = CameraColorSpace("bt709", "bt709", "bt709", True)
IPHONE_SAFARI = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/18.1 Mobile/15E148 Safari/604.1"
)
IPHONE_CHROME = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "CriOS/131.0.6778.73 Mobile/15E148 Safari/604.1"
)
IPAD_SAFARI = (
    "Mozilla/5.0 (iPad; CPU OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 "
    "Mobile/15E148 Safari/604.1"
)
MAC_SAFARI = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 "
    "Safari/605.1.15"
)
MAC_CHROME = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
ANDROID_CHROME = (
    "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile "
    "Safari/537.36"
)
WINDOWS_EDGE = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 "
    "Safari/537.36 Edg/131.0.0.0"
)
IPHONE_CAPABILITIES: dict[str, object] = {
    "type": "camera_capabilities",
    "width": 4032,
    "height": 3024,
    "frameRate": 60.0,
    "facingMode": "user",
    "codecs": ["video/H264"],
    "colorSpace": {"primaries": "bt709", "transfer": "bt709", "matrix": "bt709", "fullRange": True},
}


def expected_apple_luma(index: int, color_range: ColorRange) -> float:
    normalized = index / 255 if color_range is ColorRange.FULL else (index - 16) / 219
    displayed = float(encode_srgb_curve(np.array(np.clip(normalized, 0, 1) ** APPLE_GAMMA)))
    return 16 + 219 * displayed


def apple_request(manager: SessionManager) -> SessionRequest:
    request = session_request(manager.open_pairing().token)
    return SessionRequest(
        request.token, request.offer_sdp, request.remote_ip, "iPhone · Safari", DisplayConvention.APPLE
    )


@pytest.mark.parametrize("color_range", [ColorRange.FULL, ColorRange.LIMITED])
def test_apple_table_matches_the_display_curve_within_one_code(color_range: ColorRange) -> None:
    luma_table, _ = apple_display_tables(color_range)

    differences = [abs(luma_table[index] - round(expected_apple_luma(index, color_range))) for index in range(256)]

    assert max(differences) <= 1


def test_apple_table_keeps_black_white_and_the_range_chroma() -> None:
    luma_table, chroma_table = apple_display_tables(ColorRange.FULL)

    assert (luma_table[0], luma_table[255]) == (16, 235)
    assert chroma_table == CHROMA_TABLE.tobytes()
    assert luma_table[128] > LUMA_TABLE[128]


def test_iphone_declaring_bt709_on_apple_display_is_applied() -> None:
    correction = color_correction(IPHONE_COLOR_SPACE, DisplayConvention.APPLE)

    assert correction == ColorCorrection(CorrectionState.APPLIED, "bt709", DisplayConvention.APPLE, True)


@pytest.mark.parametrize(
    ("color_space", "display"),
    [
        (None, DisplayConvention.APPLE),
        (CameraColorSpace("bt709", "iec61966-2-1", "bt709", True), DisplayConvention.APPLE),
        (CameraColorSpace("bt709", "srgb", "bt709", True), DisplayConvention.APPLE),
        (CameraColorSpace("bt2020", "pq", "bt2020-ncl", False), DisplayConvention.APPLE),
        (CameraColorSpace("bt2020", "hlg", "bt2020-ncl", False), DisplayConvention.APPLE),
        (CameraColorSpace(None, None, None, None), DisplayConvention.APPLE),
        (IPHONE_COLOR_SPACE, DisplayConvention.STANDARD),
        (CameraColorSpace("smpte170m", "smpte170m", "smpte170m", False), DisplayConvention.STANDARD),
    ],
)
def test_other_cameras_and_displays_keep_only_the_range(
    color_space: CameraColorSpace | None, display: DisplayConvention
) -> None:
    correction = color_correction(color_space, display)

    assert correction.state is CorrectionState.DEFAULT


def test_hdr_camera_is_logged_and_left_uncorrected(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        correction = color_correction(CameraColorSpace("bt2020", "pq", "bt2020-ncl", True), DisplayConvention.APPLE)

    assert correction.state is CorrectionState.DEFAULT
    assert HDR_LEFT_UNCORRECTED in caplog.text


def test_default_correction_output_is_byte_for_byte_range_only() -> None:
    pipeline, sink = live_pipeline()
    image = random_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT)
    pipeline.color_correction = color_correction(IPHONE_COLOR_SPACE, DisplayConvention.STANDARD)

    pipeline.deliver(VideoFrame.from_ndarray(image, format="yuvj420p"))

    assert sink.last_frame is not None
    assert np.array_equal(sink.last_frame[:OUTPUT_HEIGHT], LUMA_TABLE[image[:OUTPUT_HEIGHT]])
    assert np.array_equal(sink.last_frame[OUTPUT_HEIGHT:], CHROMA_TABLE[image[OUTPUT_HEIGHT:]])


def test_default_correction_leaves_limited_range_frames_untouched() -> None:
    pipeline, sink = live_pipeline()
    image = random_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT)
    pipeline.color_correction = color_correction(None, DisplayConvention.APPLE)

    pipeline.deliver(VideoFrame.from_ndarray(image, format="yuv420p"))

    assert sink.last_frame is not None
    assert np.array_equal(sink.last_frame, image)


def test_applied_correction_reaches_the_sink_through_the_composed_tables() -> None:
    pipeline, sink = live_pipeline()
    image = random_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT)
    pipeline.color_correction = color_correction(IPHONE_COLOR_SPACE, DisplayConvention.APPLE)
    luma_table, chroma_table = (np.frombuffer(table, np.uint8) for table in apple_display_tables(ColorRange.FULL))

    pipeline.deliver(VideoFrame.from_ndarray(image, format="yuvj420p"))

    assert sink.last_frame is not None
    assert np.array_equal(sink.last_frame[:OUTPUT_HEIGHT], luma_table[image[:OUTPUT_HEIGHT]])
    assert np.array_equal(sink.last_frame[OUTPUT_HEIGHT:], chroma_table[image[OUTPUT_HEIGHT:]])


def test_declared_full_range_wins_over_an_unspecified_frame() -> None:
    correction = color_correction(IPHONE_COLOR_SPACE, DisplayConvention.APPLE)

    assert correction_tables(correction, ColorRange.UNSPECIFIED) == apple_display_tables(ColorRange.FULL)


def test_declared_limited_range_wins_over_a_full_range_frame() -> None:
    correction = color_correction(CameraColorSpace("bt709", "bt709", "bt709", False), DisplayConvention.STANDARD)

    assert correction_tables(correction, ColorRange.FULL) is None


@pytest.mark.parametrize(
    ("user_agent", "expected"),
    [
        (IPHONE_SAFARI, DisplayConvention.APPLE),
        (IPHONE_CHROME, DisplayConvention.APPLE),
        (IPAD_SAFARI, DisplayConvention.APPLE),
        (MAC_SAFARI, DisplayConvention.APPLE),
        (MAC_CHROME, DisplayConvention.STANDARD),
        (ANDROID_CHROME, DisplayConvention.STANDARD),
        (WINDOWS_EDGE, DisplayConvention.STANDARD),
        ("", DisplayConvention.STANDARD),
    ],
)
def test_display_convention_comes_from_the_user_agent(user_agent: str, expected: DisplayConvention) -> None:
    assert display_convention(user_agent) is expected


async def test_each_camera_capabilities_reapplies_the_correction() -> None:
    factory = FakePeerFactory()
    manager = SessionManager(factory)
    await manager.create_session(apple_request(manager))
    factory.last.events.on_connected()
    rear = {**IPHONE_CAPABILITIES, "facingMode": "environment"}

    for capabilities in (IPHONE_CAPABILITIES, rear):
        factory.last.events.on_message(json.dumps(capabilities))

    states = [correction.state for correction in factory.last.color_corrections]
    assert states == [CorrectionState.DEFAULT, CorrectionState.APPLIED, CorrectionState.APPLIED]


async def test_next_connection_starts_without_the_previous_correction() -> None:
    factory = FakePeerFactory()
    manager = SessionManager(factory)
    await manager.create_session(apple_request(manager))
    factory.last.events.on_connected()
    factory.last.events.on_message(json.dumps(IPHONE_CAPABILITIES))
    await manager.disconnect()

    await manager.create_session(apple_request(manager))

    assert [correction.state for correction in factory.last.color_corrections] == [CorrectionState.DEFAULT]


def test_stopping_the_phone_drops_the_correction() -> None:
    pipeline, _ = live_pipeline()
    pipeline.color_correction = color_correction(IPHONE_COLOR_SPACE, DisplayConvention.APPLE)

    pipeline.stop_phone()

    assert pipeline.color_correction is None


async def test_status_reports_the_color_correction_and_the_declared_color_space(settings: Settings) -> None:
    factory = FakePeerFactory()
    manager = await connected_manager(factory)
    factory.last.events.on_message(json.dumps(IPHONE_CAPABILITIES))
    correction = color_correction(IPHONE_COLOR_SPACE, DisplayConvention.APPLE)
    factory.last.video = VideoStats(1920, 1080, 30.0, 9800, color_correction=correction)

    async with console_client(console_app(settings, manager)) as console:
        session = (await console.get("/api/status")).json()["session"]

    assert session["video"]["colorCorrection"] == {"state": "applied", "transfer": "bt709", "display": "apple"}
    assert session["cameraCapabilities"]["colorSpace"] == {
        "primaries": "bt709",
        "transfer": "bt709",
        "matrix": "bt709",
        "fullRange": True,
    }

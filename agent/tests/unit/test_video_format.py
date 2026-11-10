import json
import logging

import pytest

from tests.fakes import FakePeerFactory
from tests.unit.test_session_manager import connected_manager, session_request
from wcam.media.video_format import (
    DEFAULT_VIDEO_FORMAT,
    CameraLimits,
    VideoFormat,
    available_formats,
    format_after_capabilities,
    format_of,
    largest_format,
)
from wcam.sessions.errors import UnavailableVideoFormatError
from wcam.sessions.manager import (
    FORMAT_BEFORE_LIVE,
    IGNORED_PHONE_MESSAGE,
    UNAVAILABLE_FORMAT_FROM_PHONE,
    SessionManager,
)

ALL_FORMATS = ["720p30", "720p60", "1080p30", "1440p30", "2160p30"]
CAPABILITIES = {
    "type": "camera_capabilities",
    "width": 3840,
    "height": 2160,
    "frameRate": 60,
    "facingMode": "environment",
    "codecs": ["video/H264", "video/VP8"],
}
HD_CAMERA = {**CAPABILITIES, "width": 1920, "height": 1080, "frameRate": 30}
INVALID_MESSAGES = [
    "not json",
    "[]",
    json.dumps({"format": "1080p30"}),
    json.dumps({"type": "unknown"}),
    json.dumps({"type": "set_video_format"}),
    json.dumps({"type": "set_video_format", "format": "4320p30"}),
    json.dumps({"type": "set_video_format", "format": 1080}),
    json.dumps({"type": "set_quality_preset", "preset": "maximum"}),
    json.dumps({**CAPABILITIES, "width": "3840"}),
    json.dumps({**CAPABILITIES, "height": -1}),
    json.dumps({**CAPABILITIES, "frameRate": 0}),
    json.dumps({**CAPABILITIES, "facingMode": "left"}),
    json.dumps({**CAPABILITIES, "codecs": "video/H264"}),
    json.dumps({**CAPABILITIES, "codecs": [1]}),
    json.dumps({key: value for key, value in CAPABILITIES.items() if key != "codecs"}),
]


def video_format_message(video_format: str, available: list[str]) -> dict[str, object]:
    size = VideoFormat(video_format).size
    return {
        "type": "video_format",
        "format": video_format,
        "width": size.width,
        "height": size.height,
        "fps": size.fps,
        "maxBitrate": size.max_bitrate_bps,
        "available": available,
    }


async def live_manager(factory: FakePeerFactory) -> SessionManager:
    manager = await connected_manager(factory)
    manager.confirm()
    factory.last.sent.clear()
    return manager


async def live_manager_with_capabilities(factory: FakePeerFactory) -> SessionManager:
    manager = await live_manager(factory)
    factory.last.events.on_message(json.dumps(CAPABILITIES))
    factory.last.sent.clear()
    return manager


def test_formats_follow_the_contract_table() -> None:
    sizes = [(f.size.width, f.size.height, f.size.fps, f.size.max_bitrate_bps) for f in VideoFormat]

    assert [str(video_format) for video_format in VideoFormat] == ALL_FORMATS
    assert sizes == [
        (1280, 720, 30, 5_000_000),
        (1280, 720, 60, 8_000_000),
        (1920, 1080, 30, 10_000_000),
        (2560, 1440, 30, 18_000_000),
        (3840, 2160, 30, 35_000_000),
    ]


def test_only_the_default_is_available_before_capabilities() -> None:
    assert available_formats(None) == (VideoFormat.FULL_HD_30,)


def test_formats_that_fit_the_camera_are_available() -> None:
    limits = CameraLimits(1920, 1080, 60)

    assert available_formats(limits) == (VideoFormat.HD_30, VideoFormat.HD_60, VideoFormat.FULL_HD_30)


def test_portrait_camera_limits_are_compared_in_landscape() -> None:
    assert available_formats(CameraLimits(2160, 3840, 30)) == available_formats(CameraLimits(3840, 2160, 30))


def test_frame_rate_slightly_below_sixty_still_offers_sixty() -> None:
    assert VideoFormat.HD_60 in available_formats(CameraLimits(1280, 720, 59.94))


def test_unknown_camera_limits_use_the_default_format_values() -> None:
    assert available_formats(CameraLimits(None, None, None)) == (VideoFormat.HD_30, VideoFormat.FULL_HD_30)


def test_camera_below_every_format_still_offers_the_default() -> None:
    assert available_formats(CameraLimits(640, 480, 30)) == (DEFAULT_VIDEO_FORMAT,)


def test_largest_format_prefers_pixels_then_fps() -> None:
    assert largest_format((VideoFormat.HD_60, VideoFormat.FULL_HD_30)) is VideoFormat.FULL_HD_30
    assert largest_format((VideoFormat.HD_30, VideoFormat.HD_60)) is VideoFormat.HD_60


def test_selected_format_outside_the_new_capabilities_falls_to_the_largest() -> None:
    available = (VideoFormat.HD_30, VideoFormat.HD_60, VideoFormat.FULL_HD_30)

    assert format_after_capabilities(VideoFormat.UHD_30, available) is VideoFormat.FULL_HD_30
    assert format_after_capabilities(VideoFormat.HD_60, available) is VideoFormat.HD_60


def test_size_and_fps_map_back_to_the_format() -> None:
    assert format_of(1280, 720, 60) is VideoFormat.HD_60
    assert format_of(1280, 720, 25) is None


def test_status_starts_with_the_default_format() -> None:
    state = SessionManager(FakePeerFactory()).status().video_format

    assert (state.selected, state.available, state.camera, state.pending) == (
        VideoFormat.FULL_HD_30,
        (VideoFormat.FULL_HD_30,),
        VideoFormat.FULL_HD_30,
        False,
    )


def test_format_outside_the_available_ones_is_refused() -> None:
    manager = SessionManager(FakePeerFactory())

    with pytest.raises(UnavailableVideoFormatError):
        manager.set_video_format(VideoFormat.UHD_30)

    assert manager.status().video_format.selected is VideoFormat.FULL_HD_30


async def test_channel_opening_sends_the_format_and_its_bitrate() -> None:
    factory = FakePeerFactory()
    manager = SessionManager(factory)

    await manager.create_session(session_request(manager.open_pairing().token))
    factory.last.events.on_connected()

    assert video_format_message("1080p30", ["1080p30"]) in factory.last.sent
    assert factory.last.max_bitrate_bps == VideoFormat.FULL_HD_30.size.max_bitrate_bps


async def test_capabilities_offer_the_formats_that_fit_and_tell_the_phone() -> None:
    factory = FakePeerFactory()
    manager = await live_manager(factory)

    factory.last.events.on_message(json.dumps(CAPABILITIES))

    assert manager.status().video_format.available == tuple(VideoFormat)
    assert factory.last.sent == [video_format_message("1080p30", ALL_FORMATS)]


async def test_console_change_limits_the_bitrate_and_tells_the_phone() -> None:
    factory = FakePeerFactory()
    manager = await live_manager_with_capabilities(factory)

    manager.set_video_format(VideoFormat.UHD_30)

    assert manager.status().video_format.selected is VideoFormat.UHD_30
    assert factory.last.max_bitrate_bps == VideoFormat.UHD_30.size.max_bitrate_bps
    assert factory.last.sent == [video_format_message("2160p30", ALL_FORMATS)]


async def test_phone_change_while_live_is_applied_and_echoed_to_the_phone() -> None:
    factory = FakePeerFactory()
    manager = await live_manager_with_capabilities(factory)

    factory.last.events.on_message(json.dumps({"type": "set_video_format", "format": "720p60"}))

    assert manager.status().video_format.selected is VideoFormat.HD_60
    assert factory.last.max_bitrate_bps == VideoFormat.HD_60.size.max_bitrate_bps
    assert factory.last.sent == [video_format_message("720p60", ALL_FORMATS)]


async def test_phone_change_before_confirmation_is_ignored(caplog: pytest.LogCaptureFixture) -> None:
    factory = FakePeerFactory()
    manager = await connected_manager(factory)
    factory.last.events.on_message(json.dumps(CAPABILITIES))
    factory.last.sent.clear()

    with caplog.at_level(logging.WARNING):
        factory.last.events.on_message(json.dumps({"type": "set_video_format", "format": "720p60"}))

    assert manager.status().video_format.selected is VideoFormat.FULL_HD_30
    assert FORMAT_BEFORE_LIVE in caplog.text
    assert factory.last.sent == []


async def test_phone_format_outside_available_is_ignored_and_the_current_one_resent(
    caplog: pytest.LogCaptureFixture,
) -> None:
    factory = FakePeerFactory()
    manager = await live_manager(factory)

    with caplog.at_level(logging.WARNING):
        factory.last.events.on_message(json.dumps({"type": "set_video_format", "format": "2160p30"}))

    assert manager.status().video_format.selected is VideoFormat.FULL_HD_30
    assert UNAVAILABLE_FORMAT_FROM_PHONE in caplog.text
    assert factory.last.sent == [video_format_message("1080p30", ["1080p30"])]


async def test_new_camera_without_the_chosen_format_falls_to_the_largest_offered() -> None:
    factory = FakePeerFactory()
    manager = await live_manager_with_capabilities(factory)
    manager.set_video_format(VideoFormat.UHD_30)
    factory.last.sent.clear()

    factory.last.events.on_message(json.dumps(HD_CAMERA))

    assert manager.status().video_format.selected is VideoFormat.FULL_HD_30
    assert factory.last.max_bitrate_bps == VideoFormat.FULL_HD_30.size.max_bitrate_bps
    assert factory.last.sent[-1] == video_format_message("1080p30", ["720p30", "1080p30"])


async def test_chosen_format_lasts_into_the_next_session() -> None:
    factory = FakePeerFactory()
    manager = await live_manager_with_capabilities(factory)
    manager.set_video_format(VideoFormat.HD_60)
    await manager.disconnect()

    await manager.create_session(session_request(manager.open_pairing().token))
    factory.last.events.on_connected()

    assert factory.last.max_bitrate_bps == VideoFormat.HD_60.size.max_bitrate_bps
    assert video_format_message("720p60", ALL_FORMATS) in factory.last.sent


async def test_camera_capabilities_are_kept_in_the_session() -> None:
    factory = FakePeerFactory()
    manager = await connected_manager(factory)

    factory.last.events.on_message(json.dumps(CAPABILITIES))

    session = manager.status().session
    assert session is not None
    assert session.camera_capabilities is not None
    assert session.camera_capabilities.width == CAPABILITIES["width"]
    assert session.camera_capabilities.frame_rate == CAPABILITIES["frameRate"]
    assert session.camera_capabilities.facing_mode == "environment"
    assert session.camera_capabilities.codecs == ("video/H264", "video/VP8")


@pytest.mark.parametrize("data", INVALID_MESSAGES)
async def test_invalid_phone_message_is_logged_and_ignored(data: str, caplog: pytest.LogCaptureFixture) -> None:
    factory = FakePeerFactory()
    manager = await live_manager(factory)

    with caplog.at_level(logging.WARNING):
        factory.last.events.on_message(data)

    session = manager.status().session
    assert session is not None
    assert session.camera_capabilities is None
    assert manager.status().video_format.selected is VideoFormat.FULL_HD_30
    assert IGNORED_PHONE_MESSAGE in caplog.text
    assert not factory.last.closed
    assert factory.last.sent == []

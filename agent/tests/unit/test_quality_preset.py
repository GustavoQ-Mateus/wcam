import json
import logging

import pytest

from tests.fakes import FakePeerFactory
from tests.unit.test_session_manager import connected_manager, session_request
from wcam.media.quality_preset import QualityPreset
from wcam.sessions.manager import IGNORED_PHONE_MESSAGE, PRESET_BEFORE_LIVE, SessionManager

CAPABILITIES = {
    "type": "camera_capabilities",
    "width": 3840,
    "height": 2160,
    "frameRate": 60,
    "facingMode": "environment",
    "codecs": ["video/H264", "video/VP8"],
}
INVALID_MESSAGES = [
    "not json",
    "[]",
    json.dumps({"preset": "maximum"}),
    json.dumps({"type": "unknown"}),
    json.dumps({"type": "set_quality_preset"}),
    json.dumps({"type": "set_quality_preset", "preset": "ultra"}),
    json.dumps({"type": "set_quality_preset", "preset": 1}),
    json.dumps({**CAPABILITIES, "width": "3840"}),
    json.dumps({**CAPABILITIES, "height": -1}),
    json.dumps({**CAPABILITIES, "frameRate": 0}),
    json.dumps({**CAPABILITIES, "facingMode": "left"}),
    json.dumps({**CAPABILITIES, "codecs": "video/H264"}),
    json.dumps({**CAPABILITIES, "codecs": [1]}),
    json.dumps({key: value for key, value in CAPABILITIES.items() if key != "codecs"}),
]


async def live_manager(factory: FakePeerFactory) -> SessionManager:
    manager = await connected_manager(factory)
    manager.confirm()
    factory.last.sent.clear()
    return manager


def test_quality_preset_defaults_to_balanced() -> None:
    assert SessionManager(FakePeerFactory()).status().quality_preset is QualityPreset.BALANCED


def test_presets_cap_the_bitrate_from_the_contract() -> None:
    assert [preset.max_bitrate_bps for preset in QualityPreset] == [20_000_000, 10_000_000, 5_000_000]


async def test_new_session_starts_with_the_bitrate_of_the_chosen_preset() -> None:
    factory = FakePeerFactory()
    manager = SessionManager(factory)
    manager.set_quality_preset(QualityPreset.LIGHT)

    await manager.create_session(session_request(manager.open_pairing().token))
    factory.last.events.on_connected()

    assert factory.last.max_bitrate_bps == QualityPreset.LIGHT.max_bitrate_bps
    assert {"type": "quality_preset", "preset": "light"} in factory.last.sent


async def test_console_change_limits_the_bitrate_and_tells_the_phone() -> None:
    factory = FakePeerFactory()
    manager = await live_manager(factory)

    manager.set_quality_preset(QualityPreset.MAXIMUM)

    assert manager.status().quality_preset is QualityPreset.MAXIMUM
    assert factory.last.max_bitrate_bps == QualityPreset.MAXIMUM.max_bitrate_bps
    assert factory.last.sent == [{"type": "quality_preset", "preset": "maximum"}]


async def test_phone_change_while_live_is_applied_and_echoed_to_the_phone() -> None:
    factory = FakePeerFactory()
    manager = await live_manager(factory)

    factory.last.events.on_message(json.dumps({"type": "set_quality_preset", "preset": "light"}))

    assert manager.status().quality_preset is QualityPreset.LIGHT
    assert factory.last.max_bitrate_bps == QualityPreset.LIGHT.max_bitrate_bps
    assert factory.last.sent == [{"type": "quality_preset", "preset": "light"}]


async def test_phone_change_before_confirmation_is_ignored(caplog: pytest.LogCaptureFixture) -> None:
    factory = FakePeerFactory()
    manager = await connected_manager(factory)

    with caplog.at_level(logging.WARNING):
        factory.last.events.on_message(json.dumps({"type": "set_quality_preset", "preset": "light"}))

    assert manager.status().quality_preset is QualityPreset.BALANCED
    assert PRESET_BEFORE_LIVE in caplog.text


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
    assert manager.status().quality_preset is QualityPreset.BALANCED
    assert IGNORED_PHONE_MESSAGE in caplog.text
    assert not factory.last.closed
    assert factory.last.sent == []

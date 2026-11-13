import json

import pytest

from tests.conftest import console_app, console_client
from tests.fakes import FakePeerFactory
from tests.unit.test_session_manager import confirm_on_both_sides, connected_manager, session_request
from wcam.config import Settings
from wcam.sessions.controls import Controls, ControlsChange, changed_controls
from wcam.sessions.errors import NoLiveSessionError
from wcam.sessions.manager import SessionManager

CAPABILITIES = {
    "type": "camera_capabilities",
    "width": 1920,
    "height": 1080,
    "frameRate": 30,
    "facingMode": "user",
    "codecs": ["video/H264"],
}


class RecordingOutput:
    def __init__(self) -> None:
        self.applied: list[tuple[bool, bool, bool]] = []

    def apply_controls(self, frozen: bool, camera_off: bool, mirror: bool) -> None:
        self.applied.append((frozen, camera_off, mirror))


def controls_message(frozen: bool, camera_off: bool, mirror: bool, facing: str | None) -> dict[str, object]:
    return {"type": "controls", "frozen": frozen, "cameraOff": camera_off, "mirror": mirror, "facing": facing}


async def live_manager_with_output(factory: FakePeerFactory, output: RecordingOutput) -> SessionManager:
    manager = SessionManager(factory, output=output)
    await manager.create_session(session_request(manager.open_pairing().token))
    factory.last.events.on_connected()
    confirm_on_both_sides(manager, factory)
    factory.last.sent.clear()
    return manager


def test_turning_the_camera_off_unfreezes_the_image() -> None:
    controls = changed_controls(Controls(frozen=True), ControlsChange(camera_off=True))

    assert (controls.frozen, controls.camera_off) == (False, True)


def test_freezing_with_the_camera_off_is_ignored() -> None:
    controls = changed_controls(Controls(camera_off=True), ControlsChange(frozen=True))

    assert (controls.frozen, controls.camera_off) == (False, True)


def test_turning_the_camera_on_unfreezes_the_image() -> None:
    controls = changed_controls(Controls(frozen=True), ControlsChange(camera_off=False))

    assert (controls.frozen, controls.camera_off) == (False, False)


def test_change_keeps_the_fields_it_does_not_name() -> None:
    controls = changed_controls(Controls(mirror=True, facing="user"), ControlsChange(frozen=True))

    assert controls == Controls(frozen=True, mirror=True, facing="user")


async def test_freezing_without_a_live_phone_is_refused() -> None:
    manager = await connected_manager(FakePeerFactory())

    with pytest.raises(NoLiveSessionError):
        manager.change_controls(ControlsChange(frozen=True))


async def test_mirror_without_a_phone_reaches_the_output() -> None:
    output = RecordingOutput()
    manager = SessionManager(FakePeerFactory(), output=output)

    manager.change_controls(ControlsChange(mirror=True))

    assert manager.status().controls.mirror
    assert output.applied == [(False, False, True)]


async def test_going_live_sends_the_controls_to_the_phone() -> None:
    factory = FakePeerFactory()
    manager = await connected_manager(factory)

    confirm_on_both_sides(manager, factory)

    assert controls_message(False, False, False, None) in factory.last.sent


async def test_console_change_reaches_the_output_and_the_phone() -> None:
    factory = FakePeerFactory()
    output = RecordingOutput()
    manager = await live_manager_with_output(factory, output)

    manager.change_controls(ControlsChange(frozen=True))

    assert output.applied == [(True, False, False)]
    assert factory.last.sent == [controls_message(True, False, False, None)]


async def test_phone_change_is_applied_and_sent_back() -> None:
    factory = FakePeerFactory()
    output = RecordingOutput()
    manager = await live_manager_with_output(factory, output)

    factory.last.events.on_message(json.dumps({"type": "set_controls", "cameraOff": True}))

    assert manager.status().controls.camera_off
    assert output.applied == [(False, True, False)]
    assert factory.last.sent == [controls_message(False, True, False, None)]


async def test_phone_change_without_effect_still_gets_the_controls_back() -> None:
    factory = FakePeerFactory()
    manager = await live_manager_with_output(factory, RecordingOutput())

    factory.last.events.on_message(json.dumps({"type": "set_controls", "mirror": False}))

    assert manager.status().controls == Controls()
    assert factory.last.sent == [controls_message(False, False, False, None)]


async def test_switching_the_camera_asks_the_phone_for_the_other_one() -> None:
    factory = FakePeerFactory()
    manager = await live_manager_with_output(factory, RecordingOutput())

    manager.change_controls(ControlsChange(facing="user"))

    assert factory.last.sent == [controls_message(False, False, False, "user")]


async def test_camera_capabilities_report_the_camera_in_use() -> None:
    factory = FakePeerFactory()
    manager = await live_manager_with_output(factory, RecordingOutput())

    factory.last.events.on_message(json.dumps(CAPABILITIES))

    assert manager.status().controls.facing == "user"


async def test_end_of_the_session_unfreezes_and_turns_the_camera_on_but_keeps_the_mirror() -> None:
    factory = FakePeerFactory()
    output = RecordingOutput()
    manager = await live_manager_with_output(factory, output)
    manager.change_controls(ControlsChange(camera_off=True, mirror=True))

    await manager.disconnect()

    assert manager.status().controls == Controls(mirror=True)
    assert output.applied[-1] == (False, False, True)


async def test_controls_route_applies_the_change(settings: Settings) -> None:
    factory = FakePeerFactory()
    manager = await live_manager_with_output(factory, RecordingOutput())

    async with console_client(console_app(settings, manager)) as console:
        response = await console.patch("/api/controls", json={"frozen": True, "facing": "environment"})
        status = (await console.get("/api/status")).json()

    assert response.status_code == 204
    assert status["controls"] == {"frozen": True, "cameraOff": False, "mirror": False, "facing": "environment"}


async def test_controls_route_without_a_live_phone_answers_no_live_session(settings: Settings) -> None:
    async with console_client(console_app(settings)) as console:
        response = await console.patch("/api/controls", json={"cameraOff": True})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "no_live_session"


@pytest.mark.parametrize(
    "body",
    [{"paused": True}, {"frozen": "yes"}, {"facing": "left"}, {"camera_off": True}, {"mirror": 1}],
)
async def test_controls_route_refuses_unknown_or_mistyped_fields(settings: Settings, body: dict[str, object]) -> None:
    async with console_client(console_app(settings)) as console:
        response = await console.patch("/api/controls", json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


async def test_status_always_has_the_controls(settings: Settings) -> None:
    async with console_client(console_app(settings)) as console:
        status = (await console.get("/api/status")).json()

    assert status["controls"] == {"frozen": False, "cameraOff": False, "mirror": False, "facing": None}

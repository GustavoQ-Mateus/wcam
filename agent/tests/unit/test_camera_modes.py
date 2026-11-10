import json

from tests.conftest import console_app, console_client
from tests.fakes import FakePeerFactory
from tests.unit.test_session_manager import connected_manager
from wcam.config import Settings

CAPABILITIES: dict[str, object] = {
    "type": "camera_capabilities",
    "width": 3840,
    "height": 2160,
    "frameRate": 60.0,
    "facingMode": "environment",
    "codecs": ["video/H264"],
    "colorSpace": None,
}
CONTINUOUS_MODES = {"exposureMode": "continuous", "whiteBalanceMode": "continuous", "focusMode": "continuous"}


async def status_capabilities(settings: Settings, capabilities: dict[str, object]) -> dict[str, object]:
    factory = FakePeerFactory()
    manager = await connected_manager(factory)
    factory.last.events.on_message(json.dumps(capabilities))
    async with console_client(console_app(settings, manager)) as console:
        session = (await console.get("/api/status")).json()["session"]
    reported: dict[str, object] = session["cameraCapabilities"]
    return reported


async def test_camera_modes_reach_the_status(settings: Settings) -> None:
    reported = await status_capabilities(settings, {**CAPABILITIES, "modes": CONTINUOUS_MODES})

    assert reported["modes"] == CONTINUOUS_MODES


async def test_modes_the_browser_does_not_report_stay_null(settings: Settings) -> None:
    partial = {"exposureMode": "continuous", "whiteBalanceMode": None, "focusMode": None}

    reported = await status_capabilities(settings, {**CAPABILITIES, "modes": partial})

    assert reported["modes"] == partial


async def test_capabilities_without_modes_report_null(settings: Settings) -> None:
    reported = await status_capabilities(settings, CAPABILITIES)

    assert reported["modes"] is None

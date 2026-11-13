import pytest

from tests.conftest import console_app, console_client, opened_pipeline, phone_app, phone_client
from tests.fakes import OFFER_SDP, FakePeerFactory
from wcam.config import Settings
from wcam.sessions.manager import SessionManager
from wcam.virtualcam.fake_sink import FakeSink
from wcam.virtualcam.pyvirtualcam_sink import unavailable_reason
from wcam.virtualcam.sink import AnnouncedFormat, UnavailableReason


@pytest.mark.parametrize("reason", [UnavailableReason.DRIVER_MISSING, UnavailableReason.DEVICE_IN_USE])
async def test_unavailable_driver_keeps_agent_running_and_reports_reason(
    settings: Settings,
    reason: UnavailableReason,
) -> None:
    sink = FakeSink(failure=reason)
    pipeline = opened_pipeline(sink)
    manager = SessionManager(FakePeerFactory())

    async with console_client(console_app(settings, manager, pipeline)) as console:
        token = (await console.post("/api/pairing")).json()["url"].split("#t=")[1]
        async with phone_client(phone_app(settings, manager)) as phone:
            created = await phone.post("/api/sessions", json={"token": token, "sdp": OFFER_SDP})
        camera = (await console.get("/api/status")).json()["virtualCamera"]
    pipeline.deliver(None)

    assert created.status_code == 201
    assert camera == {
        "state": "unavailable",
        "backend": "fake",
        "reason": reason.value,
        "fallbackReason": None,
        "output": {"width": 1920, "height": 1080, "fps": 30},
        "source": "placeholder",
        "streamingApps": None,
    }
    assert sink.frames_sent == 0


async def test_active_virtual_camera_is_reported(settings: Settings) -> None:
    async with console_client(console_app(settings)) as console:
        status = (await console.get("/api/status")).json()

    assert status["virtualCamera"]["state"] == "active"
    assert status["virtualCamera"]["reason"] is None
    assert status["process"] == {"cpuPercent": 0.0}


async def test_apps_streaming_from_the_camera_are_reported(settings: Settings) -> None:
    pipeline = opened_pipeline()
    pipeline.follow(AnnouncedFormat(1920, 1080, 30, pending=False, running=True, streaming_apps=2))

    async with console_client(console_app(settings, SessionManager(FakePeerFactory()), pipeline)) as console:
        status = (await console.get("/api/status")).json()

    assert status["virtualCamera"]["streamingApps"] == 2


async def test_camera_without_app_count_reports_null(settings: Settings) -> None:
    async with console_client(console_app(settings)) as console:
        status = (await console.get("/api/status")).json()

    assert status["virtualCamera"]["streamingApps"] is None


def test_obs_errors_map_to_reasons() -> None:
    reasons = [
        unavailable_reason("'obs' backend: OBS Virtual Camera device not found! Did you install OBS?"),
        unavailable_reason("'obs' backend: virtual camera output could not be started"),
        unavailable_reason("'obs'"),
    ]

    assert reasons == [UnavailableReason.DRIVER_MISSING, UnavailableReason.DEVICE_IN_USE, UnavailableReason.ERROR]

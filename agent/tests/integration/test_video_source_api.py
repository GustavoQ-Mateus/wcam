from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from tests.conftest import LAN, console_client, fake_manager, opened_pipeline
from tests.integration.test_webrtc import wait_until
from tests.videos import SHORT_SECONDS, SMALL_HEIGHT, SMALL_WIDTH, small_video
from wcam.app import create_console_app, phone_page_url
from wcam.config import Settings
from wcam.media.camera_format import CameraFormatControl
from wcam.process_monitor import CpuMonitor
from wcam.services import AgentServices
from wcam.video.store import MAX_VIDEO_BYTES, VideoStore

TINY_LIMIT_BYTES = 10


def video_agent(tmp_path: Path, max_bytes: int = MAX_VIDEO_BYTES) -> AgentServices:
    pipeline = opened_pipeline()
    return AgentServices(
        fake_manager(),
        pipeline,
        CpuMonitor(),
        CameraFormatControl(pipeline),
        video_store=VideoStore(tmp_path / "video", max_bytes),
    )


def client_for(settings: Settings, agent: AgentServices) -> httpx.AsyncClient:
    return console_client(create_console_app(settings, agent, phone_page_url(settings, LAN)))


async def upload(console: httpx.AsyncClient, data: bytes, name: str = "reunião.mp4") -> httpx.Response:
    headers = {"X-File-Name": quote(name), "Content-Type": "application/octet-stream"}
    return await console.put("/api/video-source/file", content=data, headers=headers)


def error_code(response: httpx.Response) -> str:
    body: dict[str, Any] = response.json()
    return body["error"]["code"]


async def video_status(console: httpx.AsyncClient) -> dict[str, Any]:
    body: dict[str, Any] = (await console.get("/api/status")).json()
    return body["videoSource"]


async def wait_for_position(console: httpx.AsyncClient, agent: AgentServices) -> float:
    await wait_until(lambda: agent.video.view().position_seconds is not None)
    position: float = (await video_status(console))["positionSeconds"]
    return position


async def test_uploaded_video_is_described_in_the_answer_and_the_status(tmp_path: Path, settings: Settings) -> None:
    async with client_for(settings, video_agent(tmp_path)) as console:
        response = await upload(console, small_video(tmp_path).read_bytes())

        status = await video_status(console)

    assert response.status_code == 201
    expected = {
        "name": "reunião.mp4",
        "durationSeconds": SHORT_SECONDS,
        "width": SMALL_WIDTH,
        "height": SMALL_HEIGHT,
        "fps": 30.0,
        "codec": "h264",
    }
    assert response.json() == expected
    assert status == {"file": expected, "active": False, "positionSeconds": None}


async def test_file_that_is_not_a_video_is_refused_without_leaving_a_file(tmp_path: Path, settings: Settings) -> None:
    async with client_for(settings, video_agent(tmp_path)) as console:
        response = await upload(console, b"not a video at all", "notes.txt")

    assert (response.status_code, error_code(response)) == (422, "video_unsupported")
    assert list((tmp_path / "video").iterdir()) == []


async def test_video_above_the_limit_is_refused(tmp_path: Path, settings: Settings) -> None:
    async with client_for(settings, video_agent(tmp_path, TINY_LIMIT_BYTES)) as console:
        response = await upload(console, small_video(tmp_path).read_bytes())

    assert (response.status_code, error_code(response)) == (413, "video_too_large")


async def test_upload_without_a_name_is_invalid(tmp_path: Path, settings: Settings) -> None:
    async with client_for(settings, video_agent(tmp_path)) as console:
        response = await console.put("/api/video-source/file", content=b"data")

    assert (response.status_code, error_code(response)) == (422, "invalid_request")


async def test_without_a_video_using_it_conflicts_and_removing_is_not_found(tmp_path: Path, settings: Settings) -> None:
    async with client_for(settings, video_agent(tmp_path)) as console:
        use = await console.put("/api/video-source", json={"active": True})
        remove = await console.delete("/api/video-source/file")

    assert (use.status_code, error_code(use)) == (409, "no_video_file")
    assert (remove.status_code, error_code(remove)) == (404, "no_video_file")


async def test_active_video_plays_and_closes_pairing_until_turned_off(tmp_path: Path, settings: Settings) -> None:
    agent = video_agent(tmp_path)
    async with client_for(settings, agent) as console:
        await upload(console, small_video(tmp_path).read_bytes())
        try:
            use = await console.put("/api/video-source", json={"active": True})
            position = await wait_for_position(console, agent)
            pairing = await console.post("/api/pairing")
            jump = await console.put("/api/video-source/position", json={"seconds": 1.0})
            outside = await console.put("/api/video-source/position", json={"seconds": SHORT_SECONDS})
            freeze = await console.patch("/api/controls", json={"frozen": True})
            camera_off = await console.patch("/api/controls", json={"cameraOff": True})
        finally:
            stop = await console.put("/api/video-source", json={"active": False})
        stopped_jump = await console.put("/api/video-source/position", json={"seconds": 1.0})
        stopped_status = await video_status(console)
        pairing_again = await console.post("/api/pairing")

    assert use.status_code == 204
    assert 0 <= position < SHORT_SECONDS
    assert (pairing.status_code, error_code(pairing)) == (409, "video_source_active")
    assert jump.status_code == 204
    assert (outside.status_code, error_code(outside)) == (422, "invalid_request")
    assert freeze.status_code == 204
    assert (camera_off.status_code, error_code(camera_off)) == (409, "no_live_session")
    assert stop.status_code == 204
    assert (stopped_jump.status_code, error_code(stopped_jump)) == (409, "video_source_inactive")
    assert (stopped_status["active"], stopped_status["positionSeconds"]) == (False, None)
    assert pairing_again.status_code == 201


async def test_removing_an_active_video_turns_it_off_and_deletes_it(tmp_path: Path, settings: Settings) -> None:
    agent = video_agent(tmp_path)
    async with client_for(settings, agent) as console:
        await upload(console, small_video(tmp_path).read_bytes())
        await console.put("/api/video-source", json={"active": True})

        remove = await console.delete("/api/video-source/file")
        status = await video_status(console)

    assert remove.status_code == 204
    assert status == {"file": None, "active": False, "positionSeconds": None}
    assert list((tmp_path / "video").iterdir()) == []


async def test_activating_records_a_developer_event(tmp_path: Path, settings: Settings) -> None:
    agent = video_agent(tmp_path)
    async with client_for(settings, agent) as console:
        await upload(console, small_video(tmp_path).read_bytes(), "clip.mp4")
        await console.put("/api/video-source", json={"active": True})
        await console.put("/api/video-source", json={"active": False})

    events = agent.dev_events.subscribe()
    kinds = [(event.kind, dict(event.data)) for event in [events.get_nowait() for _ in range(events.qsize())]]
    assert ("video_source", {"active": True, "name": "clip.mp4"}) in kinds
    assert ("video_source", {"active": False, "name": "clip.mp4"}) in kinds

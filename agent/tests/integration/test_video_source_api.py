import asyncio
import io
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
import pytest
from PIL import Image

from tests.conftest import LAN, console_client, opened_pipeline
from tests.fakes import FakePeerFactory
from tests.integration.test_webrtc import wait_until
from tests.unit.test_session_manager import confirm_on_both_sides, session_request
from tests.videos import SHORT_SECONDS, small_video
from wcam.app import create_console_app, phone_page_url
from wcam.config import Settings
from wcam.media.camera_format import CameraFormatControl
from wcam.persistence.database import open_database
from wcam.process_monitor import CpuMonitor
from wcam.services import AgentServices
from wcam.sessions.manager import SessionManager
from wcam.video.filmstrip import FILMSTRIP_WIDTH
from wcam.video.timeline import MAX_CLIP_ID_LENGTH, MAX_CLIPS

PORTRAIT_ROTATION = -90


def video_agent(tmp_path: Path, factory: FakePeerFactory | None = None) -> AgentServices:
    pipeline = opened_pipeline()
    return AgentServices(
        SessionManager(factory or FakePeerFactory()),
        pipeline,
        CpuMonitor(),
        CameraFormatControl(pipeline),
        video_folder=tmp_path / "video",
        database=open_database(tmp_path / "data"),
    )


async def go_live(agent: AgentServices, factory: FakePeerFactory) -> None:
    manager = agent.manager
    await manager.create_session(session_request(manager.open_pairing().token))
    factory.last.events.on_connected()
    confirm_on_both_sides(manager, factory)


async def live_video_agent(tmp_path: Path) -> tuple[AgentServices, FakePeerFactory]:
    factory = FakePeerFactory()
    agent = video_agent(tmp_path, factory)
    await go_live(agent, factory)
    return agent, factory


def client_for(settings: Settings, agent: AgentServices) -> httpx.AsyncClient:
    return console_client(create_console_app(settings, agent, phone_page_url(settings, LAN)))


async def upload(console: httpx.AsyncClient, data: bytes, name: str = "reunião.mp4") -> httpx.Response:
    headers = {"X-File-Name": quote(name), "Content-Type": "application/octet-stream"}
    return await console.post("/api/videos", content=data, headers=headers)


async def uploaded(console: httpx.AsyncClient, path: Path) -> dict[str, Any]:
    data = await asyncio.to_thread(path.read_bytes)
    body: dict[str, Any] = (await upload(console, data, path.name)).json()
    return body


def whole_clip(video: dict[str, Any], clip_id: str = "c1") -> dict[str, Any]:
    return {"id": clip_id, "videoId": video["id"], "inSeconds": 0.0, "outSeconds": video["durationSeconds"]}


def error_code(response: httpx.Response) -> str:
    body: dict[str, Any] = response.json()
    return body["error"]["code"]


async def video_status(console: httpx.AsyncClient) -> dict[str, Any]:
    body: dict[str, Any] = (await console.get("/api/status")).json()
    return body["videoSource"]


def folder_files(folder: Path) -> list[str]:
    return sorted(path.name for path in folder.iterdir()) if folder.is_dir() else []


async def test_upload_without_a_live_phone_is_refused_before_reading(tmp_path: Path, settings: Settings) -> None:
    async with client_for(settings, video_agent(tmp_path)) as console:
        response = await upload(console, small_video(tmp_path).read_bytes())

    assert (response.status_code, error_code(response)) == (409, "no_live_session")
    assert folder_files(tmp_path / "video") == []


async def test_uploaded_video_joins_the_library_with_its_filmstrip(tmp_path: Path, settings: Settings) -> None:
    agent, _ = await live_video_agent(tmp_path)
    async with client_for(settings, agent) as console:
        response = await upload(console, small_video(tmp_path).read_bytes())
        video = response.json()
        filmstrip = await console.get(f"/api/videos/{video['id']}/filmstrip")
        status = await video_status(console)

    assert response.status_code == 201
    assert {key: video[key] for key in ("name", "durationSeconds", "fps", "codec")} == {
        "name": "reunião.mp4",
        "durationSeconds": SHORT_SECONDS,
        "fps": 30.0,
        "codec": "h264",
    }
    assert video["filmstripFrames"] >= 1
    assert status["videos"] == [video]
    assert status["timeline"] == {"clips": [], "durationSeconds": 0.0}
    assert filmstrip.headers["content-type"] == "image/jpeg"
    assert "immutable" in filmstrip.headers["cache-control"]
    assert Image.open(io.BytesIO(filmstrip.content)).width == FILMSTRIP_WIDTH * video["filmstripFrames"]


async def test_filmstrip_of_a_portrait_video_is_upright(tmp_path: Path, settings: Settings) -> None:
    agent, _ = await live_video_agent(tmp_path)
    async with client_for(settings, agent) as console:
        video = await uploaded(console, small_video(tmp_path, rotation=PORTRAIT_ROTATION))
        filmstrip = await console.get(f"/api/videos/{video['id']}/filmstrip")

    image = Image.open(io.BytesIO(filmstrip.content))
    assert (video["width"], video["height"]) == (180, 320)
    assert image.height > FILMSTRIP_WIDTH
    assert image.size == (FILMSTRIP_WIDTH * video["filmstripFrames"], round(FILMSTRIP_WIDTH * 320 / 180))


async def test_file_that_is_not_a_video_is_refused_without_leaving_a_file(tmp_path: Path, settings: Settings) -> None:
    agent, _ = await live_video_agent(tmp_path)
    async with client_for(settings, agent) as console:
        response = await upload(console, b"not a video at all", "notes.txt")

    assert (response.status_code, error_code(response)) == (422, "video_unsupported")
    assert folder_files(tmp_path / "video") == []


async def test_upload_without_a_name_is_invalid(tmp_path: Path, settings: Settings) -> None:
    agent, _ = await live_video_agent(tmp_path)
    async with client_for(settings, agent) as console:
        response = await console.post("/api/videos", content=b"data")

    assert (response.status_code, error_code(response)) == (422, "invalid_request")


async def test_timeline_is_kept_as_sent_with_its_total_duration(tmp_path: Path, settings: Settings) -> None:
    agent, _ = await live_video_agent(tmp_path)
    async with client_for(settings, agent) as console:
        video = await uploaded(console, small_video(tmp_path))
        clips = [
            {"id": "a", "videoId": video["id"], "inSeconds": 0.25, "outSeconds": 1.0},
            {"id": "b", "videoId": video["id"], "inSeconds": 1.0, "outSeconds": 2.0},
        ]
        response = await console.put("/api/timeline", json={"clips": clips})
        status = await video_status(console)

    assert response.status_code == 204
    assert status["timeline"] == {"clips": clips, "durationSeconds": 1.75}


@pytest.mark.parametrize(
    "clip",
    [
        {"inSeconds": 1.0, "outSeconds": 1.4},
        {"inSeconds": 0.0, "outSeconds": SHORT_SECONDS + 0.1},
        {"inSeconds": -0.1, "outSeconds": 1.0},
        {"inSeconds": 1.5, "outSeconds": 1.0},
        {"videoId": "missing"},
        {"id": ""},
        {"id": "x" * (MAX_CLIP_ID_LENGTH + 1)},
        {"extra": True},
    ],
)
async def test_invalid_clip_is_refused(tmp_path: Path, settings: Settings, clip: dict[str, Any]) -> None:
    agent, _ = await live_video_agent(tmp_path)
    async with client_for(settings, agent) as console:
        video = await uploaded(console, small_video(tmp_path))
        response = await console.put("/api/timeline", json={"clips": [whole_clip(video) | clip]})

    assert (response.status_code, error_code(response)) == (422, "invalid_request")


async def test_more_than_fifty_clips_are_refused(tmp_path: Path, settings: Settings) -> None:
    agent, _ = await live_video_agent(tmp_path)
    async with client_for(settings, agent) as console:
        video = await uploaded(console, small_video(tmp_path))
        clips = [whole_clip(video, str(index)) for index in range(MAX_CLIPS + 1)]
        response = await console.put("/api/timeline", json={"clips": clips})

    assert (response.status_code, error_code(response)) == (422, "invalid_request")


async def test_removing_a_video_takes_its_clips_out_of_the_timeline(tmp_path: Path, settings: Settings) -> None:
    agent, _ = await live_video_agent(tmp_path)
    async with client_for(settings, agent) as console:
        first = await uploaded(console, small_video(tmp_path, name="first.mp4"))
        second = await uploaded(console, small_video(tmp_path, name="second.mp4"))
        clips = [whole_clip(first, "a"), whole_clip(second, "b")]
        await console.put("/api/timeline", json={"clips": clips})

        removed = await console.delete(f"/api/videos/{first['id']}")
        again = await console.delete(f"/api/videos/{first['id']}")
        filmstrip = await console.get(f"/api/videos/{first['id']}/filmstrip")
        status = await video_status(console)

    assert removed.status_code == 204
    assert (again.status_code, error_code(again)) == (404, "video_not_found")
    assert (filmstrip.status_code, error_code(filmstrip)) == (404, "video_not_found")
    assert [video["id"] for video in status["videos"]] == [second["id"]]
    assert status["timeline"]["clips"] == [whole_clip(second, "b")]
    assert not any(name.startswith(first["id"]) for name in folder_files(tmp_path / "video"))


async def test_library_and_timeline_survive_a_restart_with_the_video_off(tmp_path: Path, settings: Settings) -> None:
    agent, _ = await live_video_agent(tmp_path)
    async with client_for(settings, agent) as console:
        video = await uploaded(console, small_video(tmp_path))
        await console.put("/api/timeline", json={"clips": [whole_clip(video)]})
        await console.put("/api/video-source", json={"active": True})
        before = await video_status(console)
        await console.put("/api/video-source", json={"active": False})

    async with client_for(settings, video_agent(tmp_path)) as console:
        after = await video_status(console)

    assert before["active"]
    assert after == before | {"active": False, "positionSeconds": None}


async def test_using_the_video_needs_a_live_phone_and_a_clip(tmp_path: Path, settings: Settings) -> None:
    factory = FakePeerFactory()
    agent = video_agent(tmp_path, factory)
    async with client_for(settings, agent) as console:
        without_phone = await console.put("/api/video-source", json={"active": True})
        await go_live(agent, factory)
        without_clip = await console.put("/api/video-source", json={"active": True})

    assert (without_phone.status_code, error_code(without_phone)) == (409, "no_live_session")
    assert (without_clip.status_code, error_code(without_clip)) == (409, "timeline_empty")


async def test_video_plays_with_the_phone_still_live_until_back_to_the_camera(
    tmp_path: Path, settings: Settings
) -> None:
    agent, factory = await live_video_agent(tmp_path)
    async with client_for(settings, agent) as console:
        video = await uploaded(console, small_video(tmp_path))
        await console.put("/api/timeline", json={"clips": [whole_clip(video)]})
        use = await console.put("/api/video-source", json={"active": True})
        try:
            await wait_until(lambda: agent.video.view().position_seconds is not None)
            status = (await console.get("/api/status")).json()
            playing = agent.pipeline.video_active
            jump = await console.put("/api/video-source/position", json={"seconds": 1.0})
            outside = await console.put("/api/video-source/position", json={"seconds": SHORT_SECONDS})
            camera_off = await console.patch("/api/controls", json={"cameraOff": True})
            facing = await console.patch("/api/controls", json={"facing": "user"})
            freeze = await console.patch("/api/controls", json={"frozen": True})
        finally:
            stop = await console.put("/api/video-source", json={"active": False})
        stopped_jump = await console.put("/api/video-source/position", json={"seconds": 1.0})
        stopped = await video_status(console)

    assert use.status_code == 204
    assert status["session"]["state"] == "live"
    assert playing
    assert 0 <= status["videoSource"]["positionSeconds"] < SHORT_SECONDS
    assert jump.status_code == 204
    assert (outside.status_code, error_code(outside)) == (422, "invalid_request")
    assert (camera_off.status_code, error_code(camera_off)) == (409, "video_source_active")
    assert (facing.status_code, error_code(facing)) == (409, "video_source_active")
    assert freeze.status_code == 204
    assert stop.status_code == 204
    assert (stopped_jump.status_code, error_code(stopped_jump)) == (409, "video_source_inactive")
    assert (stopped["active"], stopped["positionSeconds"]) == (False, None)
    sent = factory.last.sent
    assert sent.index({"type": "video_source", "active": True}) < sent.index({"type": "video_source", "active": False})


async def test_video_goes_on_when_the_phone_leaves(tmp_path: Path, settings: Settings) -> None:
    agent, _ = await live_video_agent(tmp_path)
    async with client_for(settings, agent) as console:
        video = await uploaded(console, small_video(tmp_path))
        await console.put("/api/timeline", json={"clips": [whole_clip(video)]})
        await console.put("/api/video-source", json={"active": True})

        disconnect = await console.delete("/api/sessions/current")
        status = (await console.get("/api/status")).json()
        pairing = await console.post("/api/pairing")
        await console.put("/api/video-source", json={"active": False})

    assert disconnect.status_code == 204
    assert status["session"] is None
    assert status["videoSource"]["active"]
    assert pairing.status_code == 201


async def test_back_to_the_camera_from_the_phone_turns_the_video_off(tmp_path: Path, settings: Settings) -> None:
    agent, factory = await live_video_agent(tmp_path)
    async with client_for(settings, agent) as console:
        video = await uploaded(console, small_video(tmp_path))
        await console.put("/api/timeline", json={"clips": [whole_clip(video)]})
        await console.put("/api/video-source", json={"active": True})

        factory.last.events.on_message(json.dumps({"type": "set_video_source", "active": False}))
        await wait_until(lambda: not agent.video.active)

    assert factory.last.sent[-1] == {"type": "video_source", "active": False}


async def test_emptying_the_timeline_turns_the_video_off(tmp_path: Path, settings: Settings) -> None:
    agent, _ = await live_video_agent(tmp_path)
    async with client_for(settings, agent) as console:
        video = await uploaded(console, small_video(tmp_path))
        await console.put("/api/timeline", json={"clips": [whole_clip(video)]})
        await console.put("/api/video-source", json={"active": True})

        emptied = await console.put("/api/timeline", json={"clips": []})
        status = await video_status(console)

    assert emptied.status_code == 204
    assert not status["active"]


async def test_using_the_video_and_editing_the_timeline_record_developer_events(
    tmp_path: Path, settings: Settings
) -> None:
    agent, _ = await live_video_agent(tmp_path)
    events = agent.dev_events.subscribe()
    async with client_for(settings, agent) as console:
        video = await uploaded(console, small_video(tmp_path))
        await console.put("/api/timeline", json={"clips": [whole_clip(video)]})
        await console.put("/api/video-source", json={"active": True})
        await console.put("/api/video-source", json={"active": False})

    kinds = [(event.kind, dict(event.data)) for event in [events.get_nowait() for _ in range(events.qsize())]]
    assert ("timeline", {"clips": 1, "durationSeconds": SHORT_SECONDS}) in kinds
    assert ("video_source", {"active": True}) in kinds
    assert ("video_source", {"active": False}) in kinds

import asyncio
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from tests.conftest import opened_pipeline, services
from tests.fakes import FakePeerFactory
from tests.unit.test_cli import english
from tests.unit.test_dev_console import live_agent
from tests.videos import chunks_of, small_video
from wcam.media.pipeline import FrameSource
from wcam.services import AgentServices
from wcam.sessions.controls import Controls, ControlsChange
from wcam.sessions.manager import SessionManager
from wcam.tray.icons import ICON_SIZE, tray_icon
from wcam.tray.menu import MenuEntry, TrayAction, TraySnapshot, TrayState, menu_entries, tray_snapshot
from wcam.tray.tray import Tray
from wcam.video.source import VideoSourceView
from wcam.video.timeline import Clip, Timeline
from wcam.virtualcam.sink import CameraState

WAIT_SECONDS = 1.0
POLL_SECONDS = 0.01


class FakeTrayIcon:
    def __init__(self) -> None:
        self.on_select: Callable[[TrayAction], None] | None = None
        self.shown: list[tuple[TrayState, str, list[tuple[MenuEntry, str]]]] = []
        self.stopped = False

    def start(self, on_select: Callable[[TrayAction], None]) -> None:
        self.on_select = on_select

    def update(self, state: TrayState, tooltip: str, entries: list[tuple[MenuEntry, str]]) -> None:
        self.shown.append((state, tooltip, entries))

    def stop(self) -> None:
        self.stopped = True


class Calls:
    def __init__(self) -> None:
        self.console_opened = 0
        self.quit = 0

    def open_console(self) -> None:
        self.console_opened += 1

    def quit_agent(self) -> None:
        self.quit += 1


def tray_for(agent: AgentServices, icon: FakeTrayIcon, calls: Calls) -> Tray:
    return Tray(icon, agent, english(), calls.open_console, calls.quit_agent)


def idle_agent() -> AgentServices:
    return services(SessionManager(FakePeerFactory()), opened_pipeline())


def test_without_a_phone_the_tray_waits_and_disables_the_phone_items() -> None:
    agent = idle_agent()

    snapshot = tray_snapshot(agent.manager.status(), FrameSource.PLACEHOLDER, CameraState.ACTIVE)

    entries = {entry.action: entry for entry in menu_entries(snapshot)}
    assert snapshot.state is TrayState.WAITING
    for action in (TrayAction.TOGGLE_FREEZE, TrayAction.TOGGLE_CAMERA, TrayAction.SWITCH_CAMERA, TrayAction.DISCONNECT):
        assert not entries[action].enabled
    assert entries[TrayAction.TOGGLE_MIRROR].enabled
    assert entries[TrayAction.QUIT].enabled


@pytest.mark.parametrize(
    ("controls", "source", "camera_state", "expected"),
    [
        (Controls(), FrameSource.PHONE, CameraState.ACTIVE, (TrayState.LIVE, "state.live")),
        (Controls(frozen=True), FrameSource.HELD, CameraState.ACTIVE, (TrayState.FROZEN, "state.frozen")),
        (
            Controls(camera_off=True),
            FrameSource.CAMERA_OFF,
            CameraState.ACTIVE,
            (TrayState.CAMERA_OFF, "state.camera_off"),
        ),
        (Controls(), FrameSource.FROZEN, CameraState.ACTIVE, (TrayState.PROBLEM, "state.lost")),
        (Controls(), FrameSource.PHONE, CameraState.UNAVAILABLE, (TrayState.PROBLEM, "state.problem")),
    ],
)
async def test_live_tray_state_follows_controls_source_and_camera(
    controls: Controls,
    source: FrameSource,
    camera_state: CameraState,
    expected: tuple[TrayState, str],
) -> None:
    agent = await live_agent(FakePeerFactory())
    status = agent.manager.status()

    snapshot = tray_snapshot(replace(status, controls=controls), source, camera_state)

    assert (snapshot.state, snapshot.state_text_key) == expected


async def test_tray_shows_the_state_and_follows_changes() -> None:
    agent = idle_agent()
    icon, calls = FakeTrayIcon(), Calls()
    tray = tray_for(agent, icon, calls)
    running = asyncio.create_task(tray.run())
    await asyncio.sleep(0)

    await asyncio.wait_for(wait_for(lambda: len(icon.shown) >= 1), WAIT_SECONDS)
    agent.status_changes.close()
    await asyncio.wait_for(running, WAIT_SECONDS)

    state, tooltip, _ = icon.shown[0]
    assert state is TrayState.WAITING
    assert tooltip == english().text("tray.tooltip", state=english().text("state.waiting"))
    assert icon.stopped


async def wait_for(condition: Callable[[], bool]) -> None:
    while True:
        if condition():
            return
        await asyncio.sleep(POLL_SECONDS)


def test_mirror_from_the_tray_works_without_a_phone() -> None:
    agent = idle_agent()
    tray = tray_for(agent, FakeTrayIcon(), Calls())

    tray.select(TrayAction.TOGGLE_MIRROR)

    assert agent.manager.status().controls.mirror


def test_freezing_from_the_tray_without_a_phone_is_ignored() -> None:
    agent = idle_agent()
    tray = tray_for(agent, FakeTrayIcon(), Calls())

    tray.select(TrayAction.TOGGLE_FREEZE)

    assert not agent.manager.status().controls.frozen


async def test_switching_from_the_tray_asks_for_the_other_camera() -> None:
    factory = FakePeerFactory()
    agent = await live_agent(factory)
    tray = tray_for(agent, FakeTrayIcon(), Calls())
    agent.manager.change_controls(ControlsChange(facing="user"))

    tray.select(TrayAction.SWITCH_CAMERA)

    assert agent.manager.status().controls.facing == "environment"


def test_console_items_open_the_console_and_quit_stops_the_agent() -> None:
    calls = Calls()
    tray = tray_for(idle_agent(), FakeTrayIcon(), calls)

    tray.select(TrayAction.OPEN_CONSOLE)
    tray.select(TrayAction.SHOW_QR)
    tray.select(TrayAction.QUIT)

    assert (calls.console_opened, calls.quit) == (2, 1)


async def test_disconnect_from_the_tray_ends_the_phone_connection() -> None:
    agent = await live_agent(FakePeerFactory())
    tray = tray_for(agent, FakeTrayIcon(), Calls())

    tray.select(TrayAction.DISCONNECT)
    await asyncio.sleep(0)

    last_ended = agent.manager.status().last_ended
    assert last_ended is not None
    assert last_ended.reason == "disconnected_by_pc"


@pytest.mark.parametrize("state", list(TrayState))
def test_each_tray_state_has_its_own_icon(state: TrayState) -> None:
    images = {other: tray_icon(other).tobytes() for other in TrayState}

    assert tray_icon(state).size == (ICON_SIZE, ICON_SIZE)
    assert list(images.values()).count(images[state]) == 1


def video_with_a_clip(active: bool = False) -> VideoSourceView:
    return VideoSourceView((), Timeline((Clip("c1", "v1", 0.0, 2.0),)), active=active, position_seconds=None)


def use_video_entry(snapshot: TraySnapshot) -> MenuEntry:
    return {entry.action: entry for entry in menu_entries(snapshot)}[TrayAction.TOGGLE_VIDEO]


async def test_use_video_item_needs_a_live_phone_and_a_clip() -> None:
    idle = idle_agent().manager.status()
    live = (await live_agent(FakePeerFactory())).manager.status()

    without_phone = tray_snapshot(idle, FrameSource.PLACEHOLDER, CameraState.ACTIVE, video_with_a_clip())
    without_clip = tray_snapshot(live, FrameSource.PHONE, CameraState.ACTIVE)
    ready = tray_snapshot(live, FrameSource.PHONE, CameraState.ACTIVE, video_with_a_clip())

    assert not use_video_entry(without_phone).enabled
    assert not use_video_entry(without_clip).enabled
    assert use_video_entry(ready).enabled
    assert use_video_entry(ready).text_key == "tray.use_video"


@pytest.mark.parametrize(
    ("controls", "expected"),
    [(Controls(), (TrayState.VIDEO, "state.video")), (Controls(frozen=True), (TrayState.FROZEN, "state.frozen"))],
)
def test_active_video_shows_its_own_state_and_can_be_frozen_or_left(
    controls: Controls,
    expected: tuple[TrayState, str],
) -> None:
    status = replace(idle_agent().manager.status(), controls=controls)

    snapshot = tray_snapshot(status, FrameSource.VIDEO, CameraState.ACTIVE, video_with_a_clip(active=True))

    entries = {entry.action: entry for entry in menu_entries(snapshot)}
    assert (snapshot.state, snapshot.state_text_key) == expected
    assert entries[TrayAction.TOGGLE_VIDEO].enabled
    assert entries[TrayAction.TOGGLE_VIDEO].checked
    assert entries[TrayAction.TOGGLE_VIDEO].text_key == "controls.back_to_phone"
    assert entries[TrayAction.TOGGLE_FREEZE].enabled
    assert not entries[TrayAction.TOGGLE_CAMERA].enabled
    assert not entries[TrayAction.SWITCH_CAMERA].enabled


async def test_use_video_from_the_tray_turns_the_timeline_on_and_back_to_the_camera(tmp_path: Path) -> None:
    agent = await live_agent(FakePeerFactory())
    video = await agent.video.add(chunks_of(small_video(tmp_path).read_bytes()), "clip.mp4")
    await agent.video.set_timeline([Clip("c1", video.id, 0.0, video.info.duration_seconds)])
    tray = tray_for(agent, FakeTrayIcon(), Calls())

    tray.select(TrayAction.TOGGLE_VIDEO)
    await asyncio.wait_for(wait_for(lambda: agent.video.active), WAIT_SECONDS)
    tray.select(TrayAction.TOGGLE_VIDEO)
    await asyncio.wait_for(wait_for(lambda: not agent.video.active), WAIT_SECONDS)

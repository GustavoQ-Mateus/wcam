import asyncio
from collections.abc import Callable
from dataclasses import replace

import pytest

from tests.conftest import opened_pipeline, services
from tests.fakes import FakePeerFactory
from tests.unit.test_cli import english
from tests.unit.test_dev_console import live_agent
from wcam.media.pipeline import FrameSource
from wcam.services import AgentServices
from wcam.sessions.controls import Controls, ControlsChange
from wcam.sessions.manager import SessionManager
from wcam.tray.icons import ICON_SIZE, tray_icon
from wcam.tray.menu import MenuEntry, TrayAction, TrayState, menu_entries, tray_snapshot
from wcam.tray.tray import Tray
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

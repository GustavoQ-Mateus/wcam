import asyncio
import contextlib
import logging
import sys
from collections.abc import Callable, Coroutine
from typing import Any, Protocol

from wcam.i18n import Messages
from wcam.services import AgentServices
from wcam.sessions.controls import ControlsChange, Facing
from wcam.sessions.errors import NoActiveSessionError, NoLiveSessionError
from wcam.tray.menu import MenuEntry, TrayAction, TraySnapshot, TrayState, menu_entries, tray_snapshot

REFRESH_SECONDS = 1.0
OTHER_FACING: dict[Facing, Facing] = {"user": "environment", "environment": "user"}
IGNORED_TRAY_ACTION = "Ignored a tray action because the phone is not live"
NO_TRAY_OUTSIDE_WINDOWS = "The tray icon is only shown on Windows"
NO_TRAY_WITHOUT_PYSTRAY = "The tray icon is off because pystray could not be loaded"

logger = logging.getLogger(__name__)


class TrayIcon(Protocol):
    def start(self, on_select: Callable[[TrayAction], None]) -> None: ...

    def update(self, state: TrayState, tooltip: str, entries: list[tuple[MenuEntry, str]]) -> None: ...

    def stop(self) -> None: ...


class Tray:
    def __init__(
        self,
        icon: TrayIcon,
        services: AgentServices,
        messages: Messages,
        open_console: Callable[[], object],
        quit_agent: Callable[[], None],
    ) -> None:
        self._icon = icon
        self._services = services
        self._messages = messages
        self._open_console = open_console
        self._quit_agent = quit_agent
        self._shown: TraySnapshot | None = None
        self._actions: set[asyncio.Task[None]] = set()

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        changes = self._services.status_changes
        changed = changes.subscribe()

        def select_on_loop(action: TrayAction) -> None:
            loop.call_soon_threadsafe(self.select, action)

        self._icon.start(select_on_loop)
        try:
            while not changes.closed:
                changed.clear()
                self.refresh()
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(changed.wait(), REFRESH_SECONDS)
        finally:
            changes.unsubscribe(changed)
            await self._stop()

    def refresh(self) -> None:
        services = self._services
        snapshot = tray_snapshot(
            services.manager.status(), services.pipeline.source, services.pipeline.sink.status.state
        )
        if snapshot == self._shown:
            return
        self._shown = snapshot
        state_text = self._messages.text(snapshot.state_text_key)
        tooltip = self._messages.text("tray.tooltip", state=state_text)
        entries = [(entry, self._text(entry)) for entry in menu_entries(snapshot)]
        self._icon.update(snapshot.state, tooltip, entries)

    def select(self, action: TrayAction) -> None:
        if action in (TrayAction.OPEN_CONSOLE, TrayAction.SHOW_QR):
            self._open_console()
        elif action is TrayAction.QUIT:
            self._quit_agent()
        elif action is TrayAction.DISCONNECT:
            self._run(self._disconnect())
        else:
            self._change_controls(action)

    def _change_controls(self, action: TrayAction) -> None:
        change = self._change_for(action)
        if change is None:
            return
        try:
            self._services.manager.change_controls(change)
        except NoLiveSessionError:
            logger.warning(IGNORED_TRAY_ACTION)

    def _change_for(self, action: TrayAction) -> ControlsChange | None:
        controls = self._services.manager.status().controls
        if action is TrayAction.TOGGLE_FREEZE:
            return ControlsChange(frozen=not controls.frozen)
        if action is TrayAction.TOGGLE_CAMERA:
            return ControlsChange(camera_off=not controls.camera_off)
        if action is TrayAction.TOGGLE_MIRROR:
            return ControlsChange(mirror=not controls.mirror)
        if action is TrayAction.SWITCH_CAMERA and controls.facing is not None:
            return ControlsChange(facing=OTHER_FACING[controls.facing])
        return None

    async def _disconnect(self) -> None:
        with contextlib.suppress(NoActiveSessionError):
            await self._services.manager.disconnect()

    def _run(self, work: Coroutine[Any, Any, None]) -> None:
        task = asyncio.get_running_loop().create_task(work)
        self._actions.add(task)
        task.add_done_callback(self._actions.discard)

    async def _stop(self) -> None:
        for task in list(self._actions):
            task.cancel()
        await asyncio.gather(*self._actions, return_exceptions=True)
        self._icon.stop()

    def _text(self, entry: MenuEntry) -> str:
        return "" if entry.action is TrayAction.SEPARATOR else self._messages.text(entry.text_key)


def windows_tray_icon() -> TrayIcon | None:
    if sys.platform != "win32":
        logger.info(NO_TRAY_OUTSIDE_WINDOWS)
        return None
    try:
        from wcam.tray.pystray_icon import PystrayIcon
    except ImportError:
        logger.warning(NO_TRAY_WITHOUT_PYSTRAY)
        return None
    return PystrayIcon()

import threading
from collections.abc import Callable

import pystray

from wcam.tray.icons import tray_icon
from wcam.tray.menu import MenuEntry, TrayAction, TrayState

TRAY_THREAD_NAME = "wcam-tray"
TRAY_NAME = "wcam"
STOP_WAIT_SECONDS = 2.0


class PystrayIcon:
    def __init__(self) -> None:
        self._icon = pystray.Icon(TRAY_NAME, tray_icon(TrayState.WAITING))
        self._thread: threading.Thread | None = None
        self._on_select: Callable[[TrayAction], None] = ignore_action

    def start(self, on_select: Callable[[TrayAction], None]) -> None:
        self._on_select = on_select
        self._thread = threading.Thread(target=self._icon.run, name=TRAY_THREAD_NAME)
        self._thread.start()

    def update(self, state: TrayState, tooltip: str, entries: list[tuple[MenuEntry, str]]) -> None:
        self._icon.icon = tray_icon(state)
        self._icon.title = tooltip
        self._icon.menu = pystray.Menu(*(self._item(entry, text) for entry, text in entries))
        self._icon.update_menu()

    def stop(self) -> None:
        self._icon.stop()
        if self._thread is not None:
            self._thread.join(STOP_WAIT_SECONDS)

    def _item(self, entry: MenuEntry, text: str) -> pystray.MenuItem:
        if entry.action is TrayAction.SEPARATOR:
            return pystray.Menu.SEPARATOR
        action = entry.action
        return pystray.MenuItem(
            text,
            lambda: self._on_select(action),
            enabled=entry.enabled,
            checked=always_checked if entry.checked else None,
        )


def ignore_action(action: TrayAction) -> None:
    return None


def always_checked(item: pystray.MenuItem) -> bool:
    return True

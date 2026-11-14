from dataclasses import dataclass
from enum import StrEnum

from wcam.media.pipeline import FrameSource
from wcam.sessions.controls import Controls
from wcam.sessions.manager import SessionState, Status
from wcam.virtualcam.sink import CameraState

CAMERA_TEXT_KEYS = {"user": "camera.front", "environment": "camera.back"}


class TrayState(StrEnum):
    LIVE = "live"
    FROZEN = "frozen"
    CAMERA_OFF = "camera_off"
    WAITING = "waiting"
    PROBLEM = "problem"


class TrayAction(StrEnum):
    NONE = "none"
    SEPARATOR = "separator"
    TOGGLE_FREEZE = "toggle_freeze"
    TOGGLE_CAMERA = "toggle_camera"
    SWITCH_CAMERA = "switch_camera"
    TOGGLE_MIRROR = "toggle_mirror"
    OPEN_CONSOLE = "open_console"
    SHOW_QR = "show_qr"
    DISCONNECT = "disconnect"
    QUIT = "quit"


@dataclass(frozen=True, slots=True)
class TraySnapshot:
    state: TrayState
    state_text_key: str
    connected: bool
    controls: Controls


@dataclass(frozen=True, slots=True)
class MenuEntry:
    text_key: str
    action: TrayAction
    enabled: bool = True
    checked: bool = False


SEPARATOR = MenuEntry("", TrayAction.SEPARATOR)


def tray_snapshot(status: Status, source: FrameSource, camera_state: CameraState) -> TraySnapshot:
    session = status.session
    controls = status.controls
    live = session is not None and session.state is SessionState.LIVE
    state, text_key = tray_state(status, source, camera_state)
    return TraySnapshot(state, text_key, live, controls)


def tray_state(status: Status, source: FrameSource, camera_state: CameraState) -> tuple[TrayState, str]:
    session = status.session
    if camera_state is not CameraState.ACTIVE:
        return TrayState.PROBLEM, "state.problem"
    if session is None:
        return TrayState.WAITING, "state.waiting"
    if session.state is not SessionState.LIVE:
        return TrayState.WAITING, "state.confirming"
    if status.controls.camera_off:
        return TrayState.CAMERA_OFF, "state.camera_off"
    if status.controls.frozen:
        return TrayState.FROZEN, "state.frozen"
    if source is not FrameSource.PHONE:
        return TrayState.PROBLEM, "state.lost"
    return TrayState.LIVE, "state.live"


def menu_entries(snapshot: TraySnapshot) -> list[MenuEntry]:
    controls = snapshot.controls
    connected = snapshot.connected
    return [
        MenuEntry(snapshot.state_text_key, TrayAction.NONE, enabled=False),
        MenuEntry(camera_text_key(snapshot), TrayAction.NONE, enabled=False),
        SEPARATOR,
        MenuEntry(
            "controls.unfreeze" if controls.frozen else "controls.freeze",
            TrayAction.TOGGLE_FREEZE,
            enabled=connected and not controls.camera_off,
        ),
        MenuEntry(
            "controls.camera_on" if controls.camera_off else "controls.camera_off",
            TrayAction.TOGGLE_CAMERA,
            enabled=connected,
        ),
        MenuEntry("controls.switch_camera", TrayAction.SWITCH_CAMERA, enabled=connected),
        MenuEntry("controls.mirror", TrayAction.TOGGLE_MIRROR, checked=controls.mirror),
        SEPARATOR,
        MenuEntry("tray.open_console", TrayAction.OPEN_CONSOLE),
        MenuEntry("tray.show_qr", TrayAction.SHOW_QR),
        MenuEntry("tray.disconnect", TrayAction.DISCONNECT, enabled=connected),
        SEPARATOR,
        MenuEntry("tray.quit", TrayAction.QUIT),
    ]


def camera_text_key(snapshot: TraySnapshot) -> str:
    facing = snapshot.controls.facing
    if not snapshot.connected or facing is None:
        return "tray.no_phone"
    return CAMERA_TEXT_KEYS[facing]

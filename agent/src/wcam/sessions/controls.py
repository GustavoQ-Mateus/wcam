from dataclasses import dataclass, replace
from typing import Literal

type Facing = Literal["user", "environment"]


@dataclass(frozen=True, slots=True)
class Controls:
    frozen: bool = False
    camera_off: bool = False
    mirror: bool = False
    facing: Facing | None = None


@dataclass(frozen=True, slots=True)
class ControlsChange:
    frozen: bool | None = None
    camera_off: bool | None = None
    mirror: bool | None = None
    facing: Facing | None = None

    def needs_live_session(self, video_source_active: bool = False) -> bool:
        frozen_needs_phone = self.frozen is not None and not video_source_active
        return frozen_needs_phone or self.changes_camera()

    def changes_camera(self) -> bool:
        return self.camera_off is not None or self.facing is not None


def changed_controls(controls: Controls, change: ControlsChange) -> Controls:
    camera_off = controls.camera_off if change.camera_off is None else change.camera_off
    frozen = controls.frozen if change.frozen is None else change.frozen
    if camera_off or (change.camera_off is False and change.frozen is None):
        frozen = False
    return Controls(
        frozen=frozen,
        camera_off=camera_off,
        mirror=controls.mirror if change.mirror is None else change.mirror,
        facing=controls.facing if change.facing is None else change.facing,
    )


def after_session(controls: Controls) -> Controls:
    return replace(controls, frozen=False, camera_off=False)

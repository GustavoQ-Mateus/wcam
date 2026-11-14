import threading
from dataclasses import dataclass
from enum import StrEnum


class Stage(StrEnum):
    DECODE = "decode"
    COLOR = "color"
    DELIVER = "deliver"
    TOTAL = "total"


@dataclass(frozen=True, slots=True)
class StageWindow:
    milliseconds: dict[Stage, list[float]]

    def of(self, stage: Stage) -> list[float]:
        return self.milliseconds.get(stage, [])


class StageTimes:
    def __init__(self) -> None:
        self.enabled = False
        self._lock = threading.Lock()
        self._window: dict[Stage, list[float]] = {}

    def record(self, stage: Stage, milliseconds: float) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._window.setdefault(stage, []).append(milliseconds)

    def record_decode(self, milliseconds: float) -> None:
        self.record(Stage.DECODE, milliseconds)

    def take(self) -> StageWindow:
        with self._lock:
            window, self._window = self._window, {}
        return StageWindow(window)

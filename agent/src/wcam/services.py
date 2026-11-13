from dataclasses import dataclass, field

from wcam.change_feed import ChangeFeed
from wcam.clock import utc_now
from wcam.diagnostics.dev_console import DevConsole
from wcam.diagnostics.dev_events import DevEventLog
from wcam.media.camera_format import CameraFormatControl
from wcam.media.pipeline import FramePipeline
from wcam.media.preview import Preview
from wcam.process_monitor import CpuMonitor
from wcam.sessions.comparisons import ComparisonStore
from wcam.sessions.manager import SessionManager


@dataclass(frozen=True, slots=True)
class AgentServices:
    manager: SessionManager
    pipeline: FramePipeline
    cpu: CpuMonitor
    camera: CameraFormatControl
    comparisons: ComparisonStore | None = None
    status_changes: ChangeFeed = field(default_factory=ChangeFeed)
    preview: Preview = field(init=False)
    dev_events: DevEventLog = field(default_factory=DevEventLog)
    dev_console: DevConsole = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "preview", Preview(self.pipeline))
        object.__setattr__(
            self,
            "dev_console",
            DevConsole(self.manager, self.pipeline, lambda: self.cpu.percent, utc_now),
        )
        self.manager.on_change(self.status_changes.publish)
        self.camera.on_change(self.status_changes.publish)
        self.pipeline.on_source_change(self.status_changes.publish)
        self.manager.on_event(self.dev_events.record)
        self.pipeline.on_source_change(self._record_virtual_camera)
        self.camera.on_change(self._record_virtual_camera)
        self.preview.on_change(self._record_preview)
        self.dev_events.on_subscribers_change(self.dev_console.collect)

    def _record_virtual_camera(self) -> None:
        state = self.pipeline.sink.status.state
        data = {"state": state, "source": self.pipeline.source, "format": self.camera.camera_format}
        self.dev_events.record("virtual_camera", data)

    def _record_preview(self) -> None:
        self.dev_events.record("preview", {"open": self.preview.is_open})

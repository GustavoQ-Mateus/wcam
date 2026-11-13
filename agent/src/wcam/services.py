from dataclasses import dataclass, field

from wcam.change_feed import ChangeFeed
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

    def __post_init__(self) -> None:
        object.__setattr__(self, "preview", Preview(self.pipeline))
        self.manager.on_change(self.status_changes.publish)
        self.camera.on_change(self.status_changes.publish)
        self.pipeline.on_source_change(self.status_changes.publish)

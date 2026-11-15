import secrets
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

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
from wcam.video.source import VideoSource
from wcam.video.store import VideoStore

TEMPORARY_VIDEO_PREFIX = "wcam-video-"
TEMPORARY_ID_BYTES = 8


def temporary_video_store() -> VideoStore:
    return VideoStore(Path(tempfile.gettempdir()) / f"{TEMPORARY_VIDEO_PREFIX}{secrets.token_hex(TEMPORARY_ID_BYTES)}")


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
    video_store: VideoStore = field(default_factory=temporary_video_store)
    video: VideoSource = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "preview", Preview(self.pipeline))
        object.__setattr__(self, "video", VideoSource(self.video_store, self.pipeline, self.manager))
        object.__setattr__(
            self,
            "dev_console",
            DevConsole(self.manager, self.pipeline, lambda: self.cpu.percent, utc_now),
        )
        self.manager.on_change(self.status_changes.publish)
        self.camera.on_change(self.status_changes.publish)
        self.video.on_change(self.status_changes.publish)
        self.video.on_event(self.dev_events.record)
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

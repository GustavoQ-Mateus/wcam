import secrets
import sqlite3
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from wcam.change_feed import ChangeFeed
from wcam.clock import utc_now
from wcam.decoding.status import DecoderChange, DecoderStatus, DecodingSource
from wcam.diagnostics.dev_console import DevConsole
from wcam.diagnostics.dev_events import DevEventLog
from wcam.media.camera_format import CameraFormatControl
from wcam.media.pipeline import FramePipeline
from wcam.media.preview import Preview
from wcam.persistence.database import open_database
from wcam.process_monitor import CpuMonitor
from wcam.sessions.comparisons import ComparisonStore
from wcam.sessions.manager import SessionManager
from wcam.video.library import VideoLibrary
from wcam.video.source import VideoSource
from wcam.video.timeline import TimelineStore

TEMPORARY_VIDEO_PREFIX = "wcam-video-"
TEMPORARY_ID_BYTES = 8


def temporary_video_folder() -> Path:
    return Path(tempfile.gettempdir()) / f"{TEMPORARY_VIDEO_PREFIX}{secrets.token_hex(TEMPORARY_ID_BYTES)}"


def memory_database() -> sqlite3.Connection:
    return open_database(None)


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
    video_folder: Path = field(default_factory=temporary_video_folder)
    database: sqlite3.Connection = field(default_factory=memory_database)
    video: VideoSource = field(init=False)
    phone_decoder: DecoderStatus = field(default_factory=lambda: DecoderStatus(DecodingSource.PHONE))

    def __post_init__(self) -> None:
        object.__setattr__(self, "preview", Preview(self.pipeline))
        library = VideoLibrary(self.video_folder, self.database)
        library.load()
        video = VideoSource(library, TimelineStore(self.database), self.pipeline, self.manager)
        object.__setattr__(self, "video", video)
        self.manager.on_back_to_camera(video.deactivate)
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
        self.phone_decoder.on_change(self._record_decoder)
        self.phone_decoder.on_clear(self.status_changes.publish)

    def _record_virtual_camera(self) -> None:
        state = self.pipeline.sink.status.state
        data = {"state": state, "source": self.pipeline.source, "format": self.camera.camera_format}
        self.dev_events.record("virtual_camera", data)

    def _record_decoder(self, change: DecoderChange) -> None:
        data = {"source": change.source, "decoder": change.decoder, "reason": change.reason}
        self.dev_events.record("decoder", data)
        self.status_changes.publish()

    def _record_preview(self) -> None:
        self.dev_events.record("preview", {"open": self.preview.is_open})

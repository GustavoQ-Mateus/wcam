from dataclasses import dataclass

from wcam.media.camera_format import CameraFormatControl
from wcam.media.pipeline import FramePipeline
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

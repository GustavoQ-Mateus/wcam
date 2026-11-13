import statistics
import time
from collections.abc import Callable
from datetime import datetime

from wcam.diagnostics.stage_times import Stage, StageWindow
from wcam.media.pipeline import FramePipeline
from wcam.sessions.manager import SessionManager, SessionState, SessionView, Status

MILLISECONDS_PER_SECOND = 1000
BITS_PER_KILOBIT = 1000
P95 = 0.95
MINIMUM_WINDOW_SECONDS = 0.001

type Json = dict[str, object]


def iso_milliseconds(moment: datetime) -> str:
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def iso_seconds(moment: datetime) -> str:
    return moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def summary(values: list[float]) -> Json | None:
    if not values:
        return None
    ordered = sorted(values)
    p95 = ordered[min(len(ordered) - 1, int(len(ordered) * P95))]
    return {"median": round(statistics.median(ordered), 2), "p95": round(p95, 2)}


class DevConsole:
    def __init__(
        self,
        manager: SessionManager,
        pipeline: FramePipeline,
        cpu_percent: Callable[[], float],
        clock: Callable[[], datetime],
    ) -> None:
        self._manager = manager
        self._pipeline = pipeline
        self._cpu_percent = cpu_percent
        self._clock = clock
        self._previous_at = time.monotonic()
        self._previous_delivered = 0
        self._previous_lost: int | None = None

    def collect(self, subscribers: int) -> None:
        collecting = subscribers > 0
        self._pipeline.stage_times.enabled = collecting
        self._manager.want_phone_stats(collecting)

    async def metrics(self) -> Json:
        status = self._manager.status()
        session = status.session
        window = self._pipeline.stage_times.take()
        live = session is not None and session.state is SessionState.LIVE
        now = time.monotonic()
        elapsed = max(now - self._previous_at, MINIMUM_WINDOW_SECONDS)
        delivered = self._pipeline.frames_delivered
        delivered_fps = max(delivered - self._previous_delivered, 0) / elapsed
        self._previous_at, self._previous_delivered = now, delivered
        received = await self._received(session) if live else None
        output = self._pipeline.output
        camera_format = status.video_format.camera
        return {
            "at": iso_milliseconds(self._clock()),
            "session": None if session is None else self._session(session, status),
            "received": received,
            "delivered": self._delivered(delivered_fps) if live else None,
            "stages": stages(window) if live else None,
            "frameTimesMs": [round(value, 2) for value in window.of(Stage.TOTAL)] if live else None,
            "budgetMs": round(MILLISECONDS_PER_SECOND / output.fps, 1),
            "ceilingKbps": camera_format.size.max_bitrate_bps // BITS_PER_KILOBIT,
            "virtualCamera": {
                "format": camera_format,
                "pendingFormat": status.video_format.selected if status.video_format.pending else None,
                "streamingApps": output.streaming_apps,
                "source": self._pipeline.source,
            },
            "process": {"cpuPercent": self._cpu_percent()},
            "phone": self._manager.phone_stats,
        }

    def _session(self, session: SessionView, status: Status) -> Json:
        return {
            "state": session.state,
            "liveSince": None if session.live_since is None else iso_seconds(session.live_since),
            "deviceName": session.device_name,
            "facing": status.controls.facing,
            "format": status.video_format.camera,
            "codec": None if session.video is None else session.video.codec,
        }

    async def _received(self, session: SessionView | None) -> Json | None:
        video = None if session is None else session.video
        link = await self._manager.receive_stats()
        lost = None if link is None else link.packets_lost
        window_lost = 0 if lost is None or self._previous_lost is None else max(lost - self._previous_lost, 0)
        self._previous_lost = lost
        return {
            "fps": None if video is None else video.fps,
            "bitrateKbps": None if video is None else video.bitrate_kbps,
            "packetsLost": window_lost,
            "jitterMs": None if link is None else round(link.jitter_ms, 1),
        }

    def _delivered(self, fps: float) -> Json:
        return {
            "fps": round(fps, 1),
            "frames": self._pipeline.frames_delivered,
            "dropped": self._pipeline.frames_dropped,
        }


def stages(window: StageWindow) -> Json:
    return {stage.value: summary(window.of(stage)) for stage in Stage}

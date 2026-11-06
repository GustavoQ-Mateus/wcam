import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from logging.handlers import RotatingFileHandler
from pathlib import Path

from wcam.clock import Clock, utc_now

EPISODE_SECONDS = 0.5
MILLISECONDS_PER_SECOND = 1000
EPISODE_LOGGER = "wcam.episodes"
LOG_FOLDER = "logs"
LOG_FILE = "episodes.log"
LOG_MAX_BYTES = 1024 * 1024
LOG_BACKUPS = 1


class EpisodeCause(StrEnum):
    SILENCE = "silence"
    STALLED = "stalled"
    PORTRAIT = "portrait"


class EpisodeAction(StrEnum):
    FROZEN = "frozen"
    BLACK = "black"


@dataclass(frozen=True, slots=True)
class LinkSample:
    at: float
    frame_age: float
    portrait: bool
    black: bool
    rtp_bytes: int
    keyframe_requests: int
    stalls: int


@dataclass(frozen=True, slots=True)
class Episode:
    started_at: datetime
    ended_at: datetime
    cause: EpisodeCause
    action: EpisodeAction
    rtp_bytes: int
    pli_sent: int


@dataclass(slots=True)
class OpenEpisode:
    started: float
    baseline: LinkSample
    portrait: bool = False
    black: bool = False


class EpisodeTracker:
    def __init__(self, write: Callable[[Episode], None], wall_clock: Clock = utc_now) -> None:
        self._write = write
        self._wall_clock = wall_clock
        self._calm: LinkSample | None = None
        self._open: OpenEpisode | None = None

    def observe(self, sample: LinkSample) -> None:
        episode = self._open
        if episode is None:
            self._watch_for_start(sample)
            return
        episode.portrait |= sample.portrait
        episode.black |= sample.black
        if sample.frame_age <= EPISODE_SECONDS:
            self._close(episode, sample, sample.at - sample.frame_age)

    def finish(self, sample: LinkSample) -> None:
        if self._open is not None:
            self._close(self._open, sample, sample.at)

    def _watch_for_start(self, sample: LinkSample) -> None:
        if sample.frame_age <= EPISODE_SECONDS:
            self._calm = sample
            return
        self._open = OpenEpisode(sample.at - sample.frame_age, self._calm or sample, sample.portrait, sample.black)

    def _close(self, episode: OpenEpisode, sample: LinkSample, ended: float) -> None:
        self._open = None
        self._calm = sample
        now = self._wall_clock()
        self._write(
            Episode(
                started_at=now - timedelta(seconds=sample.at - episode.started),
                ended_at=now - timedelta(seconds=sample.at - ended),
                cause=episode_cause(episode, sample),
                action=EpisodeAction.BLACK if episode.black else EpisodeAction.FROZEN,
                rtp_bytes=sample.rtp_bytes - episode.baseline.rtp_bytes,
                pli_sent=sample.keyframe_requests - episode.baseline.keyframe_requests,
            )
        )


def episode_cause(episode: OpenEpisode, sample: LinkSample) -> EpisodeCause:
    if episode.portrait:
        return EpisodeCause.PORTRAIT
    if sample.stalls > episode.baseline.stalls:
        return EpisodeCause.STALLED
    return EpisodeCause.SILENCE


def episode_line(episode: Episode) -> str:
    duration = episode.ended_at - episode.started_at
    return json.dumps(
        {
            "startedAt": iso_milliseconds(episode.started_at),
            "endedAt": iso_milliseconds(episode.ended_at),
            "durationMs": round(duration.total_seconds() * MILLISECONDS_PER_SECOND),
            "cause": episode.cause,
            "action": episode.action,
            "rtpBytes": episode.rtp_bytes,
            "pliSent": episode.pli_sent,
        }
    )


def iso_milliseconds(moment: datetime) -> str:
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def write_episode(episode: Episode) -> None:
    logging.getLogger(EPISODE_LOGGER).info(episode_line(episode))


def open_episode_log(data_dir: Path) -> RotatingFileHandler:
    folder = data_dir / LOG_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(folder / LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUPS, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger(EPISODE_LOGGER)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.addHandler(handler)
    return handler

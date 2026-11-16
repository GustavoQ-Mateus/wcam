import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from wcam.persistence.database import transaction
from wcam.video.errors import InvalidTimelineError

MAX_CLIPS = 50
MIN_CLIP_SECONDS = 0.5
MAX_CLIP_ID_LENGTH = 64
TIME_TOLERANCE_SECONDS = 1e-6


@dataclass(frozen=True, slots=True)
class Clip:
    id: str
    video_id: str
    in_seconds: float
    out_seconds: float

    @property
    def duration_seconds(self) -> float:
        return self.out_seconds - self.in_seconds


@dataclass(frozen=True, slots=True)
class Timeline:
    clips: tuple[Clip, ...] = ()

    @property
    def duration_seconds(self) -> float:
        return sum(clip.duration_seconds for clip in self.clips)

    def start_of(self, index: int) -> float:
        return sum(clip.duration_seconds for clip in self.clips[:index])

    def locate(self, seconds: float) -> tuple[int, float]:
        start = 0.0
        for index, clip in enumerate(self.clips):
            if seconds < start + clip.duration_seconds:
                return index, max(0.0, seconds - start)
            start += clip.duration_seconds
        return 0, 0.0

    def without_video(self, video_id: str) -> "Timeline":
        return Timeline(tuple(clip for clip in self.clips if clip.video_id != video_id))


def validated_timeline(clips: Sequence[Clip], durations: Mapping[str, float]) -> Timeline:
    if len(clips) > MAX_CLIPS:
        raise InvalidTimelineError
    for clip in clips:
        if not valid_clip(clip, durations):
            raise InvalidTimelineError
    return Timeline(tuple(clips))


def valid_clip(clip: Clip, durations: Mapping[str, float]) -> bool:
    duration = durations.get(clip.video_id)
    return (
        duration is not None
        and 0 < len(clip.id) <= MAX_CLIP_ID_LENGTH
        and 0 <= clip.in_seconds < clip.out_seconds <= duration + TIME_TOLERANCE_SECONDS
        and clip.duration_seconds >= MIN_CLIP_SECONDS - TIME_TOLERANCE_SECONDS
    )


class TimelineStore:
    def __init__(self, database: sqlite3.Connection) -> None:
        self._database = database

    def load(self) -> Timeline:
        rows = self._database.execute(
            """
            select
                id,
                video_id,
                in_seconds,
                out_seconds
            from clips
            order by position
            """
        ).fetchall()
        return Timeline(tuple(Clip(*row) for row in rows))

    def save(self, timeline: Timeline) -> None:
        rows = [
            (position, clip.id, clip.video_id, clip.in_seconds, clip.out_seconds)
            for position, clip in enumerate(timeline.clips)
        ]
        with transaction(self._database) as database:
            database.execute("delete from clips")
            database.executemany(
                "insert into clips (position, id, video_id, in_seconds, out_seconds) values (?, ?, ?, ?, ?)",
                rows,
            )

import json
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.fakes import START
from wcam.media.episodes import (
    EPISODE_LOGGER,
    Episode,
    EpisodeAction,
    EpisodeCause,
    EpisodeTracker,
    LinkSample,
    episode_line,
    open_episode_log,
    write_episode,
)

TICK_SECONDS = 0.1
LINE_FIELDS = {"startedAt", "endedAt", "durationMs", "cause", "action", "rtpBytes", "pliSent"}


class Recorder:
    def __init__(self) -> None:
        self.episodes: list[Episode] = []

    def __call__(self, episode: Episode) -> None:
        self.episodes.append(episode)


def sample(
    at: float,
    frame_age: float,
    *,
    rtp_bytes: int = 0,
    keyframe_requests: int = 0,
    stalls: int = 0,
    black: bool = False,
) -> LinkSample:
    return LinkSample(at, frame_age, black, rtp_bytes, keyframe_requests, stalls)


def tracker() -> tuple[EpisodeTracker, Recorder]:
    recorder = Recorder()
    return EpisodeTracker(recorder, lambda: START), recorder


def gap(
    episodes: EpisodeTracker,
    seconds: float,
    *,
    rtp_bytes: int = 0,
    keyframe_requests: int = 0,
    stalls: int = 0,
) -> None:
    episodes.observe(sample(0.0, 0.0))
    ticks = round(seconds / TICK_SECONDS)
    for tick in range(1, ticks + 1):
        episodes.observe(sample(tick * TICK_SECONDS, tick * TICK_SECONDS))
    end = (ticks + 1) * TICK_SECONDS
    episodes.observe(sample(end, 0.0, rtp_bytes=rtp_bytes, keyframe_requests=keyframe_requests, stalls=stalls))


@pytest.fixture
def episode_log(tmp_path: Path) -> Iterator[Path]:
    handler = open_episode_log(tmp_path)
    yield Path(handler.baseFilename)
    logging.getLogger(EPISODE_LOGGER).removeHandler(handler)
    handler.close()


def test_short_gap_is_not_an_episode() -> None:
    episodes, recorder = tracker()

    gap(episodes, 0.4)

    assert recorder.episodes == []


def test_silence_longer_than_half_a_second_is_one_frozen_episode() -> None:
    episodes, recorder = tracker()

    gap(episodes, 1.2, rtp_bytes=0)

    assert len(recorder.episodes) == 1
    episode = recorder.episodes[0]
    assert (episode.cause, episode.action) == (EpisodeCause.SILENCE, EpisodeAction.FROZEN)
    assert (episode.ended_at - episode.started_at).total_seconds() == pytest.approx(1.3)


def test_stall_during_the_gap_is_recorded_with_bytes_and_keyframe_requests() -> None:
    episodes, recorder = tracker()

    gap(episodes, 0.8, rtp_bytes=50_000, keyframe_requests=1, stalls=1)

    episode = recorder.episodes[0]
    assert (episode.cause, episode.rtp_bytes, episode.pli_sent) == (EpisodeCause.STALLED, 50_000, 1)


def test_episode_causes_are_only_silence_and_stalled() -> None:
    assert [str(cause) for cause in EpisodeCause] == ["silence", "stalled"]


def test_gap_that_reaches_black_is_recorded_as_black() -> None:
    episodes, recorder = tracker()
    episodes.observe(sample(0.0, 0.0))

    episodes.observe(sample(1.0, 1.0))
    episodes.observe(sample(3.5, 3.5, black=True))
    episodes.observe(sample(3.6, 0.0))

    assert recorder.episodes[0].action is EpisodeAction.BLACK


def test_open_episode_is_closed_when_the_session_ends() -> None:
    episodes, recorder = tracker()
    episodes.observe(sample(0.0, 0.0))
    episodes.observe(sample(0.9, 0.9))

    episodes.finish(sample(1.0, 1.0))

    assert len(recorder.episodes) == 1
    assert recorder.episodes[0].ended_at == START


def test_episode_line_has_the_contract_fields_in_utc() -> None:
    episodes, recorder = tracker()
    gap(episodes, 0.9)

    line = json.loads(episode_line(recorder.episodes[0]))

    assert set(line) == LINE_FIELDS
    assert line["startedAt"].endswith("Z")
    assert line["endedAt"] == "2026-11-01T18:00:00.000Z"
    assert line["durationMs"] == 1000


def test_episodes_are_written_one_json_line_each(episode_log: Path) -> None:
    episodes = EpisodeTracker(write_episode, lambda: START)
    gap(episodes, 0.9)
    gap(episodes, 0.6)

    lines = episode_log.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 2
    assert all(set(json.loads(line)) == LINE_FIELDS for line in lines)

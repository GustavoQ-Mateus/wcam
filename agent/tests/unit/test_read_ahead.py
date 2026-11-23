import numpy as np

from wcam.video.playback import MAX_FRAMES_BEHIND, ReadAhead, TimelineFrame
from wcam.video.timeline import Timeline

CAPACITY = 4
PERIOD = 1 / 30


def started(capacity: int = CAPACITY) -> tuple[ReadAhead, int]:
    read_ahead = ReadAhead(capacity)
    return read_ahead, read_ahead.restart(Timeline(), {}, 0.0).generation


def frame(generation: int, index: int) -> TimelineFrame:
    return TimelineFrame(generation, index * PERIOD, np.zeros((3, 2), dtype=np.uint8), 0.0, 0.0, 0.0)


def test_late_tick_shows_the_older_due_frame_instead_of_skipping_it() -> None:
    read_ahead, generation = started()
    for index in range(3):
        read_ahead.put(frame(generation, index))

    first = read_ahead.take_due(PERIOD)
    second = read_ahead.take_due(2 * PERIOD)

    assert first is not None
    assert second is not None
    assert (first.play_seconds, second.play_seconds) == (0.0, PERIOD)


def test_more_frames_behind_than_allowed_skip_to_the_newest_due() -> None:
    read_ahead, generation = started()
    behind = MAX_FRAMES_BEHIND + 1
    for index in range(behind):
        read_ahead.put(frame(generation, index))

    shown = read_ahead.take_due((behind - 1) * PERIOD)

    assert shown is not None
    assert shown.play_seconds == (behind - 1) * PERIOD
    assert read_ahead.take_due(behind * PERIOD) is None


def test_restart_drops_the_frames_read_for_the_previous_point() -> None:
    read_ahead, generation = started()
    read_ahead.put(frame(generation, 0))

    read_ahead.restart(Timeline(), {}, 1.0)
    read_ahead.put(frame(generation, 1))

    assert read_ahead.take_first() is None

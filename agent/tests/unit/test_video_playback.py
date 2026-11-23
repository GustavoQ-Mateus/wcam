import itertools
from pathlib import Path

import numpy as np
import pytest

from tests.videos import (
    CAMERA_FPS,
    SMALL_HEIGHT,
    FakeTime,
    FakeVideoOutput,
    played,
    played_timeline,
    small_video,
    video_duration,
)
from wcam.decoding.source import software_decoding
from wcam.decoding.status import DecodingSource
from wcam.media.placeholder import BLACK_LUMA
from wcam.video.playback import ClipDecoder, VideoPlayback, following_tick
from wcam.video.timeline import Clip, Timeline

RUN_SECONDS = 4.0
POSITION_TOLERANCE = 1e-3
CAMERA_PERIOD = 1 / CAMERA_FPS
SLOW_FPS = 15
NOT_BLACK_LUMA = BLACK_LUMA + 40
FIRST_CLIP = Clip("a", "first", 0.5, 1.5)
SECOND_CLIP = Clip("b", "second", 0.2, 1.0)

type Setup = tuple[FakeTime, FakeVideoOutput, VideoPlayback]


def steps(positions: list[float]) -> list[float]:
    return [after - before for before, after in itertools.pairwise(positions) if after >= before]


def two_clips(tmp_path: Path) -> tuple[Timeline, dict[str, Path]]:
    first = small_video(tmp_path, name="first.mp4")
    second = small_video(tmp_path, fps=SLOW_FPS, name="second.mp4")
    return Timeline((FIRST_CLIP, SECOND_CLIP)), {"first": first, "second": second}


def first_jump(output: FakeVideoOutput) -> int:
    return next(index for index, (_, _, replace_held) in enumerate(output.shown) if replace_held and index > 0)


def gaps_between_frames(output: FakeVideoOutput) -> list[float]:
    return np.diff(np.array(output.shown_at)).tolist()


@pytest.mark.parametrize("video_fps", [30, 60])
async def test_camera_gets_a_new_frame_every_tick_from_a_video_at_least_as_fast(tmp_path: Path, video_fps: int) -> None:
    output = await played(small_video(tmp_path, fps=video_fps), RUN_SECONDS)

    assert len(output.shown) >= RUN_SECONDS * CAMERA_FPS - 1
    assert all(gap == pytest.approx(CAMERA_PERIOD, abs=POSITION_TOLERANCE) for gap in gaps_between_frames(output))


async def test_slower_video_gets_each_frame_once_for_the_camera_to_repeat(tmp_path: Path) -> None:
    output = await played(small_video(tmp_path, fps=SLOW_FPS), RUN_SECONDS)

    assert all(gap == pytest.approx(1 / SLOW_FPS, abs=POSITION_TOLERANCE) for gap in gaps_between_frames(output))
    assert all(step == pytest.approx(1 / SLOW_FPS, abs=POSITION_TOLERANCE) for step in steps(output.positions))


async def test_higher_fps_video_skips_frames_instead_of_slowing_down(tmp_path: Path) -> None:
    output = await played(small_video(tmp_path, fps=60), RUN_SECONDS)

    assert all(step == pytest.approx(CAMERA_PERIOD, abs=POSITION_TOLERANCE) for step in steps(output.positions))


async def test_video_loops_to_the_start_without_a_black_frame(tmp_path: Path) -> None:
    output = await played(small_video(tmp_path), RUN_SECONDS)

    positions = output.positions
    wrap = next(index for index in range(1, len(positions)) if positions[index] < positions[index - 1])
    assert positions[wrap] == pytest.approx(0.0, abs=POSITION_TOLERANCE)
    assert all(image[:SMALL_HEIGHT].mean() > NOT_BLACK_LUMA for _, image, _ in output.shown)


async def test_each_clip_starts_at_its_in_point_and_stops_before_its_out_point(tmp_path: Path) -> None:
    output = await played_timeline(*two_clips(tmp_path), 2.0)

    positions = output.positions
    second_start = FIRST_CLIP.duration_seconds
    assert positions[0] == pytest.approx(0.0, abs=POSITION_TOLERANCE)
    assert any(position == pytest.approx(second_start, abs=POSITION_TOLERANCE) for position in positions)
    assert max(positions) < second_start + SECOND_CLIP.duration_seconds


async def test_clip_change_and_loop_repeat_at_most_one_frame(tmp_path: Path) -> None:
    output = await played_timeline(*two_clips(tmp_path), 4.0)

    positions = np.array(output.positions)
    gaps = np.diff(np.array(output.shown_at))
    inside_first_clip = gaps[positions[1:] < FIRST_CLIP.duration_seconds]
    assert inside_first_clip.max() <= 2 * CAMERA_PERIOD + POSITION_TOLERANCE
    assert gaps.max() <= 2 / SLOW_FPS + POSITION_TOLERANCE


async def test_jump_shows_the_requested_point_next(tmp_path: Path) -> None:
    def jump_later(clock: FakeTime, output: FakeVideoOutput, playback: VideoPlayback) -> None:
        clock.at(0.5, lambda: playback.seek(1.5))

    output = await played(small_video(tmp_path), 1.0, jump_later)

    jumped = first_jump(output)
    assert output.positions[jumped] == pytest.approx(1.5, abs=POSITION_TOLERANCE)
    assert output.positions[jumped + 1] == pytest.approx(1.5 + CAMERA_PERIOD, abs=POSITION_TOLERANCE)


async def test_jump_into_the_second_clip_lands_on_its_frame(tmp_path: Path) -> None:
    def jump_later(clock: FakeTime, output: FakeVideoOutput, playback: VideoPlayback) -> None:
        clock.at(0.3, lambda: playback.seek(1.4))

    output = await played_timeline(*two_clips(tmp_path), 0.8, jump_later)

    assert output.positions[first_jump(output)] == pytest.approx(1.4, abs=1 / SLOW_FPS)


async def test_position_stops_while_frozen_and_goes_on_from_there(tmp_path: Path) -> None:
    def freeze_for_a_second(clock: FakeTime, output: FakeVideoOutput, playback: VideoPlayback) -> None:
        clock.at(0.5, lambda: setattr(output, "frozen", True))
        clock.at(1.5, lambda: setattr(output, "frozen", False))

    output = await played(small_video(tmp_path), 1.9, freeze_for_a_second)

    times = np.array(output.shown_at)
    assert not ((times > 0.5 + POSITION_TOLERANCE) & (times < 1.5 - POSITION_TOLERANCE)).any()
    resumed = int(np.argmax(times >= 1.5 - POSITION_TOLERANCE))
    assert output.positions[resumed] - output.positions[resumed - 1] < 2 * CAMERA_PERIOD


async def test_jump_while_frozen_shows_the_new_point_and_stays_frozen(tmp_path: Path) -> None:
    def freeze_then_jump(clock: FakeTime, output: FakeVideoOutput, playback: VideoPlayback) -> None:
        clock.at(0.5, lambda: setattr(output, "frozen", True))
        clock.at(0.7, lambda: playback.seek(1.2))

    output = await played(small_video(tmp_path), 1.5, freeze_then_jump)

    after_freeze = [shown for shown, moment in zip(output.shown, output.shown_at, strict=True) if moment > 0.5]
    assert len(after_freeze) == 1
    position, _, replace_held = after_freeze[0]
    assert replace_held
    assert position == pytest.approx(1.2, abs=POSITION_TOLERANCE)


async def test_timeline_change_goes_on_from_the_same_second(tmp_path: Path) -> None:
    timeline, paths = two_clips(tmp_path)
    reordered = Timeline((SECOND_CLIP, FIRST_CLIP))

    def edit_later(clock: FakeTime, output: FakeVideoOutput, playback: VideoPlayback) -> None:
        clock.at(0.6, lambda: playback.change_timeline(reordered, paths))

    output = await played_timeline(timeline, paths, 1.0, edit_later)

    changed = first_jump(output)
    assert output.positions[changed] == pytest.approx(output.positions[changed - 1], abs=2 / SLOW_FPS)


def test_late_tick_is_made_up_by_a_shorter_wait() -> None:
    assert following_tick(1.0, CAMERA_PERIOD, 1.0 + CAMERA_PERIOD + 0.01) == pytest.approx(1.0 + CAMERA_PERIOD)


def test_tick_more_than_a_period_behind_starts_again_from_now() -> None:
    now = 1.0 + 3 * CAMERA_PERIOD

    assert following_tick(1.0, CAMERA_PERIOD, now) == now


def test_jump_past_the_last_keyframe_reports_the_clip_as_finished(tmp_path: Path) -> None:
    path = small_video(tmp_path)
    duration = video_duration(path)
    decoder = ClipDecoder(path, Clip("c", "v", 0.0, duration), software_decoding(DecodingSource.VIDEO))
    decoder.start_at(0.0)

    jumped = decoder.jump_to_keyframe_after(duration - CAMERA_PERIOD)

    decoder.close()
    assert not jumped

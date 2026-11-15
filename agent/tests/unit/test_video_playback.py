import itertools
from pathlib import Path

import numpy as np
import pytest

from tests.videos import CAMERA_FPS, SMALL_HEIGHT, FakeTime, FakeVideoOutput, played, small_video
from wcam.media.placeholder import BLACK_LUMA
from wcam.video.playback import VideoPlayback

RUN_SECONDS = 4.0
POSITION_TOLERANCE = 1e-3
CAMERA_PERIOD = 1 / CAMERA_FPS
NOT_BLACK_LUMA = BLACK_LUMA + 40


def steps(positions: list[float]) -> list[float]:
    return [after - before for before, after in itertools.pairwise(positions) if after >= before]


@pytest.mark.parametrize("video_fps", [15, 30, 60])
async def test_camera_gets_its_own_fps_whatever_the_video_fps(tmp_path: Path, video_fps: int) -> None:
    output = await played(small_video(tmp_path, fps=video_fps), RUN_SECONDS)

    assert len(output.shown) == RUN_SECONDS * CAMERA_FPS


async def test_lower_fps_video_repeats_each_frame(tmp_path: Path) -> None:
    output = await played(small_video(tmp_path, fps=15), RUN_SECONDS)

    positions = output.positions
    assert positions[0::2] == positions[1::2]


async def test_higher_fps_video_skips_frames_instead_of_slowing_down(tmp_path: Path) -> None:
    output = await played(small_video(tmp_path, fps=60), RUN_SECONDS)

    assert all(step == pytest.approx(CAMERA_PERIOD, abs=POSITION_TOLERANCE) for step in steps(output.positions))


async def test_video_loops_to_the_start_without_a_black_frame(tmp_path: Path) -> None:
    output = await played(small_video(tmp_path), RUN_SECONDS)

    positions = output.positions
    wrap = next(index for index in range(1, len(positions)) if positions[index] < positions[index - 1])
    assert positions[wrap] == pytest.approx(0.0, abs=POSITION_TOLERANCE)
    assert all(image[:SMALL_HEIGHT].mean() > NOT_BLACK_LUMA for _, image, _ in output.shown)


async def test_jump_shows_the_requested_point_next(tmp_path: Path) -> None:
    def jump_later(clock: FakeTime, output: FakeVideoOutput, playback: VideoPlayback) -> None:
        clock.at(0.5, lambda: playback.seek(1.5))

    output = await played(small_video(tmp_path), 1.0, jump_later)

    jumped = next(index for index, (_, _, replace_held) in enumerate(output.shown) if replace_held)
    assert output.positions[jumped] == pytest.approx(1.5, abs=POSITION_TOLERANCE)
    assert output.positions[jumped + 1] == pytest.approx(1.5 + CAMERA_PERIOD, abs=POSITION_TOLERANCE)


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

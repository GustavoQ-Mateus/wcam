from pathlib import Path

from tests.videos import PORTRAIT_ROTATION, SMALL_HEIGHT, SMALL_WIDTH, first_frame, small_video
from wcam.media.pipeline import i420_planes
from wcam.media.placeholder import BLACK_LUMA, NEUTRAL_CHROMA
from wcam.tools.make_test_video import BACKGROUND_LUMA, MARKER_LUMA
from wcam.video.frames import fitted_i420, fitted_size, shown_size

LUMA_TOLERANCE = 12
WIDE_HEIGHT = 100


def near(value: int, expected: int) -> bool:
    return abs(int(value) - expected) <= LUMA_TOLERANCE


def test_video_with_the_camera_size_fills_the_frame(tmp_path: Path) -> None:
    frame = first_frame(small_video(tmp_path))

    luma, _, _ = i420_planes(fitted_i420(frame, SMALL_WIDTH, SMALL_HEIGHT), SMALL_WIDTH, SMALL_HEIGHT)

    assert near(luma[2, 2], MARKER_LUMA)
    assert near(luma[2, -3], BACKGROUND_LUMA)


def test_portrait_video_is_turned_upright_with_black_side_bars(tmp_path: Path) -> None:
    frame = first_frame(small_video(tmp_path, rotation=PORTRAIT_ROTATION))
    fit_width, fit_height = fitted_size(*shown_size(frame), SMALL_WIDTH, SMALL_HEIGHT)
    left = (SMALL_WIDTH - fit_width) // 2

    image = fitted_i420(frame, SMALL_WIDTH, SMALL_HEIGHT)

    luma, blue, red = i420_planes(image, SMALL_WIDTH, SMALL_HEIGHT)
    assert shown_size(frame) == (SMALL_HEIGHT, SMALL_WIDTH)
    assert fit_height == SMALL_HEIGHT
    assert (luma[:, : left - 2] == BLACK_LUMA).all()
    assert (luma[:, left + fit_width + 2 :] == BLACK_LUMA).all()
    assert (blue[:, : left // 2 - 1] == NEUTRAL_CHROMA).all()
    assert (red[:, (left + fit_width) // 2 + 1 :] == NEUTRAL_CHROMA).all()
    assert near(luma[2, left + fit_width - 3], MARKER_LUMA)
    assert near(luma[SMALL_HEIGHT - 3, left + 2], BACKGROUND_LUMA)


def test_wider_video_gets_black_bars_above_and_below(tmp_path: Path) -> None:
    frame = first_frame(small_video(tmp_path, height=WIDE_HEIGHT))

    image = fitted_i420(frame, SMALL_WIDTH, SMALL_HEIGHT)

    luma, blue, _ = i420_planes(image, SMALL_WIDTH, SMALL_HEIGHT)
    top = (SMALL_HEIGHT - WIDE_HEIGHT) // 2
    assert (luma[: top - 2] == BLACK_LUMA).all()
    assert (luma[top + WIDE_HEIGHT + 2 :] == BLACK_LUMA).all()
    assert (blue[: top // 2 - 1] == NEUTRAL_CHROMA).all()
    assert near(luma[top + 2, 2], MARKER_LUMA)


def test_larger_video_is_reduced_to_the_camera_size_without_distortion(tmp_path: Path) -> None:
    frame = first_frame(small_video(tmp_path, width=2 * SMALL_WIDTH, height=2 * SMALL_HEIGHT))

    image = fitted_i420(frame, SMALL_WIDTH, SMALL_HEIGHT)

    luma, _, _ = i420_planes(image, SMALL_WIDTH, SMALL_HEIGHT)
    assert image.shape == (SMALL_HEIGHT * 3 // 2, SMALL_WIDTH)
    assert near(luma[SMALL_HEIGHT // 4 - 3, SMALL_WIDTH // 4 - 3], MARKER_LUMA)
    assert near(luma[SMALL_HEIGHT // 4 + 3, SMALL_WIDTH // 4 + 3], BACKGROUND_LUMA)

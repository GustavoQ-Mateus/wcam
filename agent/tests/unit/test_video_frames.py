from pathlib import Path

import numpy as np
from av import VideoFrame
from av.video.reformatter import ColorRange, Colorspace

from tests.frames import nv12_from_i420
from tests.videos import PORTRAIT_ROTATION, SMALL_HEIGHT, SMALL_WIDTH, first_frame, small_video
from wcam.media.pipeline import I420_FORMAT, nv12_planes
from wcam.media.placeholder import BLACK_LUMA, NEUTRAL_CHROMA
from wcam.tools.make_test_video import BACKGROUND_LUMA, MARKER_LUMA, pattern_frame
from wcam.video.frames import SINGLE_THREAD, converted_frame, fitted_nv12, fitted_size, passes_through, shown_size
from wcam.virtualcam.sink import I420Frame

LUMA_TOLERANCE = 12
WIDE_HEIGHT = 100
UHD_WIDTH = 3840
UHD_HEIGHT = 2160


def near(value: int, expected: int) -> bool:
    return abs(int(value) - expected) <= LUMA_TOLERANCE


def test_video_with_the_camera_size_fills_the_frame(tmp_path: Path) -> None:
    frame = first_frame(small_video(tmp_path))

    luma, _, _ = nv12_planes(fitted_nv12(frame, SMALL_WIDTH, SMALL_HEIGHT), SMALL_WIDTH, SMALL_HEIGHT)

    assert near(luma[2, 2], MARKER_LUMA)
    assert near(luma[2, -3], BACKGROUND_LUMA)


def test_portrait_video_is_turned_upright_with_black_side_bars(tmp_path: Path) -> None:
    frame = first_frame(small_video(tmp_path, rotation=PORTRAIT_ROTATION))
    fit_width, fit_height = fitted_size(*shown_size(frame), SMALL_WIDTH, SMALL_HEIGHT)
    left = (SMALL_WIDTH - fit_width) // 2

    image = fitted_nv12(frame, SMALL_WIDTH, SMALL_HEIGHT)

    luma, blue, red = nv12_planes(image, SMALL_WIDTH, SMALL_HEIGHT)
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

    image = fitted_nv12(frame, SMALL_WIDTH, SMALL_HEIGHT)

    luma, blue, _ = nv12_planes(image, SMALL_WIDTH, SMALL_HEIGHT)
    top = (SMALL_HEIGHT - WIDE_HEIGHT) // 2
    assert (luma[: top - 2] == BLACK_LUMA).all()
    assert (luma[top + WIDE_HEIGHT + 2 :] == BLACK_LUMA).all()
    assert (blue[: top // 2 - 1] == NEUTRAL_CHROMA).all()
    assert near(luma[top + 2, 2], MARKER_LUMA)


def test_larger_video_is_reduced_to_the_camera_size_without_distortion(tmp_path: Path) -> None:
    frame = first_frame(small_video(tmp_path, width=2 * SMALL_WIDTH, height=2 * SMALL_HEIGHT))

    image = fitted_nv12(frame, SMALL_WIDTH, SMALL_HEIGHT)

    luma, _, _ = nv12_planes(image, SMALL_WIDTH, SMALL_HEIGHT)
    assert image.shape == (SMALL_HEIGHT * 3 // 2, SMALL_WIDTH)
    assert near(luma[SMALL_HEIGHT // 4 - 3, SMALL_WIDTH // 4 - 3], MARKER_LUMA)
    assert near(luma[SMALL_HEIGHT // 4 + 3, SMALL_WIDTH // 4 + 3], BACKGROUND_LUMA)


def camera_ready_frame(width: int, height: int) -> VideoFrame:
    frame = VideoFrame.from_ndarray(pattern_frame(width, height, 0, 1), format=I420_FORMAT)
    frame.colorspace = Colorspace.ITU709
    frame.color_range = ColorRange.MPEG
    return frame


def blank_chroma_rows(image: I420Frame, width: int, height: int) -> list[int]:
    _, blue, red = nv12_planes(image, width, height)
    return np.flatnonzero(((blue == 0) & (red == 0)).all(axis=1)).tolist()


def test_4k_video_at_the_camera_size_keeps_every_row_of_the_picture() -> None:
    image = fitted_nv12(camera_ready_frame(UHD_WIDTH, UHD_HEIGHT), UHD_WIDTH, UHD_HEIGHT)

    assert blank_chroma_rows(image, UHD_WIDTH, UHD_HEIGHT) == []


def test_4k_conversion_without_scaling_keeps_every_chroma_row() -> None:
    converted = converted_frame(camera_ready_frame(UHD_WIDTH, UHD_HEIGHT), UHD_WIDTH, UHD_HEIGHT).to_ndarray()

    assert blank_chroma_rows(np.asarray(converted, dtype=np.uint8), UHD_WIDTH, UHD_HEIGHT) == []


def test_frame_already_in_the_camera_format_is_copied_byte_for_byte() -> None:
    frame = camera_ready_frame(UHD_WIDTH, UHD_HEIGHT)
    through_swscale = frame.reformat(
        format=I420_FORMAT, dst_colorspace=Colorspace.ITU709, dst_color_range=ColorRange.MPEG, threads=SINGLE_THREAD
    )

    image = fitted_nv12(frame, UHD_WIDTH, UHD_HEIGHT)

    assert passes_through(frame, UHD_WIDTH, UHD_HEIGHT)
    assert through_swscale is not frame
    expected = nv12_from_i420(np.asarray(through_swscale.to_ndarray(), dtype=np.uint8))
    assert np.array_equal(image, expected)

import numpy as np
import pytest
from av import VideoFrame

from tests.unit.test_pipeline import random_i420
from wcam.media.color_correction import ColorTables, apple_display_tables, range_tables
from wcam.media.color_range import ColorRange, declared_range
from wcam.media.pipeline import i420_array, reformatted
from wcam.virtualcam.sink import I420Frame

CASES = [
    pytest.param(1920, 1080, 1920, 1080, id="landscape"),
    pytest.param(1080, 1920, 608, 1080, id="portrait-1080p"),
    pytest.param(720, 1280, 404, 720, id="portrait-720p-padded"),
]
FORMATS = ["yuvj420p", "yuv420p"]


def previous_i420_array(
    frame: VideoFrame,
    width: int,
    height: int,
    color_range: ColorRange,
    tables: ColorTables | None,
) -> I420Frame:
    array: I420Frame = np.ascontiguousarray(reformatted(frame, width, height, color_range).to_ndarray(), dtype=np.uint8)
    if tables is None:
        return array
    luma_table, chroma_table = tables
    for plane, table in ((array[:height], luma_table), (array[height:], chroma_table)):
        view = memoryview(plane.reshape(-1))
        view[:] = bytes(view).translate(table)
    return array


def tables_for(correction: str, color_range: ColorRange) -> ColorTables | None:
    if correction == "apple":
        return apple_display_tables(color_range)
    if correction == "range":
        return range_tables(color_range)
    return None


@pytest.mark.parametrize(("frame_width", "frame_height", "width", "height"), CASES)
@pytest.mark.parametrize("pixel_format", FORMATS)
@pytest.mark.parametrize("correction", ["apple", "range", "none"])
def test_direct_plane_translation_matches_the_previous_conversion_byte_for_byte(
    frame_width: int, frame_height: int, width: int, height: int, pixel_format: str, correction: str
) -> None:
    frame = VideoFrame.from_ndarray(random_i420(frame_width, frame_height), format=pixel_format)
    color_range = declared_range(frame)
    tables = tables_for(correction, color_range)

    converted = i420_array(frame, width, height, color_range, tables)

    expected = previous_i420_array(frame, width, height, color_range, tables)
    assert converted.shape == (height * 3 // 2, width)
    assert converted.tobytes() == expected.tobytes()


def test_padded_planes_are_cropped_to_the_image_width() -> None:
    frame = VideoFrame.from_ndarray(random_i420(720, 1280), format="yuvj420p")

    padded = reformatted(frame, 404, 720, ColorRange.FULL)

    assert any(plane.line_size != plane.width for plane in padded.planes)

import numpy as np
import pytest
from av import VideoFrame

from tests.frames import nv12_from_i420
from tests.unit.test_pipeline import random_i420
from wcam.media.color_correction import ColorTables, apple_display_tables, range_tables
from wcam.media.color_range import ColorRange, declared_range
from wcam.media.pipeline import nv12_frame, reformatted
from wcam.media.plane_translation import PlaneTranslator
from wcam.tools.make_reference import HEIGHT, WIDTH, reference_frame
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
def test_nv12_translation_matches_the_previous_i420_conversion_then_nv12_byte_for_byte(
    frame_width: int, frame_height: int, width: int, height: int, pixel_format: str, correction: str
) -> None:
    frame = VideoFrame.from_ndarray(random_i420(frame_width, frame_height), format=pixel_format)
    color_range = declared_range(frame)
    tables = tables_for(correction, color_range)

    converted = nv12_frame(frame, width, height, color_range, tables)

    expected = nv12_from_i420(previous_i420_array(frame, width, height, color_range, tables))
    assert converted.shape == (height * 3 // 2, width)
    assert converted.tobytes() == expected.tobytes()


def test_padded_planes_are_cropped_to_the_image_width() -> None:
    frame = VideoFrame.from_ndarray(random_i420(720, 1280), format="yuvj420p")

    padded = reformatted(frame, 404, 720, ColorRange.FULL)

    assert any(plane.line_size != plane.width for plane in padded.planes)


def previous_mirrored(array: I420Frame, width: int, height: int) -> I420Frame:
    mirrored = array.copy()
    luma_size = width * height
    chroma_size = luma_size // 4
    offsets = (
        (0, height, width),
        (luma_size, height // 2, width // 2),
        (luma_size + chroma_size, height // 2, width // 2),
    )
    flat = mirrored.reshape(-1)
    for offset, rows, columns in offsets:
        plane = flat[offset : offset + rows * columns].reshape(rows, columns)
        plane[:] = plane[:, ::-1].copy()
    return mirrored


@pytest.mark.parametrize(("frame_width", "frame_height", "width", "height"), CASES)
@pytest.mark.parametrize("pixel_format", FORMATS)
@pytest.mark.parametrize("correction", ["apple", "range", "none"])
def test_mirrored_nv12_translation_matches_the_previous_i420_conversion_then_nv12_byte_for_byte(
    frame_width: int, frame_height: int, width: int, height: int, pixel_format: str, correction: str
) -> None:
    frame = VideoFrame.from_ndarray(random_i420(frame_width, frame_height), format=pixel_format)
    color_range = declared_range(frame)
    tables = tables_for(correction, color_range)

    converted = nv12_frame(frame, width, height, color_range, tables, mirror=True)

    expected = nv12_from_i420(
        previous_mirrored(previous_i420_array(frame, width, height, color_range, tables), width, height)
    )
    assert converted.tobytes() == expected.tobytes()


def test_translator_keeps_its_graph_while_the_tables_and_size_stay_the_same() -> None:
    translator = PlaneTranslator()
    frame = VideoFrame.from_ndarray(random_i420(64, 48), format="yuvj420p")
    tables = range_tables(ColorRange.FULL)

    first = translator.translated(frame, tables, mirror=False)
    second = translator.translated(frame, tables, mirror=False)

    assert first.tobytes() == second.tobytes()
    assert translator.graphs_built == 1


def reference_video_frame() -> VideoFrame:
    planes = np.frombuffer(reference_frame()[-WIDTH * HEIGHT * 3 // 2 :], dtype=np.uint8)
    return VideoFrame.from_ndarray(planes.reshape(HEIGHT * 3 // 2, WIDTH), format="yuvj420p")


def test_reference_video_with_tables_and_mirror_matches_the_previous_i420_conversion_then_nv12() -> None:
    frame = reference_video_frame()
    tables = apple_display_tables(ColorRange.FULL)

    converted = nv12_frame(frame, WIDTH, HEIGHT, ColorRange.FULL, tables, mirror=True)

    previous = previous_i420_array(frame, WIDTH, HEIGHT, ColorRange.FULL, tables)
    assert converted.tobytes() == nv12_from_i420(previous_mirrored(previous, WIDTH, HEIGHT)).tobytes()

import numpy as np
from av import VideoFrame

from tests.unit.test_pipeline import (
    PORTRAIT_HEIGHT,
    PORTRAIT_WIDTH,
    SteppingClock,
    live_pipeline,
    phone_frame,
    random_i420,
)
from wcam.media.color_correction import apple_display_tables
from wcam.media.color_range import ColorRange
from wcam.media.pipeline import FrameSource, i420_array, i420_planes
from wcam.media.placeholder import BLACK_LUMA, ICON_LUMA, NEUTRAL_CHROMA, camera_off_i420
from wcam.virtualcam.sink import OUTPUT_HEIGHT, OUTPUT_WIDTH, I420Frame

SMALL_WIDTH = 64
SMALL_HEIGHT = 48


def mirrored_planes(frame: I420Frame, width: int, height: int) -> bytes:
    return b"".join(np.ascontiguousarray(plane[:, ::-1]).tobytes() for plane in i420_planes(frame, width, height))


def test_camera_off_frame_has_the_icon_in_the_center_and_black_at_the_border() -> None:
    frame = camera_off_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT)

    luma, blue, red = i420_planes(frame, OUTPUT_WIDTH, OUTPUT_HEIGHT)
    assert luma[OUTPUT_HEIGHT // 2, OUTPUT_WIDTH // 2] == ICON_LUMA
    assert luma[0, 0] == BLACK_LUMA
    assert luma[-1, -1] == BLACK_LUMA
    assert luma[OUTPUT_HEIGHT // 2, 0] == BLACK_LUMA
    assert (luma[:, : OUTPUT_WIDTH // 4] == BLACK_LUMA).all()
    assert (blue == NEUTRAL_CHROMA).all()
    assert (red == NEUTRAL_CHROMA).all()


def test_camera_off_frame_follows_the_announced_size() -> None:
    frame = camera_off_i420(1280, 720)

    luma, _, _ = i420_planes(frame, 1280, 720)
    assert frame.shape == (720 * 3 // 2, 1280)
    assert luma[360, 640] == ICON_LUMA


def test_mirror_reverses_the_columns_of_every_plane() -> None:
    original = random_i420(SMALL_WIDTH, SMALL_HEIGHT)
    frame = VideoFrame.from_ndarray(original, format="yuv420p")

    mirrored = i420_array(frame, SMALL_WIDTH, SMALL_HEIGHT, ColorRange.LIMITED, mirror=True)

    assert mirrored.tobytes() == mirrored_planes(original, SMALL_WIDTH, SMALL_HEIGHT)


def test_mirror_with_color_tables_equals_the_tables_then_the_mirror() -> None:
    frame = VideoFrame.from_ndarray(random_i420(SMALL_WIDTH, SMALL_HEIGHT), format="yuvj420p")
    tables = apple_display_tables(ColorRange.FULL)

    mirrored = i420_array(frame, SMALL_WIDTH, SMALL_HEIGHT, ColorRange.FULL, tables, mirror=True)

    translated = i420_array(frame, SMALL_WIDTH, SMALL_HEIGHT, ColorRange.FULL, tables)
    assert mirrored.tobytes() == mirrored_planes(translated, SMALL_WIDTH, SMALL_HEIGHT)


def test_mirrored_phone_frame_reaches_the_sink_mirrored() -> None:
    pipeline, sink = live_pipeline()
    original = random_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT)
    pipeline.apply_controls(frozen=False, camera_off=False, mirror=True)

    pipeline.deliver(VideoFrame.from_ndarray(original, format="yuv420p"))

    assert sink.last_frame is not None
    assert sink.last_frame.tobytes() == mirrored_planes(original, OUTPUT_WIDTH, OUTPUT_HEIGHT)


def test_mirrored_portrait_frame_keeps_black_bands_on_both_sides() -> None:
    pipeline, sink = live_pipeline()
    pipeline.apply_controls(frozen=False, camera_off=False, mirror=True)

    pipeline.deliver(phone_frame(PORTRAIT_WIDTH, PORTRAIT_HEIGHT))

    assert sink.last_frame is not None
    luma, _, _ = i420_planes(sink.last_frame, OUTPUT_WIDTH, OUTPUT_HEIGHT)
    assert (luma[:, :600] == BLACK_LUMA).all()
    assert (luma[:, -600:] == BLACK_LUMA).all()


def test_frozen_image_repeats_the_last_delivered_frame_while_the_phone_keeps_sending() -> None:
    pipeline, sink = live_pipeline()
    pipeline.deliver(phone_frame(seed=1))
    held = sink.last_frame
    pipeline.apply_controls(frozen=True, camera_off=False, mirror=False)

    pipeline.deliver(phone_frame(seed=2))
    pipeline.deliver(None)

    assert sink.last_frame is held
    assert pipeline.source is FrameSource.HELD


def test_unfrozen_image_goes_back_to_the_phone() -> None:
    pipeline, sink = live_pipeline()
    pipeline.deliver(phone_frame(seed=1))
    pipeline.apply_controls(frozen=True, camera_off=False, mirror=False)
    pipeline.deliver(phone_frame(seed=2))
    pipeline.apply_controls(frozen=False, camera_off=False, mirror=False)

    pipeline.deliver(phone_frame(seed=3))

    assert sink.last_frame is not None
    assert sink.last_frame.tobytes() == random_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT, 3).tobytes()
    assert pipeline.source is FrameSource.PHONE


def test_camera_off_sends_the_camera_off_frame() -> None:
    pipeline, sink = live_pipeline()
    pipeline.deliver(phone_frame())
    pipeline.apply_controls(frozen=False, camera_off=True, mirror=False)

    pipeline.deliver(None)

    assert sink.last_frame is not None
    assert sink.last_frame.tobytes() == camera_off_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT).tobytes()
    assert pipeline.source is FrameSource.CAMERA_OFF


def test_turning_the_camera_on_starts_counting_the_frame_age_again() -> None:
    clock = SteppingClock()
    pipeline, _ = live_pipeline(clock)
    pipeline.apply_controls(frozen=False, camera_off=True, mirror=False)
    clock.now += 60

    pipeline.apply_controls(frozen=False, camera_off=False, mirror=False)

    assert pipeline.phone_frame_age() == 0

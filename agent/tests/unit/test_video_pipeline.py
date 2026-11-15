from tests.unit.test_output_controls import mirrored_planes
from tests.unit.test_pipeline import random_i420
from wcam.media.pipeline import FramePipeline, FrameSource, VideoImageFrame
from wcam.virtualcam.fake_sink import FakeSink
from wcam.virtualcam.sink import OUTPUT_HEIGHT, OUTPUT_WIDTH

OTHER_SEED = 11


def video_pipeline() -> tuple[FramePipeline, FakeSink]:
    sink = FakeSink()
    pipeline = FramePipeline(sink)
    pipeline.open()
    pipeline.start_video()
    return pipeline, sink


def test_video_frame_reaches_the_camera_as_the_video_source() -> None:
    pipeline, sink = video_pipeline()
    image = random_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT)

    pipeline.deliver(VideoImageFrame(image, replace_held=False))

    assert sink.last_frame is not None
    assert sink.last_frame.tobytes() == image.tobytes()
    assert pipeline.source is FrameSource.VIDEO
    assert pipeline.frames_delivered == 1


def test_camera_repeats_the_last_video_frame_while_the_next_one_is_decoded() -> None:
    pipeline, sink = video_pipeline()
    image = random_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT)
    pipeline.deliver(VideoImageFrame(image, replace_held=False))

    pipeline.deliver(None)

    assert sink.last_frame is not None
    assert sink.last_frame.tobytes() == image.tobytes()
    assert pipeline.source is FrameSource.VIDEO


def test_mirror_reverses_the_video_frame() -> None:
    pipeline, sink = video_pipeline()
    pipeline.apply_controls(frozen=False, camera_off=False, mirror=True)
    image = random_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT)

    pipeline.deliver(VideoImageFrame(image, replace_held=False))

    assert sink.last_frame is not None
    assert sink.last_frame.tobytes() == mirrored_planes(image, OUTPUT_WIDTH, OUTPUT_HEIGHT)


def test_frozen_video_holds_its_frame_until_a_jump_replaces_it() -> None:
    pipeline, sink = video_pipeline()
    first = random_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT)
    jumped = random_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT, OTHER_SEED)
    pipeline.deliver(VideoImageFrame(first, replace_held=False))
    pipeline.apply_controls(frozen=True, camera_off=False, mirror=False)

    pipeline.deliver(None)
    held = sink.last_frame
    pipeline.deliver(VideoImageFrame(jumped, replace_held=True))

    assert held is not None
    assert held.tobytes() == first.tobytes()
    assert sink.last_frame is not None
    assert sink.last_frame.tobytes() == jumped.tobytes()
    assert pipeline.source is FrameSource.HELD


def test_stopping_the_video_brings_back_the_waiting_frame() -> None:
    pipeline, sink = video_pipeline()
    pipeline.deliver(VideoImageFrame(random_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT), replace_held=False))

    pipeline.stop_video()
    pipeline.deliver(None)

    assert sink.last_frame is pipeline.placeholder
    assert pipeline.source is FrameSource.PLACEHOLDER

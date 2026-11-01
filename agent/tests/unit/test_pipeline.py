import asyncio

import numpy as np
from av import VideoFrame

from wcam.media.pipeline import FramePipeline, FrameSource
from wcam.media.placeholder import black_i420
from wcam.virtualcam.fake_sink import FakeSink
from wcam.virtualcam.sink import OUTPUT_FPS, OUTPUT_HEIGHT, OUTPUT_WIDTH, I420Frame

SEED = 7
RUN_SECONDS = 0.5
MINIMUM_PLACEHOLDERS_IN_RUN = 10


class SteppingClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def random_i420(width: int, height: int) -> I420Frame:
    generator = np.random.default_rng(SEED)
    return generator.integers(0, 256, size=(height * 3 // 2, width), dtype=np.uint8)


def phone_frame(width: int = OUTPUT_WIDTH, height: int = OUTPUT_HEIGHT) -> VideoFrame:
    return VideoFrame.from_ndarray(random_i420(width, height), format="yuv420p")


def live_pipeline(clock: SteppingClock | None = None) -> tuple[FramePipeline, FakeSink]:
    sink = FakeSink()
    pipeline = FramePipeline(sink, clock=clock or SteppingClock())
    pipeline.open()
    pipeline.start_phone()
    return pipeline, sink


def test_phone_frame_reaches_sink_unchanged_when_size_matches() -> None:
    pipeline, sink = live_pipeline()
    original = random_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT)

    pipeline.deliver(VideoFrame.from_ndarray(original, format="yuv420p"))

    assert sink.last_frame is not None
    assert sink.last_frame.dtype == np.uint8
    assert sink.last_frame.size == OUTPUT_WIDTH * OUTPUT_HEIGHT * 3 // 2
    assert sink.last_frame.tobytes() == original.tobytes()
    assert pipeline.frames_scaled == 0
    assert pipeline.source is FrameSource.PHONE


def test_landscape_frame_with_other_size_is_scaled_and_counted() -> None:
    pipeline, sink = live_pipeline()

    pipeline.deliver(phone_frame(1280, 720))
    pipeline.deliver(phone_frame(1440, 1080))

    assert pipeline.frames_scaled == 2
    assert sink.last_frame is not None
    assert sink.last_frame.shape == (OUTPUT_HEIGHT * 3 // 2, OUTPUT_WIDTH)
    luma = sink.last_frame[:OUTPUT_HEIGHT]
    assert (luma[:, :240] == 16).all()
    assert (luma[:, -240:] == 16).all()
    assert not (luma[:, 240:-240] == 16).all()


def test_portrait_frame_is_replaced_by_placeholder() -> None:
    pipeline, sink = live_pipeline()

    pipeline.deliver(phone_frame(OUTPUT_HEIGHT, OUTPUT_WIDTH))

    assert sink.last_frame is not None
    assert sink.last_frame.tobytes() == black_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT).tobytes()
    assert pipeline.source is FrameSource.PLACEHOLDER


def test_sink_receives_placeholder_without_session() -> None:
    sink = FakeSink()
    pipeline = FramePipeline(sink)
    pipeline.open()

    pipeline.deliver(None)

    assert sink.frames_sent == 1
    assert sink.last_frame is not None
    assert sink.last_frame.tobytes() == black_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT).tobytes()
    assert pipeline.source is FrameSource.PLACEHOLDER


def test_sink_receives_placeholder_while_awaiting_confirmation() -> None:
    sink = FakeSink()
    pipeline = FramePipeline(sink)
    pipeline.open()

    pipeline.deliver(phone_frame())

    assert sink.last_frame is not None
    assert sink.last_frame.tobytes() == black_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT).tobytes()
    assert pipeline.source is FrameSource.PLACEHOLDER


def test_short_gap_repeats_the_last_phone_frame() -> None:
    clock = SteppingClock()
    pipeline, sink = live_pipeline(clock)
    pipeline.deliver(phone_frame())
    sent = sink.last_frame

    clock.now += 0.5
    pipeline.deliver(None)

    assert sink.last_frame is sent
    assert pipeline.source is FrameSource.PHONE


def test_sink_receives_placeholder_after_one_second_without_frames() -> None:
    clock = SteppingClock()
    pipeline, sink = live_pipeline(clock)
    pipeline.deliver(phone_frame())

    clock.now += 1.01
    pipeline.deliver(None)

    assert sink.last_frame is not None
    assert sink.last_frame.tobytes() == black_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT).tobytes()
    assert pipeline.source is FrameSource.PLACEHOLDER


def test_stopping_the_phone_returns_to_placeholder_at_once() -> None:
    pipeline, sink = live_pipeline()
    pipeline.deliver(phone_frame())

    pipeline.stop_phone()
    pipeline.deliver(None)

    assert sink.last_frame is not None
    assert sink.last_frame.tobytes() == black_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT).tobytes()


def test_new_phone_session_resets_scaled_count() -> None:
    pipeline, _ = live_pipeline()
    pipeline.deliver(phone_frame(1280, 720))

    pipeline.start_phone()

    assert pipeline.frames_scaled == 0


async def test_running_pipeline_feeds_placeholders_continuously() -> None:
    sink = FakeSink()
    pipeline = FramePipeline(sink)
    pipeline.open()

    task = asyncio.create_task(pipeline.run())
    await asyncio.sleep(RUN_SECONDS)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert MINIMUM_PLACEHOLDERS_IN_RUN <= sink.frames_sent <= RUN_SECONDS * OUTPUT_FPS + 2
    assert sink.status.state == "unavailable"


def test_unopened_sink_receives_nothing() -> None:
    sink = FakeSink()
    pipeline = FramePipeline(sink)

    pipeline.deliver(None)

    assert sink.frames_sent == 0

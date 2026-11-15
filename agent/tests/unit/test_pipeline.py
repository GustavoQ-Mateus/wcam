import asyncio

import numpy as np
import pytest
from av import VideoFrame

from wcam.api.schemas import video_body
from wcam.media.color_correction import CameraColorSpace, DisplayConvention, color_correction
from wcam.media.color_range import LUMA_TABLE
from wcam.media.metrics import Orientation, VideoStats
from wcam.media.pipeline import FREEZE_SECONDS, FramePipeline, FrameSource, i420_planes
from wcam.media.placeholder import black_i420
from wcam.virtualcam.fake_sink import FakeSink
from wcam.virtualcam.sink import OUTPUT_FPS, OUTPUT_HEIGHT, OUTPUT_WIDTH, I420Frame

SEED = 7
RUN_SECONDS = 0.5
MINIMUM_PLACEHOLDERS_IN_RUN = 10
FREEZE_TOLERANCE_SECONDS = 0.2
STANDARD = DisplayConvention.STANDARD
PORTRAIT_WIDTH = 1080
PORTRAIT_HEIGHT = 1920
PORTRAIT_REDUCED_WIDTH = 608
PORTRAIT_LEFT = 656
IMAGE_LUMA = 200
IMAGE_CHROMA = 90


class SteppingClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def random_i420(width: int, height: int, seed: int = SEED) -> I420Frame:
    generator = np.random.default_rng(seed)
    return generator.integers(0, 256, size=(height * 3 // 2, width), dtype=np.uint8)


def phone_frame(width: int = OUTPUT_WIDTH, height: int = OUTPUT_HEIGHT, seed: int = SEED) -> VideoFrame:
    return VideoFrame.from_ndarray(random_i420(width, height, seed), format="yuv420p")


def flat_frame(width: int, height: int, luma: int, chroma: int, pixel_format: str = "yuv420p") -> VideoFrame:
    image = np.full((height * 3 // 2, width), chroma, dtype=np.uint8)
    image[:height] = luma
    return VideoFrame.from_ndarray(image, format=pixel_format)


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


def test_landscape_frame_with_other_size_repeats_the_last_good_frame() -> None:
    pipeline, sink = live_pipeline()
    pipeline.deliver(phone_frame())
    good = sink.last_frame

    pipeline.deliver(phone_frame(1280, 720))

    assert sink.last_frame is good
    assert pipeline.frames_scaled == 0


def test_landscape_frame_with_other_size_before_any_good_one_sends_black() -> None:
    pipeline, sink = live_pipeline()

    pipeline.deliver(phone_frame(1280, 720))

    assert sink.last_frame is not None
    assert sink.last_frame.tobytes() == black_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT).tobytes()
    assert pipeline.source is FrameSource.PLACEHOLDER
    assert pipeline.frames_scaled == 0


def test_portrait_frame_is_reduced_to_the_output_height_and_centered_between_black_bands() -> None:
    pipeline, sink = live_pipeline()

    pipeline.deliver(flat_frame(PORTRAIT_WIDTH, PORTRAIT_HEIGHT, IMAGE_LUMA, IMAGE_CHROMA))

    assert sink.last_frame is not None
    luma, blue, red = i420_planes(sink.last_frame, OUTPUT_WIDTH, OUTPUT_HEIGHT)
    left, right = PORTRAIT_LEFT, PORTRAIT_LEFT + PORTRAIT_REDUCED_WIDTH
    assert (luma[:, left:right] == IMAGE_LUMA).all()
    assert (luma[:, :left] == 16).all()
    assert (luma[:, right:] == 16).all()
    for chroma in (blue, red):
        assert (chroma[:, left // 2 : right // 2] == IMAGE_CHROMA).all()
        assert (chroma[:, : left // 2] == 128).all()
        assert (chroma[:, right // 2 :] == 128).all()
    assert pipeline.frames_scaled == 1
    assert pipeline.portrait
    assert pipeline.source is FrameSource.PHONE


def test_portrait_frame_follows_the_announced_height() -> None:
    pipeline, sink = live_pipeline()
    sink.request_format(1280, 720, 60)
    pipeline.follow(sink.announced_format())

    pipeline.deliver(flat_frame(PORTRAIT_WIDTH, PORTRAIT_HEIGHT, IMAGE_LUMA, IMAGE_CHROMA))

    assert sink.last_frame is not None
    luma = sink.last_frame[:720]
    assert sink.last_frame.shape == (720 * 3 // 2, 1280)
    assert (luma[:, 438:842] == IMAGE_LUMA).all()
    assert (luma[:, :438] == 16).all()
    assert (luma[:, 842:] == 16).all()


def test_frame_in_the_announced_format_reaches_the_sink_unchanged() -> None:
    pipeline, sink = live_pipeline()
    sink.request_format(3840, 2160, 30)
    pipeline.follow(sink.announced_format())
    original = random_i420(3840, 2160)

    pipeline.deliver(VideoFrame.from_ndarray(original, format="yuv420p"))

    assert sink.last_frame is not None
    assert sink.last_frame.tobytes() == original.tobytes()
    assert pipeline.output.fps == 30


def test_last_good_frame_of_the_previous_format_is_not_sent_after_a_change() -> None:
    pipeline, sink = live_pipeline()
    pipeline.deliver(phone_frame())
    sink.request_format(1280, 720, 60)
    pipeline.follow(sink.announced_format())

    pipeline.deliver(None)

    assert sink.last_frame is not None
    assert sink.last_frame.tobytes() == black_i420(1280, 720).tobytes()


async def test_format_request_runs_on_the_frame_worker_and_is_followed() -> None:
    pipeline, sink = live_pipeline()

    accepted = await pipeline.request_format(1280, 720, 60)

    assert accepted
    assert sink.requests == [(1280, 720, 60)]
    assert (pipeline.output.width, pipeline.output.height, pipeline.output.fps) == (1280, 720, 60)


async def test_refused_format_request_keeps_the_output() -> None:
    pipeline, sink = live_pipeline()
    sink.accepts_formats = False

    accepted = await pipeline.request_format(1280, 720, 60)

    assert not accepted
    assert (pipeline.output.width, pipeline.output.height) == (OUTPUT_WIDTH, OUTPUT_HEIGHT)


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


@pytest.mark.parametrize("seconds", [0.6, 1.5, FREEZE_SECONDS - FREEZE_TOLERANCE_SECONDS])
def test_gap_shorter_than_three_seconds_freezes_the_last_phone_frame(seconds: float) -> None:
    clock = SteppingClock()
    pipeline, sink = live_pipeline(clock)
    pipeline.deliver(phone_frame())
    sent = sink.last_frame

    clock.now += seconds
    pipeline.deliver(None)

    assert sink.last_frame is sent
    assert pipeline.source is FrameSource.FROZEN


def test_gap_longer_than_three_seconds_turns_to_black() -> None:
    clock = SteppingClock()
    pipeline, sink = live_pipeline(clock)
    pipeline.deliver(phone_frame())

    clock.now += FREEZE_SECONDS + FREEZE_TOLERANCE_SECONDS
    pipeline.deliver(None)

    assert sink.last_frame is not None
    assert (sink.last_frame[:OUTPUT_HEIGHT] == 16).all()
    assert (sink.last_frame[OUTPUT_HEIGHT:] == 128).all()
    assert pipeline.source is FrameSource.PLACEHOLDER


def test_frame_after_freeze_goes_back_to_phone() -> None:
    clock = SteppingClock()
    pipeline, sink = live_pipeline(clock)
    pipeline.deliver(phone_frame())
    clock.now += 2.0
    pipeline.deliver(None)

    pipeline.deliver(phone_frame(seed=SEED + 1))

    assert pipeline.source is FrameSource.PHONE
    assert sink.last_frame is not None
    assert sink.last_frame.tobytes() == random_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT, SEED + 1).tobytes()


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


def test_frozen_frame_is_sent_on_every_tick_until_black() -> None:
    clock = SteppingClock()
    pipeline, sink = live_pipeline(clock)
    pipeline.deliver(phone_frame())
    frozen = sink.last_frame
    ticks = round((FREEZE_SECONDS - FREEZE_TOLERANCE_SECONDS) * OUTPUT_FPS)

    sent: list[I420Frame | None] = []
    for _ in range(ticks):
        clock.now += 1 / OUTPUT_FPS
        pipeline.deliver(None)
        sent.append(sink.last_frame)

    assert sink.frames_sent == ticks + 1
    assert all(frame is frozen for frame in sent)


def test_portrait_image_gets_the_color_tables_and_the_bands_stay_black() -> None:
    pipeline, sink = live_pipeline()
    pipeline.color_correction = color_correction(CameraColorSpace("bt709", "bt709", "bt709", True), STANDARD)

    pipeline.deliver(flat_frame(PORTRAIT_WIDTH, PORTRAIT_HEIGHT, IMAGE_LUMA, IMAGE_CHROMA, "yuvj420p"))

    assert sink.last_frame is not None
    luma = sink.last_frame[:OUTPUT_HEIGHT]
    left, right = PORTRAIT_LEFT, PORTRAIT_LEFT + PORTRAIT_REDUCED_WIDTH
    assert (luma[:, left:right] == LUMA_TABLE[IMAGE_LUMA]).all()
    assert (luma[:, :left] == 16).all()
    assert (sink.last_frame[OUTPUT_HEIGHT:, : left // 2] == 128).all()


def test_portrait_frame_reports_portrait_orientation() -> None:
    stats = VideoStats(1080, 1920, 30.0, 9000, orientation=Orientation.PORTRAIT)

    assert video_body(stats).orientation == "portrait"
    assert VideoStats(1920, 1080, 30.0, 9000).orientation is Orientation.LANDSCAPE


def test_longest_gap_between_phone_frames_is_kept_until_read() -> None:
    clock = SteppingClock()
    pipeline, _ = live_pipeline(clock)
    pipeline.deliver(phone_frame())
    for step in (0.2, 0.6, 0.1):
        clock.now += step
        pipeline.deliver(phone_frame())

    longest = pipeline.take_longest_gap()

    assert longest is not None
    assert longest.seconds == pytest.approx(0.6)
    assert pipeline.take_longest_gap() is None

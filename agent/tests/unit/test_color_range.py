import numpy as np
import pytest
from av import VideoFrame
from av.video.reformatter import ColorRange as DeclaredRange
from av.video.reformatter import Colorspace

from tests.unit.test_pipeline import live_pipeline, random_i420
from wcam.media.color_range import CHROMA_TABLE, LUMA_TABLE, ColorRange, declared_matrix, declared_range
from wcam.tools.synthetic_h264 import decode, encode, h264_decoder, h264_encoder
from wcam.virtualcam.sink import OUTPUT_HEIGHT, OUTPUT_WIDTH, I420Frame

SMALL_WIDTH = 64
SMALL_HEIGHT = 48
SCALED_WIDTH = 720
SCALED_HEIGHT = 1280
SMALL_FPS = 30
SMALL_BITRATE_BPS = 500_000
SMPTE170M = 6


def flat_i420(width: int, height: int, luma: int, chroma: int) -> I420Frame:
    frame = np.full((height * 3 // 2, width), chroma, dtype=np.uint8)
    frame[:height] = luma
    return frame


def full_range_frame(luma: int, chroma: int, width: int = OUTPUT_WIDTH, height: int = OUTPUT_HEIGHT) -> VideoFrame:
    return VideoFrame.from_ndarray(flat_i420(width, height, luma, chroma), format="yuvj420p")


def decoded_full_range_frame() -> VideoFrame:
    encoder = h264_encoder(SMALL_WIDTH, SMALL_HEIGHT, SMALL_FPS, SMALL_BITRATE_BPS, "yuvj420p")
    packets = encode([full_range_frame(0, 128, SMALL_WIDTH, SMALL_HEIGHT)], encoder)
    return decode(packets, h264_decoder())[0]


def test_full_range_extremes_map_to_limited_range() -> None:
    assert (LUMA_TABLE[0], LUMA_TABLE[255]) == (16, 235)
    assert (CHROMA_TABLE[0], CHROMA_TABLE[128], CHROMA_TABLE[255]) == (16, 128, 240)


def test_no_luma_above_zero_becomes_black_or_darker() -> None:
    assert (LUMA_TABLE[1:] > 16).all()


def test_tables_round_to_the_nearest_integer() -> None:
    assert LUMA_TABLE[128] == round(16 + 128 * 219 / 255)
    assert CHROMA_TABLE[64] == round(128 + (64 - 128) * 224 / 255)


@pytest.mark.parametrize(("luma", "expected_luma"), [(0, 16), (255, 235), (128, 126)])
def test_full_range_phone_frame_reaches_sink_in_limited_range(luma: int, expected_luma: int) -> None:
    pipeline, sink = live_pipeline()

    pipeline.deliver(full_range_frame(luma, 128))

    assert sink.last_frame is not None
    assert (sink.last_frame[:OUTPUT_HEIGHT] == expected_luma).all()
    assert (sink.last_frame[OUTPUT_HEIGHT:] == 128).all()
    assert pipeline.color_range is ColorRange.FULL


def test_full_range_declared_on_yuv420p_frame_is_limited_too() -> None:
    pipeline, sink = live_pipeline()
    frame = VideoFrame.from_ndarray(flat_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT, 0, 255), format="yuv420p")
    frame.color_range = DeclaredRange.JPEG

    pipeline.deliver(frame)

    assert sink.last_frame is not None
    assert (sink.last_frame[:OUTPUT_HEIGHT] == 16).all()
    assert (sink.last_frame[OUTPUT_HEIGHT:] == 240).all()


@pytest.mark.parametrize("declared", [DeclaredRange.MPEG, DeclaredRange.UNSPECIFIED])
def test_limited_and_unspecified_range_pass_byte_for_byte(declared: DeclaredRange) -> None:
    pipeline, sink = live_pipeline()
    original = random_i420(OUTPUT_WIDTH, OUTPUT_HEIGHT)
    frame = VideoFrame.from_ndarray(original, format="yuv420p")
    frame.color_range = declared

    pipeline.deliver(frame)

    assert sink.last_frame is not None
    assert sink.last_frame.tobytes() == original.tobytes()


def test_reduced_portrait_full_range_frame_is_converted_only_once() -> None:
    pipeline, sink = live_pipeline()

    pipeline.deliver(full_range_frame(255, 128, SCALED_WIDTH, SCALED_HEIGHT))

    assert sink.last_frame is not None
    assert (sink.last_frame[OUTPUT_HEIGHT // 2, OUTPUT_WIDTH // 2]) == 235
    assert pipeline.frames_scaled == 1


def test_decoded_yuvj420p_frame_is_recognised_as_full_range() -> None:
    frame = decoded_full_range_frame()

    assert declared_range(frame) is ColorRange.FULL


@pytest.mark.parametrize(
    ("colorspace", "expected"),
    [(Colorspace.ITU709, "bt709"), (Colorspace.ITU601, "bt601"), (SMPTE170M, "bt601"), (2, "unspecified")],
)
def test_declared_matrix_uses_contract_names(colorspace: int, expected: str) -> None:
    frame = VideoFrame(SMALL_WIDTH, SMALL_HEIGHT, "yuv420p")
    frame.colorspace = colorspace

    assert declared_matrix(frame) == expected


def test_new_phone_session_forgets_the_previous_declaration() -> None:
    pipeline, _ = live_pipeline()
    pipeline.deliver(full_range_frame(0, 128))

    pipeline.start_phone()

    assert pipeline.color_range is ColorRange.UNSPECIFIED

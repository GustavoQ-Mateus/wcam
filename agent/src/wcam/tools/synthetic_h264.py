from collections.abc import Iterable, Iterator
from fractions import Fraction
from typing import Protocol, cast

import av
import numpy as np
from av import VideoFrame

ENCODER_NAME = "libx264"
DECODER_NAME = "h264"
ENCODER_OPTIONS = {"preset": "ultrafast", "tune": "zerolatency"}
I420_FORMAT = "yuv420p"
SEED = 20261106
SHIFT_PIXELS_PER_FRAME = 4


class CodedPacket(Protocol):
    pts: int | None
    time_base: Fraction | None
    is_keyframe: bool

    def __bytes__(self) -> bytes: ...


class VideoEncoder(Protocol):
    def encode(self, frame: VideoFrame | None = None) -> list[CodedPacket]: ...


class VideoDecoder(Protocol):
    def decode(self, packet: CodedPacket | None = None) -> list[VideoFrame]: ...


def h264_encoder(
    width: int,
    height: int,
    fps: int,
    bitrate_bps: int,
    pixel_format: str = I420_FORMAT,
) -> VideoEncoder:
    context = av.CodecContext.create(ENCODER_NAME, "w")
    context.width = width
    context.height = height
    context.pix_fmt = pixel_format
    context.time_base = Fraction(1, fps)
    context.framerate = Fraction(fps)
    context.bit_rate = bitrate_bps
    context.options = {**ENCODER_OPTIONS, "keyint": "infinite"}
    return cast(VideoEncoder, context)


def h264_decoder() -> VideoDecoder:
    return cast(VideoDecoder, av.CodecContext.create(DECODER_NAME, "r"))


def encode(frames: Iterable[VideoFrame], encoder: VideoEncoder) -> list[CodedPacket]:
    packets: list[CodedPacket] = []
    for index, frame in enumerate(frames):
        frame.pts = index
        packets.extend(encoder.encode(frame))
    packets.extend(encoder.encode(None))
    return packets


def decode(packets: Iterable[CodedPacket], decoder: VideoDecoder) -> list[VideoFrame]:
    frames = [frame for packet in packets for frame in decoder.decode(packet)]
    frames.extend(decoder.decode(None))
    return frames


def moving_frames(width: int, height: int, count: int, pixel_format: str = I420_FORMAT) -> Iterator[VideoFrame]:
    generator = np.random.default_rng(SEED)
    image = generator.integers(0, 256, size=(height * 3 // 2, width), dtype=np.uint8)
    for index in range(count):
        shifted = np.roll(image, index * SHIFT_PIXELS_PER_FRAME, axis=1)
        yield VideoFrame.from_ndarray(shifted, format=pixel_format)

import sys
from collections.abc import Buffer, Iterator
from fractions import Fraction
from typing import cast

import av
import numpy as np
import psutil
import pytest
from av import VideoFrame
from av.video.codeccontext import VideoCodecContext

from wcam.decoding.hardware import HardwareDecodeError, HardwareDecoderProcess, HardwareStream
from wcam.decoding.messages import EncodedPacket
from wcam.decoding.status import FallbackReason
from wcam.media.phone_decoder import contains_idr
from wcam.process_priority import ABOVE_NORMAL_PRIORITY_CLASS
from wcam.tools.make_reference import FRAME_MARKER, HEIGHT, WIDTH, reference_frame
from wcam.tools.synthetic_h264 import VideoEncoder, encode

FPS = 30
FRAME_COUNT = 30
BITRATE_BPS = 8_000_000
SHIFT_PIXELS_PER_FRAME = 4
FULL_RANGE = 2
ENCODER_OPTIONS = {"profile": "baseline", "preset": "veryfast", "tune": "zerolatency", "g": "15"}
FRAME_STEP = 3000

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the hardware decoder needs a Windows video card")


def reference_image() -> np.ndarray[tuple[int, int], np.dtype[np.uint8]]:
    data = reference_frame()
    planes = data[data.index(FRAME_MARKER) + len(FRAME_MARKER) :]
    return np.frombuffer(planes, np.uint8).reshape(HEIGHT * 3 // 2, WIDTH)


def reference_frames() -> Iterator[VideoFrame]:
    image = reference_image()
    for index in range(FRAME_COUNT):
        yield VideoFrame.from_ndarray(np.roll(image, index * SHIFT_PIXELS_PER_FRAME, axis=1), format="yuv420p")


def reference_packets() -> list[bytes]:
    encoder = av.CodecContext.create("libx264", "w")
    assert isinstance(encoder, VideoCodecContext)
    encoder.width, encoder.height, encoder.pix_fmt = WIDTH, HEIGHT, "yuv420p"
    encoder.time_base = Fraction(1, FPS)
    encoder.framerate = Fraction(FPS)
    encoder.bit_rate = BITRATE_BPS
    encoder.color_range = FULL_RANGE
    encoder.options = ENCODER_OPTIONS
    packets = encode(reference_frames(), cast(VideoEncoder, encoder))
    return [bytes(cast(Buffer, packet)) for packet in packets]


def planes(frame: VideoFrame) -> list[bytes]:
    return [
        np.frombuffer(plane, np.uint8).reshape(-1, plane.line_size)[: plane.height, : plane.width].tobytes()
        for plane in frame.planes
    ]


@pytest.fixture
def hardware() -> Iterator[HardwareStream]:
    decoder = HardwareDecoderProcess()
    unavailable = hardware_unavailable(decoder)
    if unavailable is not None:
        decoder.close()
        pytest.skip(f"no hardware decoder on this computer: {unavailable}")
    opened = decoder.open("h264", None)
    assert not isinstance(opened, FallbackReason)
    yield opened
    decoder.close()


def hardware_unavailable(decoder: HardwareDecoderProcess) -> str | None:
    probe = decoder.open("h264", None)
    if isinstance(probe, FallbackReason):
        return probe
    data = reference_packets()[0]
    try:
        frames = probe.decode(EncodedPacket(data, 0, contains_idr(data))).frames
    except HardwareDecodeError as error:
        return error.reason
    finally:
        probe.close()
    return None if frames else "no frame decoded"


def test_hardware_frames_equal_software_frames_byte_for_byte(hardware: HardwareStream) -> None:
    software = av.CodecContext.create("h264", "r")
    hardware_frames: list[VideoFrame] = []
    software_frames: list[VideoFrame] = []
    for index, data in enumerate(reference_packets()):
        hardware_frames.extend(hardware.decode(EncodedPacket(data, index * FRAME_STEP, contains_idr(data))).frames)
        software_frames.extend(software.decode(av.Packet(data)))  # type: ignore[arg-type]

    assert len(hardware_frames) == len(software_frames) == FRAME_COUNT
    assert all(planes(a) == planes(b) for a, b in zip(hardware_frames, software_frames, strict=True))


def test_hardware_frames_keep_the_declared_range_and_matrix(hardware: HardwareStream) -> None:
    software = av.CodecContext.create("h264", "r")
    data = reference_packets()[0]

    decoded = hardware.decode(EncodedPacket(data, 0, contains_idr(data))).frames[0]
    expected = software.decode(av.Packet(data))[0]  # type: ignore[arg-type]

    assert (decoded.color_range, decoded.colorspace, decoded.key_frame) == (
        expected.color_range,
        expected.colorspace,
        expected.key_frame,
    )


def test_decoder_process_runs_above_normal_priority() -> None:
    decoder = HardwareDecoderProcess()
    try:
        opened = decoder.open("h264", None)
        if not isinstance(opened, FallbackReason):
            opened.close()
        priorities = [child.nice() for child in psutil.Process().children(recursive=True)]
    finally:
        decoder.close()

    assert ABOVE_NORMAL_PRIORITY_CLASS in priorities

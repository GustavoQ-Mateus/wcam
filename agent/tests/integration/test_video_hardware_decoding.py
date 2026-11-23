import itertools
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import cast

import av
import numpy as np
import pytest
from av import VideoFrame

from wcam.decoding.hardware import (
    HardwareDecodeError,
    HardwareDecoder,
    HardwareDecoderProcess,
    HardwareFrames,
    HardwareStream,
)
from wcam.decoding.messages import EncodedPacket
from wcam.decoding.source import SourceDecoding, software_decoding
from wcam.decoding.status import DecoderKind, DecoderStatus, DecodingSource, FallbackReason
from wcam.tools.make_test_video import Muxer, pattern_frame, write_test_video
from wcam.tools.synthetic_h264 import CodedPacket, VideoDecoder
from wcam.video.playback import ClipDecoder, DecodedFrame
from wcam.video.timeline import Clip

WIDTH = 640
HEIGHT = 360
FPS = 30
SECONDS = 2.0
FRAME_COUNT = round(FPS * SECONDS)
WORKING_PACKETS = 20
HEVC_ENCODER = "libx265"
HEVC_OPTIONS = {"x265-params": "log-level=error:keyint=30"}
FRAME_PERIOD = 1 / FPS
PERIOD_TOLERANCE = 1e-3

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="the hardware decoder needs a Windows video card")


class FailingStream:
    def __init__(self, codec: str, extradata: bytes | None) -> None:
        context = av.CodecContext.create(codec, "r")
        context.extradata = extradata
        self._software = cast(VideoDecoder, context)
        self.decoded_packets = 0

    def decode(self, packet: EncodedPacket) -> HardwareFrames:
        if self.decoded_packets >= WORKING_PACKETS:
            raise HardwareDecodeError(FallbackReason.STREAM_ERROR)
        self.decoded_packets += 1
        encoded = None
        if packet.data:
            encoded = av.Packet(packet.data)
            encoded.pts = packet.pts
        frames = self._software.decode(cast(CodedPacket | None, encoded))
        return HardwareFrames(frames, 1.0, 0.5)

    def close(self) -> None:
        pass


class FailingHardware:
    def open(self, codec: str, extradata: bytes | None) -> HardwareStream | FallbackReason:
        return FailingStream(codec, extradata)

    def close(self) -> None:
        pass


def hevc_video(path: Path) -> Path:
    with av.open(str(path), "w") as opened:
        container = cast(Muxer, opened)
        stream = container.add_stream(HEVC_ENCODER, rate=FPS, options=HEVC_OPTIONS)
        stream.width, stream.height, stream.pix_fmt = WIDTH, HEIGHT, "yuv420p"
        for index in range(FRAME_COUNT):
            frame = VideoFrame.from_ndarray(pattern_frame(WIDTH, HEIGHT, index, FRAME_COUNT), format="yuv420p")
            frame.pts = index
            container.mux(stream.encode(frame))
        container.mux(stream.encode(None))
    return path


def h264_video(path: Path) -> Path:
    write_test_video(path, WIDTH, HEIGHT, FPS, SECONDS)
    return path


def decoded_frames(path: Path, decoding: SourceDecoding) -> list[DecodedFrame]:
    decoder = ClipDecoder(path, Clip("c", "v", 0.0, SECONDS), decoding)
    decoder.start_at(0.0)
    try:
        return list(decoder.decoded())
    finally:
        decoder.close()


def planes(frame: VideoFrame) -> list[bytes]:
    return [
        np.frombuffer(plane, np.uint8).reshape(-1, plane.line_size)[: plane.height, : plane.width].tobytes()
        for plane in frame.planes
    ]


@pytest.fixture
def hardware_decoding() -> Iterator[SourceDecoding]:
    decoding = SourceDecoding("auto", DecoderStatus(DecodingSource.VIDEO), HardwareDecoderProcess)
    decoding.start()
    yield decoding
    decoding.stop()


def failing_decoding() -> SourceDecoding:
    def start_hardware() -> HardwareDecoder:
        return FailingHardware()

    decoding = SourceDecoding("auto", DecoderStatus(DecodingSource.VIDEO), start_hardware)
    decoding.start()
    return decoding


@windows_only
@pytest.mark.parametrize("write_video", [h264_video, hevc_video])
def test_library_video_frames_from_the_video_card_equal_software_byte_for_byte(
    tmp_path: Path, hardware_decoding: SourceDecoding, write_video: Callable[[Path], Path]
) -> None:
    path = write_video(tmp_path / "clip.mp4")

    hardware = decoded_frames(path, hardware_decoding)
    software = decoded_frames(path, software_decoding(DecodingSource.VIDEO))

    if not hardware or hardware[0].decoder is not DecoderKind.HARDWARE:
        pytest.skip("no hardware decoder for this video on this computer")
    assert [frame.offset_seconds for frame in hardware] == [frame.offset_seconds for frame in software]
    assert all(planes(a.frame) == planes(b.frame) for a, b in zip(hardware, software, strict=True))


def test_video_card_failing_mid_clip_resumes_in_software_without_skipping_or_repeating_frames(
    tmp_path: Path,
) -> None:
    frames = decoded_frames(h264_video(tmp_path / "clip.mp4"), failing_decoding())

    offsets = [frame.offset_seconds for frame in frames]
    steps = [later - earlier for earlier, later in itertools.pairwise(offsets)]
    assert len(frames) == FRAME_COUNT
    assert all(abs(step - FRAME_PERIOD) < PERIOD_TOLERANCE for step in steps)


def test_video_card_failing_mid_clip_marks_the_later_frames_as_software_with_the_stream_error(
    tmp_path: Path,
) -> None:
    frames = decoded_frames(h264_video(tmp_path / "clip.mp4"), failing_decoding())

    paths = {(frame.decoder, frame.reason) for frame in frames}
    assert paths == {(DecoderKind.HARDWARE, None), (DecoderKind.SOFTWARE, FallbackReason.STREAM_ERROR)}
    assert frames[-1].decoder is DecoderKind.SOFTWARE


def test_hardware_decoding_off_decodes_the_video_in_software_with_the_reason(tmp_path: Path) -> None:
    frames = decoded_frames(h264_video(tmp_path / "clip.mp4"), software_decoding(DecodingSource.VIDEO))

    assert {(frame.decoder, frame.reason) for frame in frames} == {(DecoderKind.SOFTWARE, FallbackReason.DISABLED)}

from collections.abc import Buffer
from fractions import Fraction
from typing import cast

import av
from aiortc import rtcrtpreceiver
from aiortc.codecs.vpx import Vp8Decoder
from aiortc.jitterbuffer import JitterFrame
from aiortc.rtcrtpparameters import RTCRtpCodecParameters
from av import VideoFrame
from av.video.codeccontext import VideoCodecContext

from wcam.decoding.hardware import HardwareDecodeError, HardwareDecoder, HardwareFrames, HardwareStream
from wcam.decoding.messages import EncodedPacket
from wcam.decoding.source import HardwareDecodeMode, SourceDecoding, software_reason, unused_hardware
from wcam.decoding.status import DecoderChange, DecoderKind, DecoderStatus, DecodingSource, FallbackReason
from wcam.diagnostics.stage_times import Stage
from wcam.media.phone_decoder import (
    PhoneDecoding,
    PhoneH264Decoder,
    SoftwareOnlyDecoder,
    contains_idr,
    install_phone_decoder,
)
from wcam.tools.synthetic_h264 import VideoEncoder, encode, h264_encoder, moving_frames

WIDTH = 64
HEIGHT = 48
FPS = 30
BITRATE_BPS = 500_000
FRAME_COUNT = 6
FRAME_STEP = 3000
GET_DECODER_ATTRIBUTE = "get_decoder"
LATE_SECONDS = 1.0


class FakeHardware:
    def __init__(self, open_failure: FallbackReason | None = None, failure: FallbackReason | None = None) -> None:
        self.open_failure = open_failure
        self.failure = failure
        self.packets: list[EncodedPacket] = []
        self.closed = False

    def open(self, codec: str, extradata: bytes | None) -> HardwareStream | FallbackReason:
        return self if self.open_failure is None else self.open_failure

    def decode(self, packet: EncodedPacket) -> HardwareFrames:
        self.packets.append(packet)
        if self.failure is not None:
            raise HardwareDecodeError(self.failure)
        return HardwareFrames([VideoFrame(WIDTH, HEIGHT, "yuv420p")], 4.0, 1.5)

    def close(self) -> None:
        self.closed = True


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class Recorder:
    def __init__(self) -> None:
        self.stages: list[tuple[Stage, float]] = []
        self.changes: list[DecoderChange] = []
        self.keyframe_requests = 0

    def stage(self, stage: Stage, milliseconds: float) -> None:
        self.stages.append((stage, milliseconds))

    def request_keyframe(self) -> None:
        self.keyframe_requests += 1

    def recorded(self, stage: Stage) -> list[float]:
        return [milliseconds for recorded, milliseconds in self.stages if recorded is stage]


def h264_frames() -> list[JitterFrame]:
    packets = encode(moving_frames(WIDTH, HEIGHT, FRAME_COUNT), h264_encoder(WIDTH, HEIGHT, FPS, BITRATE_BPS))
    return [JitterFrame(bytes(packet), index * FRAME_STEP) for index, packet in enumerate(packets)]  # type: ignore[arg-type]


def decoding_with(
    hardware: HardwareDecoder | None, recorder: Recorder, mode: HardwareDecodeMode = "on"
) -> PhoneDecoding:
    status = DecoderStatus(DecodingSource.PHONE)
    status.on_change(recorder.changes.append)

    def start_hardware() -> HardwareDecoder:
        if hardware is None:
            raise AssertionError("the hardware decoder must not start")
        return hardware

    source = SourceDecoding(mode, status, start_hardware, live=True)
    decoding = PhoneDecoding(source, recorder.stage)
    decoding.start_session(recorder.request_keyframe)
    return decoding


def test_idr_slice_is_found_after_the_parameter_sets() -> None:
    assert contains_idr(b"\x00\x00\x00\x01\x67\x42\x00\x00\x00\x01\x68\xce\x00\x00\x00\x01\x65\x88")


def test_non_idr_slice_is_not_a_keyframe() -> None:
    assert not contains_idr(b"\x00\x00\x00\x01\x41\x9a\x00")


def test_frames_from_the_hardware_decoder_report_hardware_with_decode_and_transfer_times() -> None:
    recorder = Recorder()
    decoder = decoding_with(FakeHardware(), recorder).create_decoder()

    frames = decoder.decode(h264_frames()[0])

    assert len(frames) == 1
    assert recorder.changes == [DecoderChange(DecodingSource.PHONE, DecoderKind.HARDWARE, None)]
    assert recorder.recorded(Stage.TRANSFER) == [1.5]
    assert len(recorder.recorded(Stage.DECODE)) == 1


def test_hardware_packet_carries_the_keyframe_flag() -> None:
    hardware = FakeHardware()
    decoder = decoding_with(hardware, Recorder()).create_decoder()

    decoder.decode(h264_frames()[0])

    assert hardware.packets[0].keyframe


def test_hardware_failing_mid_stream_falls_back_to_software_and_requests_a_keyframe() -> None:
    recorder = Recorder()
    hardware = FakeHardware(failure=FallbackReason.STREAM_ERROR)
    decoder = decoding_with(hardware, recorder).create_decoder()
    frames = h264_frames()

    lost = decoder.decode(frames[0])
    decoded = [frame for encoded in frames for frame in decoder.decode(encoded)]

    assert lost == []
    assert hardware.closed
    assert recorder.keyframe_requests == 1
    assert len(decoded) == FRAME_COUNT
    assert recorder.changes == [DecoderChange(DecodingSource.PHONE, DecoderKind.SOFTWARE, FallbackReason.STREAM_ERROR)]


def test_hardware_failing_to_open_decodes_in_software_with_the_reason() -> None:
    recorder = Recorder()
    hardware = FakeHardware(open_failure=FallbackReason.UNSUPPORTED)
    decoder = decoding_with(hardware, recorder).create_decoder()

    decoded = [frame for encoded in h264_frames() for frame in decoder.decode(encoded)]

    assert len(decoded) == FRAME_COUNT
    assert recorder.changes == [DecoderChange(DecodingSource.PHONE, DecoderKind.SOFTWARE, FallbackReason.UNSUPPORTED)]


def test_hardware_decoding_off_never_starts_the_hardware_and_reports_disabled() -> None:
    recorder = Recorder()
    decoder = decoding_with(None, recorder, mode="off").create_decoder()

    decoded = [frame for encoded in h264_frames() for frame in decoder.decode(encoded)]

    assert len(decoded) == FRAME_COUNT
    assert recorder.changes == [DecoderChange(DecodingSource.PHONE, DecoderKind.SOFTWARE, FallbackReason.DISABLED)]


def test_automatic_mode_decodes_the_live_phone_in_software_without_starting_the_video_card() -> None:
    recorder = Recorder()
    decoder = decoding_with(None, recorder, mode="auto").create_decoder()

    decoded = [frame for encoded in h264_frames() for frame in decoder.decode(encoded)]

    assert len(decoded) == FRAME_COUNT
    assert recorder.changes == [DecoderChange(DecodingSource.PHONE, DecoderKind.SOFTWARE, FallbackReason.LIVE_PHONE)]


def test_automatic_mode_keeps_the_video_card_for_the_library_video() -> None:
    assert software_reason("auto", live=False) is None


def test_frame_far_behind_the_clock_is_skipped_and_asks_for_a_keyframe() -> None:
    recorder = Recorder()
    clock = FakeClock()
    status = DecoderStatus(DecodingSource.PHONE)
    decoding = PhoneDecoding(SourceDecoding("off", status, unused_hardware), recorder.stage, clock)
    decoding.start_session(recorder.request_keyframe)
    decoder = decoding.create_decoder()
    frames = h264_frames()

    decoder.decode(frames[0])
    clock.now += LATE_SECONDS
    skipped = decoder.decode(frames[1])

    assert skipped == []
    assert recorder.keyframe_requests == 1


def test_software_frames_record_a_zero_transfer() -> None:
    recorder = Recorder()
    decoder = decoding_with(None, recorder, mode="off").create_decoder()

    for encoded in h264_frames():
        decoder.decode(encoded)

    assert recorder.recorded(Stage.TRANSFER) == [0.0] * FRAME_COUNT


def test_ending_the_session_closes_the_hardware_decoder_and_clears_the_status() -> None:
    recorder = Recorder()
    hardware = FakeHardware()
    decoding = decoding_with(hardware, recorder)
    decoding.create_decoder().decode(h264_frames()[0])

    decoding.end_session()

    assert hardware.closed
    assert decoding.status.decoder is None


def test_installed_factory_gives_h264_to_the_phone_decoder_and_keeps_vp8() -> None:
    decoding = decoding_with(None, Recorder(), mode="off")
    original = getattr(rtcrtpreceiver, GET_DECODER_ATTRIBUTE)
    install_phone_decoder(decoding)
    get_decoder = getattr(rtcrtpreceiver, GET_DECODER_ATTRIBUTE)
    try:
        h264 = get_decoder(RTCRtpCodecParameters(mimeType="video/H264", clockRate=90000, payloadType=102))
        vp8 = get_decoder(RTCRtpCodecParameters(mimeType="video/VP8", clockRate=90000, payloadType=96))
    finally:
        setattr(rtcrtpreceiver, GET_DECODER_ATTRIBUTE, original)

    assert isinstance(h264, PhoneH264Decoder)
    assert isinstance(vp8, SoftwareOnlyDecoder)


def vp8_frames() -> list[JitterFrame]:
    encoder = cast(VideoEncoder, av.CodecContext.create("libvpx", "w"))
    context = cast(VideoCodecContext, encoder)
    context.width, context.height, context.pix_fmt = WIDTH, HEIGHT, "yuv420p"
    context.time_base = Fraction(1, FPS)
    context.bit_rate = BITRATE_BPS
    packets = encode(moving_frames(WIDTH, HEIGHT, FRAME_COUNT), encoder)
    return [JitterFrame(bytes(cast(Buffer, packet)), index * FRAME_STEP) for index, packet in enumerate(packets)]


def test_vp8_session_reports_software_because_the_video_card_has_no_path_for_it() -> None:
    recorder = Recorder()
    decoder = decoding_with(FakeHardware(), recorder).software_only(Vp8Decoder())

    decoded = [frame for encoded in vp8_frames() for frame in decoder.decode(encoded)]

    assert len(decoded) == FRAME_COUNT
    assert recorder.changes == [DecoderChange(DecodingSource.PHONE, DecoderKind.SOFTWARE, FallbackReason.UNSUPPORTED)]


def test_vp8_frames_record_a_zero_transfer() -> None:
    recorder = Recorder()
    decoder = decoding_with(FakeHardware(), recorder).software_only(Vp8Decoder())

    for encoded in vp8_frames():
        decoder.decode(encoded)

    assert recorder.recorded(Stage.TRANSFER) == [0.0] * FRAME_COUNT

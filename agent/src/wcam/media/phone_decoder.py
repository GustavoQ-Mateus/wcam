import time
from collections.abc import Callable

from aiortc import codecs as aiortc_codecs
from aiortc import rtcrtpreceiver
from aiortc.codecs.base import Decoder
from aiortc.codecs.h264 import H264Decoder
from aiortc.jitterbuffer import JitterFrame
from aiortc.rtcrtpparameters import RTCRtpCodecParameters
from av.frame import Frame

from wcam.decoding.hardware import HardwareDecodeError, HardwareStream
from wcam.decoding.messages import EncodedPacket
from wcam.decoding.source import SourceDecoding
from wcam.decoding.status import DecoderKind, DecoderStatus, FallbackReason
from wcam.diagnostics.stage_times import Stage
from wcam.media.latency_limit import Clock, LatencyLimit
from wcam.process_priority import join_capture_task

H264_MIME_TYPE = "video/h264"
VIDEO_MIME_PREFIX = "video/"
H264_CODEC = "h264"
START_CODE = b"\x00\x00\x01"
NAL_TYPE_MASK = 0x1F
IDR_NAL_TYPE = 5
MILLISECONDS_PER_SECOND = 1000
PHONE_DECODER_MARK = "_wcam_phone_decoder"
GET_DECODER_ATTRIBUTE = "get_decoder"

type StageRecorder = Callable[[Stage, float], None]
type GetDecoder = Callable[[RTCRtpCodecParameters], Decoder]


class UnexpectedAiortcReceiverError(RuntimeError):
    pass


def contains_idr(data: bytes) -> bool:
    position = data.find(START_CODE)
    while position != -1 and position + len(START_CODE) < len(data):
        nal_start = position + len(START_CODE)
        if data[nal_start] & NAL_TYPE_MASK == IDR_NAL_TYPE:
            return True
        position = data.find(START_CODE, nal_start)
    return False


def elapsed_since(started: float) -> float:
    return (time.perf_counter() - started) * MILLISECONDS_PER_SECOND


class PhoneH264Decoder(Decoder):
    def __init__(
        self,
        hardware: HardwareStream | None,
        fallback_reason: FallbackReason | None,
        status: DecoderStatus,
        record_stage: StageRecorder,
        request_keyframe: Callable[[], None],
        latency: LatencyLimit,
    ) -> None:
        self._hardware = hardware
        self._fallback_reason = fallback_reason
        self._status = status
        self._record_stage = record_stage
        self._request_keyframe = request_keyframe
        self._latency = latency
        self._software = H264Decoder()

    def decode(self, encoded_frame: JitterFrame) -> list[Frame]:
        keyframe = contains_idr(encoded_frame.data)
        if not self._latency.admits(encoded_frame.timestamp, keyframe):
            return []
        if self._hardware is not None:
            return self._decoded_in_hardware(encoded_frame, self._hardware, keyframe)
        frames = self._software.decode(encoded_frame)
        for _ in frames:
            self._record_stage(Stage.TRANSFER, 0.0)
        if frames:
            self._status.report(DecoderKind.SOFTWARE, self._fallback_reason)
        return frames

    def _decoded_in_hardware(self, encoded_frame: JitterFrame, hardware: HardwareStream, keyframe: bool) -> list[Frame]:
        started = time.perf_counter()
        packet = EncodedPacket(encoded_frame.data, encoded_frame.timestamp, keyframe)
        try:
            decoded = hardware.decode(packet)
        except HardwareDecodeError as error:
            self._fall_back(hardware, error.reason)
            return []
        if not decoded.frames:
            return []
        self._record_stage(Stage.DECODE, elapsed_since(started) - decoded.transfer_milliseconds)
        self._record_stage(Stage.TRANSFER, decoded.transfer_milliseconds)
        self._status.report(DecoderKind.HARDWARE, None)
        frames: list[Frame] = [*decoded.frames]
        return frames

    def _fall_back(self, hardware: HardwareStream, reason: FallbackReason) -> None:
        self._hardware = None
        self._fallback_reason = reason
        hardware.close()
        self._request_keyframe()


class SoftwareOnlyDecoder(Decoder):
    def __init__(self, software: Decoder, status: DecoderStatus, record_stage: StageRecorder) -> None:
        self._software = software
        self._status = status
        self._record_stage = record_stage

    def decode(self, encoded_frame: JitterFrame) -> list[Frame]:
        frames = self._software.decode(encoded_frame)
        for _ in frames:
            self._record_stage(Stage.TRANSFER, 0.0)
        if frames:
            self._status.report(DecoderKind.SOFTWARE, FallbackReason.UNSUPPORTED)
        return frames


class PhoneDecoding:
    def __init__(self, source: SourceDecoding, record_stage: StageRecorder, clock: Clock = time.monotonic) -> None:
        self.status = source.status
        self._source = source
        self._record_stage = record_stage
        self._clock = clock
        self._request_keyframe: Callable[[], None] = lambda: None

    def start_session(self, request_keyframe: Callable[[], None]) -> None:
        self._request_keyframe = request_keyframe
        self._source.start()

    def end_session(self) -> None:
        self._request_keyframe = lambda: None
        self._source.stop()

    def create_decoder(self) -> Decoder:
        request_keyframe = self._request_keyframe
        latency = LatencyLimit(request_keyframe, self._clock)
        opened = self._source.open(H264_CODEC, None)
        if isinstance(opened, FallbackReason):
            return PhoneH264Decoder(None, opened, self.status, self._record_stage, request_keyframe, latency)
        return PhoneH264Decoder(opened, None, self.status, self._record_stage, request_keyframe, latency)

    def software_only(self, software: Decoder) -> Decoder:
        return SoftwareOnlyDecoder(software, self.status, self._record_stage)


def install_phone_decoder(decoding: PhoneDecoding) -> None:
    # aiortc 1.15 picks the decoder by calling the get_decoder it imported, with no option to supply one.
    original: GetDecoder = aiortc_codecs.get_decoder
    installed: GetDecoder = getattr(rtcrtpreceiver, GET_DECODER_ATTRIBUTE)
    if installed is not original and not getattr(installed, PHONE_DECODER_MARK, False):
        raise UnexpectedAiortcReceiverError("aiortc no longer picks the decoder through get_decoder")

    def get_decoder(codec: RTCRtpCodecParameters) -> Decoder:
        join_capture_task()
        mime_type = codec.mimeType.lower()
        if mime_type == H264_MIME_TYPE:
            return decoding.create_decoder()
        if mime_type.startswith(VIDEO_MIME_PREFIX):
            return decoding.software_only(original(codec))
        return original(codec)

    setattr(get_decoder, PHONE_DECODER_MARK, True)
    setattr(rtcrtpreceiver, GET_DECODER_ATTRIBUTE, get_decoder)

import threading
import time
from collections.abc import Callable
from typing import Literal

from aiortc import codecs as aiortc_codecs
from aiortc import rtcrtpreceiver
from aiortc.codecs.base import Decoder
from aiortc.codecs.h264 import H264Decoder
from aiortc.jitterbuffer import JitterFrame
from aiortc.rtcrtpparameters import RTCRtpCodecParameters
from av.frame import Frame

from wcam.decoding.hardware import HardwareDecodeError, HardwareDecoder
from wcam.decoding.messages import EncodedPacket
from wcam.decoding.status import DecoderKind, DecoderStatus, FallbackReason
from wcam.diagnostics.stage_times import Stage

H264_MIME_TYPE = "video/h264"
H264_CODEC = "h264"
START_CODE = b"\x00\x00\x01"
NAL_TYPE_MASK = 0x1F
IDR_NAL_TYPE = 5
MILLISECONDS_PER_SECOND = 1000
PHONE_DECODER_MARK = "_wcam_phone_decoder"
GET_DECODER_ATTRIBUTE = "get_decoder"

type HardwareDecodeMode = Literal["auto", "off"]
type StageRecorder = Callable[[Stage, float], None]
type HardwareFactory = Callable[[], HardwareDecoder]
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
        hardware: HardwareDecoder | None,
        fallback_reason: FallbackReason | None,
        status: DecoderStatus,
        record_stage: StageRecorder,
        request_keyframe: Callable[[], None],
    ) -> None:
        self._hardware = hardware
        self._fallback_reason = fallback_reason
        self._status = status
        self._record_stage = record_stage
        self._request_keyframe = request_keyframe
        self._software = H264Decoder()

    def decode(self, encoded_frame: JitterFrame) -> list[Frame]:
        if self._hardware is not None:
            return self._decoded_in_hardware(encoded_frame, self._hardware)
        frames = self._software.decode(encoded_frame)
        for _ in frames:
            self._record_stage(Stage.TRANSFER, 0.0)
        if frames:
            self._status.report(DecoderKind.SOFTWARE, self._fallback_reason)
        return frames

    def _decoded_in_hardware(self, encoded_frame: JitterFrame, hardware: HardwareDecoder) -> list[Frame]:
        started = time.perf_counter()
        packet = EncodedPacket(encoded_frame.data, encoded_frame.timestamp, contains_idr(encoded_frame.data))
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

    def _fall_back(self, hardware: HardwareDecoder, reason: FallbackReason) -> None:
        self._hardware = None
        self._fallback_reason = reason
        hardware.close()
        self._request_keyframe()


class PhoneDecoding:
    def __init__(
        self,
        mode: HardwareDecodeMode,
        status: DecoderStatus,
        record_stage: StageRecorder,
        start_hardware: HardwareFactory,
    ) -> None:
        self.status = status
        self._mode = mode
        self._record_stage = record_stage
        self._start_hardware = start_hardware
        self._lock = threading.Lock()
        self._prepared: HardwareDecoder | None = None
        self._owned: list[HardwareDecoder] = []
        self._request_keyframe: Callable[[], None] = lambda: None

    def start_session(self, request_keyframe: Callable[[], None]) -> None:
        with self._lock:
            self._request_keyframe = request_keyframe
            if self._mode == "off" or self._prepared is not None:
                return
            self._prepared = self._start_hardware()
            self._owned.append(self._prepared)

    def end_session(self) -> None:
        with self._lock:
            owned, self._owned, self._prepared = self._owned, [], None
            self._request_keyframe = lambda: None
        for hardware in owned:
            hardware.close()
        self.status.clear()

    def create_decoder(self) -> Decoder:
        with self._lock:
            hardware, self._prepared = self._prepared, None
            request_keyframe = self._request_keyframe
        if hardware is None:
            reason = FallbackReason.DISABLED if self._mode == "off" else FallbackReason.OPEN_FAILED
            return PhoneH264Decoder(None, reason, self.status, self._record_stage, request_keyframe)
        failure = hardware.open(H264_CODEC, None)
        if failure is not None:
            hardware.close()
            return PhoneH264Decoder(None, failure, self.status, self._record_stage, request_keyframe)
        return PhoneH264Decoder(hardware, None, self.status, self._record_stage, request_keyframe)


def install_phone_decoder(decoding: PhoneDecoding) -> None:
    # aiortc 1.15 picks the decoder by calling the get_decoder it imported, with no option to supply one.
    original: GetDecoder = aiortc_codecs.get_decoder
    installed: GetDecoder = getattr(rtcrtpreceiver, GET_DECODER_ATTRIBUTE)
    if installed is not original and not getattr(installed, PHONE_DECODER_MARK, False):
        raise UnexpectedAiortcReceiverError("aiortc no longer picks the decoder through get_decoder")

    def get_decoder(codec: RTCRtpCodecParameters) -> Decoder:
        if codec.mimeType.lower() == H264_MIME_TYPE:
            return decoding.create_decoder()
        return original(codec)

    setattr(get_decoder, PHONE_DECODER_MARK, True)
    setattr(rtcrtpreceiver, GET_DECODER_ATTRIBUTE, get_decoder)

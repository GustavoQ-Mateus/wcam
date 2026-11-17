from dataclasses import dataclass

from wcam.decoding.status import FallbackReason


@dataclass(frozen=True, slots=True)
class OpenStream:
    codec: str
    extradata: bytes | None


@dataclass(frozen=True, slots=True)
class StreamOpened:
    failure: FallbackReason | None


@dataclass(frozen=True, slots=True)
class EncodedPacket:
    data: bytes
    pts: int | None
    keyframe: bool


@dataclass(frozen=True, slots=True)
class DecodedImage:
    slot: int
    width: int
    height: int
    pts: int | None
    keyframe: bool
    color_range: int
    colorspace: int


@dataclass(frozen=True, slots=True)
class PacketDecoded:
    images: tuple[DecodedImage, ...]
    decode_milliseconds: float
    transfer_milliseconds: float


@dataclass(frozen=True, slots=True)
class DecodeFailed:
    failure: FallbackReason


type ChildRequest = OpenStream | EncodedPacket | None
type ChildReply = StreamOpened | PacketDecoded | DecodeFailed

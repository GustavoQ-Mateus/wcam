import base64
import binascii
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    TypeAdapter,
    ValidationError,
    model_validator,
)
from pydantic.alias_generators import to_camel

from wcam.media.color_correction import CameraColorSpace
from wcam.media.color_difference import RgbSpace
from wcam.media.quality_preset import QualityPreset

SNAPSHOT_CHUNK_BYTES = 45_000


class PhoneMessage(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, strict=True, frozen=True)


class SetQualityPresetMessage(PhoneMessage):
    type: Literal["set_quality_preset"]
    preset: QualityPreset


class CameraColorSpaceMessage(PhoneMessage):
    primaries: str | None = None
    transfer: str | None = None
    matrix: str | None = None
    full_range: bool | None = None

    def to_color_space(self) -> CameraColorSpace:
        return CameraColorSpace(self.primaries, self.transfer, self.matrix, self.full_range)


class CameraCapabilitiesMessage(PhoneMessage):
    type: Literal["camera_capabilities"]
    width: PositiveInt | None
    height: PositiveInt | None
    frame_rate: PositiveFloat | None
    facing_mode: Literal["user", "environment"] | None
    codecs: tuple[str, ...]
    color_space: CameraColorSpaceMessage | None = None

    def camera_color_space(self) -> CameraColorSpace | None:
        return None if self.color_space is None else self.color_space.to_color_space()


class SnapshotBeginMessage(PhoneMessage):
    type: Literal["snapshot_begin"]
    id: str
    captured_at: float
    color_space: RgbSpace
    width: PositiveInt
    height: PositiveInt
    size: PositiveInt
    chunks: PositiveInt


class ChunkMessage(PhoneMessage):
    id: str
    index: NonNegativeInt
    data: str

    @model_validator(mode="after")
    def check_data(self) -> Self:
        if len(self.data_bytes()) > SNAPSHOT_CHUNK_BYTES:
            raise ValueError("chunk is too large")
        return self

    def data_bytes(self) -> bytes:
        try:
            return base64.b64decode(self.data, validate=True)
        except binascii.Error as error:
            raise ValueError("data is not base64") from error


class SnapshotChunkMessage(ChunkMessage):
    type: Literal["snapshot_chunk"]


class ScreenshotBeginMessage(PhoneMessage):
    type: Literal["screenshot_begin"]
    id: str
    size: PositiveInt
    chunks: PositiveInt


class ScreenshotChunkMessage(ChunkMessage):
    type: Literal["screenshot_chunk"]


type AnyPhoneMessage = (
    SetQualityPresetMessage
    | CameraCapabilitiesMessage
    | SnapshotBeginMessage
    | SnapshotChunkMessage
    | ScreenshotBeginMessage
    | ScreenshotChunkMessage
)

PHONE_MESSAGE = TypeAdapter[AnyPhoneMessage](
    Annotated[
        SetQualityPresetMessage
        | CameraCapabilitiesMessage
        | SnapshotBeginMessage
        | SnapshotChunkMessage
        | ScreenshotBeginMessage
        | ScreenshotChunkMessage,
        Field(discriminator="type"),
    ]
)


def parse_phone_message(data: str | bytes) -> AnyPhoneMessage | None:
    try:
        return PHONE_MESSAGE.validate_json(data)
    except ValidationError:
        return None

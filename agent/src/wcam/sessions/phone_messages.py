import base64
import binascii
from typing import Annotated, Literal, Self

import numpy as np
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveFloat,
    PositiveInt,
    TypeAdapter,
    ValidationError,
    model_validator,
)
from pydantic.alias_generators import to_camel

from wcam.media.color_calibration import ColorSample
from wcam.media.color_difference import RgbSpace
from wcam.media.quality_preset import QualityPreset

RGB_CHANNELS = 3


class PhoneMessage(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, strict=True, frozen=True)


class SetQualityPresetMessage(PhoneMessage):
    type: Literal["set_quality_preset"]
    preset: QualityPreset


class CameraCapabilitiesMessage(PhoneMessage):
    type: Literal["camera_capabilities"]
    width: PositiveInt | None
    height: PositiveInt | None
    frame_rate: PositiveFloat | None
    facing_mode: Literal["user", "environment"] | None
    codecs: tuple[str, ...]


class ColorSampleMessage(PhoneMessage):
    type: Literal["color_sample"]
    color_space: RgbSpace
    width: PositiveInt
    height: PositiveInt
    rgb: str
    captured_at: float

    @model_validator(mode="after")
    def check_pixel_count(self) -> Self:
        if len(self.rgb_bytes()) != self.width * self.height * RGB_CHANNELS:
            raise ValueError("rgb does not hold width x height pixels")
        return self

    def rgb_bytes(self) -> bytes:
        try:
            return base64.b64decode(self.rgb, validate=True)
        except binascii.Error as error:
            raise ValueError("rgb is not base64") from error

    def to_sample(self) -> ColorSample:
        pixels = np.frombuffer(self.rgb_bytes(), dtype=np.uint8).reshape(self.height, self.width, RGB_CHANNELS)
        return ColorSample(self.color_space, pixels, self.captured_at)


type AnyPhoneMessage = SetQualityPresetMessage | CameraCapabilitiesMessage | ColorSampleMessage

PHONE_MESSAGE = TypeAdapter[AnyPhoneMessage](
    Annotated[SetQualityPresetMessage | CameraCapabilitiesMessage | ColorSampleMessage, Field(discriminator="type")]
)


def parse_phone_message(data: str | bytes) -> AnyPhoneMessage | None:
    try:
        return PHONE_MESSAGE.validate_json(data)
    except ValidationError:
        return None

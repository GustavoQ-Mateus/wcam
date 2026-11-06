from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveFloat, PositiveInt, TypeAdapter, ValidationError
from pydantic.alias_generators import to_camel

from wcam.media.quality_preset import QualityPreset


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


PHONE_MESSAGE = TypeAdapter[SetQualityPresetMessage | CameraCapabilitiesMessage](
    Annotated[SetQualityPresetMessage | CameraCapabilitiesMessage, Field(discriminator="type")]
)


def parse_phone_message(data: str | bytes) -> SetQualityPresetMessage | CameraCapabilitiesMessage | None:
    try:
        return PHONE_MESSAGE.validate_json(data)
    except ValidationError:
        return None

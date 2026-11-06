from enum import StrEnum


class QualityPreset(StrEnum):
    MAXIMUM = "maximum"
    BALANCED = "balanced"
    LIGHT = "light"

    @property
    def max_bitrate_bps(self) -> int:
        return MAX_BITRATE_BPS[self]


MAX_BITRATE_BPS = {
    QualityPreset.MAXIMUM: 20_000_000,
    QualityPreset.BALANCED: 10_000_000,
    QualityPreset.LIGHT: 5_000_000,
}
DEFAULT_QUALITY_PRESET = QualityPreset.BALANCED

import base64
import json
from dataclasses import dataclass
from pathlib import Path

from wcam.media.color_calibration import IDENTITY_TABLE, ColorSample, ColorTables, SampleMatch, decoded_planes

SAMPLE_FILE = "color-sample-{number}.json"
CALIBRATION_FILE = "color-calibration.json"


@dataclass(frozen=True, slots=True)
class TracedSample:
    sample: ColorSample
    received_at_ms: float
    state: str
    match: SampleMatch | None


class ColorTrace:
    def __init__(self, folder: Path) -> None:
        self._folder = folder
        self._samples = 0

    def record_sample(self, traced: TracedSample) -> None:
        self._folder.mkdir(parents=True, exist_ok=True)
        self._samples += 1
        path = self._folder / SAMPLE_FILE.format(number=self._samples)
        path.write_text(json.dumps(sample_record(traced), indent=2), encoding="utf-8")

    def record_calibration(
        self,
        state: str,
        delta_e: float | None,
        range_tables: ColorTables | None,
        applied_tables: ColorTables | None,
    ) -> None:
        self._folder.mkdir(parents=True, exist_ok=True)
        record = {
            "state": state,
            "deltaE": delta_e,
            "rangeTables": plane_tables(range_tables),
            "appliedTables": plane_tables(applied_tables),
        }
        (self._folder / CALIBRATION_FILE).write_text(json.dumps(record, indent=2), encoding="utf-8")


def plane_tables(tables: ColorTables | None) -> dict[str, list[int]]:
    luma, chroma = tables or (IDENTITY_TABLE, IDENTITY_TABLE)
    return {"y": list(luma), "u": list(chroma), "v": list(chroma)}


def sample_record(traced: TracedSample) -> dict[str, object]:
    sample = traced.sample
    match = traced.match
    record: dict[str, object] = {
        "colorSpace": sample.color_space.value,
        "width": sample.width,
        "height": sample.height,
        "rgb": encoded(sample.pixels.tobytes()),
        "capturedAt": sample.captured_at,
        "receivedAt": traced.received_at_ms,
        "calibrationState": traced.state,
        "correlation": None if match is None else round(match.correlation, 4),
        "mirrored": None if match is None else match.mirrored,
        "colorRange": None if match is None else match.frame.color_range.value,
        "matchedFrame": None,
    }
    if match is not None:
        luma, blue, red = decoded_planes(match.frame)
        record["matchedFrame"] = {
            "y": encoded(luma.tobytes()),
            "u": encoded(blue.tobytes()),
            "v": encoded(red.tobytes()),
        }
    return record


def encoded(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")

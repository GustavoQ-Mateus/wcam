from wcam.api.schemas import CamelModel, iso_utc
from wcam.media.comparison_report import GRID_COLUMNS, GRID_ROWS, ImageDifference
from wcam.sessions.comparisons import (
    CalibrationSnapshot,
    Comparison,
    PcSnapshot,
    PhoneSnapshot,
    ScreenDifference,
    ScreenSnapshot,
)


class ComparisonCreatedResponse(CamelModel):
    id: str


class PhoneImageBody(CamelModel):
    captured_at: str
    color_space: str
    width: int
    height: int


class PcImageBody(CamelModel):
    received_at: str
    width: int
    height: int


class ScreenImageBody(CamelModel):
    received_at: str
    width: int
    height: int
    color_space: str


class ColorTablesBody(CamelModel):
    y: list[int]
    u: list[int]
    v: list[int]


class ComparisonCalibrationBody(CamelModel):
    state: str
    delta_e: float | None
    tables: ColorTablesBody


class DeltaEBody(CamelModel):
    mean: float
    median: float
    p90: float


class GridBody(CamelModel):
    columns: int
    rows: int
    delta_e2000: list[float]


class DifferenceBody(CamelModel):
    capture_gap_ms: int | None
    correlation: float
    mirrored: bool
    delta_e2000: DeltaEBody
    delta_l: float
    chroma_ratio: float | None
    hue_shift_degrees: float | None
    grid: GridBody


class ScreenDifferenceBody(CamelModel):
    phone: DifferenceBody
    pc: DifferenceBody


class ComparisonResponse(CamelModel):
    id: str
    state: str
    reason: str | None
    requested_at: str
    phone: PhoneImageBody | None
    pc: PcImageBody | None
    calibration: ComparisonCalibrationBody
    difference: DifferenceBody | None
    screen: ScreenImageBody | None
    screen_difference: ScreenDifferenceBody | None


def comparison_response(comparison: Comparison) -> ComparisonResponse:
    difference = comparison.difference
    screen_difference = comparison.screen_difference
    return ComparisonResponse(
        id=comparison.id,
        state=comparison.state,
        reason=comparison.reason,
        requested_at=iso_utc(comparison.requested_at),
        phone=None if comparison.phone is None else phone_body(comparison.phone),
        pc=None if comparison.pc is None else pc_body(comparison.pc),
        calibration=calibration_body(comparison.calibration),
        difference=None if difference is None else difference_body(difference, comparison.capture_gap_ms),
        screen=None if comparison.screen is None else screen_body(comparison.screen),
        screen_difference=None if screen_difference is None else screen_difference_body(screen_difference),
    )


def phone_body(phone: PhoneSnapshot) -> PhoneImageBody:
    return PhoneImageBody(
        captured_at=iso_utc(phone.captured_at),
        color_space=phone.color_space,
        width=phone.width,
        height=phone.height,
    )


def pc_body(pc: PcSnapshot) -> PcImageBody:
    return PcImageBody(received_at=iso_utc(pc.received_at), width=pc.width, height=pc.height)


def screen_body(screen: ScreenSnapshot) -> ScreenImageBody:
    return ScreenImageBody(
        received_at=iso_utc(screen.received_at),
        width=screen.width,
        height=screen.height,
        color_space=screen.color_space,
    )


def calibration_body(calibration: CalibrationSnapshot) -> ComparisonCalibrationBody:
    chroma = list(calibration.chroma_table)
    tables = ColorTablesBody(y=list(calibration.luma_table), u=chroma, v=chroma)
    return ComparisonCalibrationBody(state=calibration.state, delta_e=calibration.delta_e, tables=tables)


def difference_body(difference: ImageDifference, capture_gap_ms: int | None) -> DifferenceBody:
    return DifferenceBody(
        capture_gap_ms=capture_gap_ms,
        correlation=difference.correlation,
        mirrored=difference.mirrored,
        delta_e2000=DeltaEBody(
            mean=difference.delta_e_mean,
            median=difference.delta_e_median,
            p90=difference.delta_e_p90,
        ),
        delta_l=difference.delta_l,
        chroma_ratio=difference.chroma_ratio,
        hue_shift_degrees=difference.hue_shift_degrees,
        grid=GridBody(columns=GRID_COLUMNS, rows=GRID_ROWS, delta_e2000=list(difference.grid)),
    )


def screen_difference_body(difference: ScreenDifference) -> ScreenDifferenceBody:
    return ScreenDifferenceBody(phone=difference_body(difference.phone, None), pc=difference_body(difference.pc, None))

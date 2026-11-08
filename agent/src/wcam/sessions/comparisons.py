import asyncio
import logging
import secrets
from collections import OrderedDict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from wcam.clock import Clock, utc_now
from wcam.errors import AgentError
from wcam.media.color_difference import RgbSpace
from wcam.media.comparison_report import DecodedImage, ImageDifference, decoded_png, image_difference
from wcam.media.screen_alignment import aligned_screen, png_color_space
from wcam.sessions.phone_messages import (
    SNAPSHOT_CHUNK_BYTES,
    ScreenshotBeginMessage,
    ScreenshotChunkMessage,
    SnapshotBeginMessage,
    SnapshotChunkMessage,
)

MAX_COMPARISONS = 5
DEADLINE_SECONDS = 10.0
MAX_IMAGE_BYTES = 20 * 1024 * 1024
ID_BYTES = 8
MILLISECONDS = 1000
IGNORED_SNAPSHOT = "Ignored a phone snapshot that matches no pending comparison"
IGNORED_SCREENSHOT = "Ignored a phone screenshot that is incomplete, invalid or matches no comparison"

logger = logging.getLogger(__name__)


class ComparisonState(StrEnum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class FailureReason(StrEnum):
    PHONE_TIMEOUT = "phone_timeout"
    PHONE_INVALID = "phone_invalid"
    PC_MISSING = "pc_missing"
    SESSION_ENDED = "session_ended"


class ComparisonNotFoundError(AgentError):
    code = "comparison_not_found"


class ComparisonNotReadyError(AgentError):
    code = "comparison_not_ready"


class InvalidImageError(AgentError):
    code = "invalid_request"


@dataclass(frozen=True, slots=True)
class CalibrationSnapshot:
    state: str
    delta_e: float | None
    luma_table: bytes
    chroma_table: bytes


@dataclass(frozen=True, slots=True)
class PhoneSnapshot:
    captured_at: datetime
    color_space: RgbSpace
    width: int
    height: int
    png: bytes


@dataclass(frozen=True, slots=True)
class PcSnapshot:
    received_at: datetime
    width: int
    height: int
    png: bytes


@dataclass(frozen=True, slots=True)
class ScreenSnapshot:
    received_at: datetime
    width: int
    height: int
    color_space: RgbSpace
    png: bytes


@dataclass(frozen=True, slots=True)
class ScreenDifference:
    phone: ImageDifference
    pc: ImageDifference


@dataclass(slots=True)
class PhoneAssembly:
    begin: SnapshotBeginMessage
    parts: dict[int, bytes] = field(default_factory=dict[int, bytes])


@dataclass(slots=True)
class ScreenshotAssembly:
    begin: ScreenshotBeginMessage
    parts: dict[int, bytes] = field(default_factory=dict[int, bytes])


@dataclass(slots=True)
class Comparison:
    id: str
    requested_at: datetime
    calibration: CalibrationSnapshot
    state: ComparisonState = ComparisonState.PENDING
    reason: FailureReason | None = None
    phone: PhoneSnapshot | None = None
    pc: PcSnapshot | None = None
    difference: ImageDifference | None = None
    screen: ScreenSnapshot | None = None
    screen_difference: ScreenDifference | None = None
    assembly: PhoneAssembly | None = None
    screenshot_assembly: ScreenshotAssembly | None = None
    waiting_screen: bytes | None = None

    @property
    def capture_gap_ms(self) -> int | None:
        if self.phone is None or self.pc is None:
            return None
        return round(abs((self.phone.captured_at - self.pc.received_at).total_seconds()) * MILLISECONDS)


class ComparisonStore:
    def __init__(
        self,
        calibration: Callable[[], CalibrationSnapshot],
        clock: Clock = utc_now,
        deadline: float = DEADLINE_SECONDS,
    ) -> None:
        self._calibration = calibration
        self._clock = clock
        self._deadline = deadline
        self._comparisons: OrderedDict[str, Comparison] = OrderedDict()
        self._tasks: dict[str, set[asyncio.Task[None]]] = {}

    def create(self) -> Comparison:
        comparison = Comparison(secrets.token_hex(ID_BYTES), self._clock(), self._calibration())
        self._comparisons[comparison.id] = comparison
        self._own(comparison.id, self._expire(comparison))
        while len(self._comparisons) > MAX_COMPARISONS:
            oldest, _ = self._comparisons.popitem(last=False)
            self._cancel(oldest)
        return comparison

    def find(self, comparison_id: str) -> Comparison:
        comparison = self._comparisons.get(comparison_id)
        if comparison is None:
            raise ComparisonNotFoundError
        return comparison

    def receive_begin(self, message: SnapshotBeginMessage) -> None:
        comparison = self._pending(message.id)
        if comparison is None or comparison.phone is not None:
            logger.warning(IGNORED_SNAPSHOT)
            return
        if message.size > min(MAX_IMAGE_BYTES, message.chunks * SNAPSHOT_CHUNK_BYTES):
            self._fail(comparison, FailureReason.PHONE_INVALID)
            return
        comparison.assembly = PhoneAssembly(message)

    def receive_chunk(self, message: SnapshotChunkMessage) -> None:
        comparison = self._pending(message.id)
        assembly = None if comparison is None else comparison.assembly
        if comparison is None or assembly is None:
            logger.warning(IGNORED_SNAPSHOT)
            return
        if message.index >= assembly.begin.chunks:
            self._fail(comparison, FailureReason.PHONE_INVALID)
            return
        assembly.parts[message.index] = message.data_bytes()
        if len(assembly.parts) == assembly.begin.chunks:
            self._finish_phone(comparison, assembly)

    async def receive_pc(self, comparison_id: str, png: bytes) -> None:
        comparison = self.find(comparison_id)
        image = await decoded_upload(png)
        if comparison.state is not ComparisonState.PENDING or comparison.pc is not None:
            return
        comparison.pc = PcSnapshot(self._clock(), image.width, image.height, png)
        self._complete_when_both_arrived(comparison)

    async def receive_screen(self, comparison_id: str, png: bytes) -> None:
        comparison = self.find(comparison_id)
        if comparison.state is not ComparisonState.READY:
            raise ComparisonNotReadyError
        await self._apply_screen(comparison, png)

    def receive_screenshot_begin(self, message: ScreenshotBeginMessage) -> None:
        comparison = self._comparisons.get(message.id)
        too_large = message.size > min(MAX_IMAGE_BYTES, message.chunks * SNAPSHOT_CHUNK_BYTES)
        if comparison is None or comparison.state is ComparisonState.FAILED or too_large:
            logger.warning(IGNORED_SCREENSHOT)
            return
        comparison.screenshot_assembly = ScreenshotAssembly(message)

    def receive_screenshot_chunk(self, message: ScreenshotChunkMessage) -> None:
        comparison = self._comparisons.get(message.id)
        assembly = None if comparison is None else comparison.screenshot_assembly
        if comparison is None or assembly is None or message.index >= assembly.begin.chunks:
            logger.warning(IGNORED_SCREENSHOT)
            return
        assembly.parts[message.index] = message.data_bytes()
        if len(assembly.parts) < assembly.begin.chunks:
            return
        comparison.screenshot_assembly = None
        png = b"".join(assembly.parts[index] for index in range(assembly.begin.chunks))
        if len(png) != assembly.begin.size:
            logger.warning(IGNORED_SCREENSHOT)
            return
        self._take_screenshot(comparison, png)

    def end_session(self) -> None:
        for comparison in list(self._comparisons.values()):
            if comparison.state is ComparisonState.PENDING:
                self._fail(comparison, FailureReason.SESSION_ENDED)

    async def close(self) -> None:
        tasks = [task for owned in self._tasks.values() for task in owned]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

    def _take_screenshot(self, comparison: Comparison, png: bytes) -> None:
        if comparison.state is ComparisonState.PENDING:
            comparison.waiting_screen = png
        elif comparison.state is ComparisonState.READY:
            self._own(comparison.id, self._apply_screenshot(comparison, png))

    async def _apply_screenshot(self, comparison: Comparison, png: bytes) -> None:
        try:
            await self._apply_screen(comparison, png)
        except InvalidImageError:
            logger.warning(IGNORED_SCREENSHOT)

    async def _apply_screen(self, comparison: Comparison, png: bytes) -> None:
        phone, pc = comparison.phone, comparison.pc
        if phone is None or pc is None:
            raise ComparisonNotReadyError
        if len(png) > MAX_IMAGE_BYTES:
            raise InvalidImageError
        try:
            snapshot, difference = await asyncio.to_thread(screen_report, png, phone, pc, self._clock())
        except ValueError as error:
            raise InvalidImageError from error
        comparison.screen = snapshot
        comparison.screen_difference = difference

    def _pending(self, comparison_id: str) -> Comparison | None:
        comparison = self._comparisons.get(comparison_id)
        if comparison is None or comparison.state is not ComparisonState.PENDING:
            return None
        return comparison

    def _finish_phone(self, comparison: Comparison, assembly: PhoneAssembly) -> None:
        png = b"".join(assembly.parts[index] for index in range(assembly.begin.chunks))
        if len(png) != assembly.begin.size:
            self._fail(comparison, FailureReason.PHONE_INVALID)
            return
        begin = assembly.begin
        captured_at = datetime.fromtimestamp(begin.captured_at / MILLISECONDS, UTC)
        comparison.phone = PhoneSnapshot(captured_at, begin.color_space, begin.width, begin.height, png)
        comparison.assembly = None
        self._complete_when_both_arrived(comparison)

    def _complete_when_both_arrived(self, comparison: Comparison) -> None:
        if comparison.phone is not None and comparison.pc is not None:
            self._own(comparison.id, self._report(comparison, comparison.phone, comparison.pc))

    async def _report(self, comparison: Comparison, phone: PhoneSnapshot, pc: PcSnapshot) -> None:
        try:
            difference = await asyncio.to_thread(snapshots_difference, phone, pc)
        except ValueError:
            self._fail(comparison, FailureReason.PHONE_INVALID)
            return
        if comparison.state is not ComparisonState.PENDING:
            return
        comparison.difference = difference
        comparison.state = ComparisonState.READY
        self._cancel(comparison.id, keep=asyncio.current_task())
        waiting, comparison.waiting_screen = comparison.waiting_screen, None
        if waiting is not None:
            await self._apply_screenshot(comparison, waiting)

    async def _expire(self, comparison: Comparison) -> None:
        await asyncio.sleep(self._deadline)
        if comparison.state is not ComparisonState.PENDING or comparison.difference is not None:
            return
        if comparison.phone is None:
            reason = FailureReason.PHONE_TIMEOUT if comparison.assembly is None else FailureReason.PHONE_INVALID
            self._fail(comparison, reason)
        elif comparison.pc is None:
            self._fail(comparison, FailureReason.PC_MISSING)

    def _fail(self, comparison: Comparison, reason: FailureReason) -> None:
        comparison.state = ComparisonState.FAILED
        comparison.reason = reason
        comparison.assembly = None
        self._cancel(comparison.id, keep=asyncio.current_task())

    def _own(self, comparison_id: str, work: Coroutine[Any, Any, None]) -> None:
        task = asyncio.get_running_loop().create_task(work)
        owned = self._tasks.setdefault(comparison_id, set())
        owned.add(task)
        task.add_done_callback(owned.discard)

    def _cancel(self, comparison_id: str, keep: asyncio.Task[Any] | None = None) -> None:
        for task in self._tasks.get(comparison_id, set()):
            if task is not keep:
                task.cancel()
        if keep is None:
            self._tasks.pop(comparison_id, None)


async def decoded_upload(png: bytes) -> DecodedImage:
    if len(png) > MAX_IMAGE_BYTES:
        raise InvalidImageError
    try:
        return await asyncio.to_thread(decoded_png, png)
    except ValueError as error:
        raise InvalidImageError from error


def snapshots_difference(phone: PhoneSnapshot, pc: PcSnapshot) -> ImageDifference:
    return image_difference(decoded_png(phone.png), phone.color_space, decoded_png(pc.png), RgbSpace.SRGB)


def screen_report(
    png: bytes, phone: PhoneSnapshot, pc: PcSnapshot, received_at: datetime
) -> tuple[ScreenSnapshot, ScreenDifference]:
    screen = decoded_png(png)
    space = png_color_space(png)
    phone_image = decoded_png(phone.png)
    aligned, _ = aligned_screen(phone_image, screen)
    difference = ScreenDifference(
        phone=image_difference(aligned, space, phone_image, phone.color_space),
        pc=image_difference(aligned, space, decoded_png(pc.png), RgbSpace.SRGB),
    )
    return ScreenSnapshot(received_at, screen.width, screen.height, space, png), difference

import asyncio
import base64
import json
import logging
import struct
import zlib
from collections.abc import Callable
from typing import cast

import av
import numpy as np
import pytest
from av import VideoFrame

from tests.conftest import LAN, console_app, console_client, opened_pipeline
from tests.fakes import FakePeerFactory
from tests.unit.test_session_manager import confirm_on_both_sides, connected_manager, session_request
from tests.unit.test_video_format import live_manager
from wcam.app import create_console_app, phone_page_url
from wcam.config import Settings
from wcam.media.camera_format import CameraFormatControl
from wcam.media.color_correction import IDENTITY_TABLE
from wcam.media.color_difference import RgbSpace
from wcam.media.comparison_report import GRID_COLUMNS, GRID_ROWS, decoded_png, image_difference
from wcam.media.screen_alignment import aligned_screen, png_color_space
from wcam.process_monitor import CpuMonitor
from wcam.services import AgentServices
from wcam.sessions.comparisons import (
    MAX_COMPARISONS,
    ComparisonNotFoundError,
    ComparisonNotReadyError,
    ComparisonState,
    ComparisonStore,
    CorrectionSnapshot,
    FailureReason,
    InvalidImageError,
)
from wcam.sessions.errors import NoLiveSessionError
from wcam.sessions.manager import PHONE_IMAGE_WITHOUT_DEV_TOOLS, SessionManager, SessionRequest
from wcam.sessions.phone_messages import (
    ScreenshotBeginMessage,
    ScreenshotChunkMessage,
    SnapshotBeginMessage,
    SnapshotChunkMessage,
)
from wcam.tools.synthetic_h264 import VideoEncoder

WIDTH = 1280
HEIGHT = 720
SCREEN_WIDTH = 2556
SCREEN_HEIGHT = 1179
CHUNK_BYTES = 40_000
SHORT_DEADLINE = 0.2
SETTLE_SECONDS = 20.0
POLL_SECONDS = 0.02
CAPTURED_AT = 1793991387130.0
CAPTURE_DELAY_MS = 120.0
PC_CAPTURE_AFTER_REQUEST_MS = 200.0
MILLISECONDS = 1000
DARKER_CODES = 20
SAME_IMAGE_DELTA_E = 0.5
CORRECTION = CorrectionSnapshot("applied", "bt709", "apple", IDENTITY_TABLE, IDENTITY_TABLE)


def scene(seed: int = 3, width: int = WIDTH, height: int = HEIGHT) -> np.ndarray:
    generator = np.random.default_rng(seed)
    colors = generator.integers(30, 225, size=(6, 8, 3))
    rows, columns = np.mgrid[0:height, 0:width]
    picked = colors[rows * 6 // height, columns * 8 // width]
    shade = 0.6 + 0.4 * columns[..., None] / width
    return np.clip(picked * shade, 0, 255).astype(np.uint8)


def png_bytes(rgb: np.ndarray) -> bytes:
    context = av.CodecContext.create("png", "w")
    context.width = rgb.shape[1]
    context.height = rgb.shape[0]
    context.pix_fmt = "rgb24"
    encoder = cast(VideoEncoder, context)
    packets = encoder.encode(VideoFrame.from_ndarray(rgb, format="rgb24")) + encoder.encode()
    return b"".join(bytes(packet) for packet in packets)


def with_icc(png: bytes, profile_text: bytes) -> bytes:
    data = b"ICC Profile\x00\x00" + zlib.compress(profile_text)
    chunk = struct.pack(">I", len(data)) + b"iCCP" + data + struct.pack(">I", zlib.crc32(b"iCCP" + data))
    header_end = 8 + 8 + 13 + 4
    return png[:header_end] + chunk + png[header_end:]


def chunks_of(png: bytes) -> list[str]:
    return [base64.b64encode(png[start : start + CHUNK_BYTES]).decode() for start in range(0, len(png), CHUNK_BYTES)]


def snapshot_messages(
    comparison_id: str, png: bytes, capture_delay_ms: float | None = CAPTURE_DELAY_MS
) -> tuple[SnapshotBeginMessage, list[SnapshotChunkMessage]]:
    parts = chunks_of(png)
    begin = SnapshotBeginMessage(
        type="snapshot_begin",
        id=comparison_id,
        captured_at=CAPTURED_AT,
        capture_delay_ms=capture_delay_ms,
        color_space=RgbSpace.SRGB,
        width=WIDTH,
        height=HEIGHT,
        size=len(png),
        chunks=len(parts),
    )
    chunks = [
        SnapshotChunkMessage(type="snapshot_chunk", id=comparison_id, index=i, data=d) for i, d in enumerate(parts)
    ]
    return begin, chunks


def screenshot_messages(comparison_id: str, png: bytes) -> tuple[ScreenshotBeginMessage, list[ScreenshotChunkMessage]]:
    parts = chunks_of(png)
    begin = ScreenshotBeginMessage(type="screenshot_begin", id=comparison_id, size=len(png), chunks=len(parts))
    chunks = [
        ScreenshotChunkMessage(type="screenshot_chunk", id=comparison_id, index=index, data=data)
        for index, data in enumerate(parts)
    ]
    return begin, chunks


def screenshot_of(phone: np.ndarray, mirrored: bool = False) -> np.ndarray:
    shown = phone[:, ::-1] if mirrored else phone
    scale = min(SCREEN_WIDTH / WIDTH, SCREEN_HEIGHT / HEIGHT)
    width, height = round(WIDTH * scale), round(HEIGHT * scale)
    rows = (np.arange(height) * HEIGHT // height)[:, None]
    columns = (np.arange(width) * WIDTH // width)[None, :]
    screen = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH, 3), dtype=np.uint8)
    left = (SCREEN_WIDTH - width) // 2
    screen[:height, left : left + width] = shown[rows, columns]
    screen[1000:1120, 1200:1360] = 230
    return screen


async def wait_for(condition: Callable[[], bool]) -> None:
    async with asyncio.timeout(SETTLE_SECONDS):
        while True:
            if condition():
                return
            await asyncio.sleep(POLL_SECONDS)


def store(deadline: float = SHORT_DEADLINE) -> ComparisonStore:
    return ComparisonStore(lambda: CORRECTION, deadline=deadline)


async def ready_comparison(comparisons: ComparisonStore, phone: np.ndarray, pc: np.ndarray) -> str:
    comparison = comparisons.create()
    begin, chunks = snapshot_messages(comparison.id, png_bytes(phone))
    comparisons.receive_begin(begin)
    for chunk in reversed(chunks):
        comparisons.receive_chunk(chunk)
    await comparisons.receive_pc(comparison.id, png_bytes(pc))
    await wait_for(lambda: comparison.state is not ComparisonState.PENDING)
    return comparison.id


async def test_chunks_in_any_order_rebuild_the_phone_image_and_the_report_gets_ready() -> None:
    comparisons = store(SETTLE_SECONDS)
    phone = scene()

    comparison_id = await ready_comparison(comparisons, phone, phone)

    comparison = comparisons.find(comparison_id)
    assert comparison.state is ComparisonState.READY
    assert comparison.phone is not None
    assert np.array_equal(decoded_png(comparison.phone.png).rgb, phone)
    assert comparison.difference is not None
    assert comparison.difference.delta_e_mean < SAME_IMAGE_DELTA_E
    assert len(comparison.difference.grid) == GRID_COLUMNS * GRID_ROWS
    await comparisons.close()


async def test_missing_chunk_fails_as_invalid_phone_image_at_the_deadline() -> None:
    comparisons = store()
    comparison = comparisons.create()
    begin, chunks = snapshot_messages(comparison.id, png_bytes(scene()))
    comparisons.receive_begin(begin)
    for chunk in chunks[1:]:
        comparisons.receive_chunk(chunk)

    await wait_for(lambda: comparison.state is ComparisonState.FAILED)

    assert comparison.reason is FailureReason.PHONE_INVALID


async def test_wrong_size_fails_as_invalid_phone_image() -> None:
    comparisons = store(SETTLE_SECONDS)
    comparison = comparisons.create()
    png = png_bytes(scene())
    begin, chunks = snapshot_messages(comparison.id, png)
    comparisons.receive_begin(begin.model_copy(update={"size": len(png) - 1}))
    for chunk in chunks:
        comparisons.receive_chunk(chunk)

    assert (comparison.state, comparison.reason) == (ComparisonState.FAILED, FailureReason.PHONE_INVALID)
    await comparisons.close()


async def test_silent_phone_fails_with_phone_timeout() -> None:
    comparisons = store()
    comparison = comparisons.create()

    await wait_for(lambda: comparison.state is ComparisonState.FAILED)

    assert comparison.reason is FailureReason.PHONE_TIMEOUT


async def test_missing_pc_image_fails_with_pc_missing() -> None:
    comparisons = store()
    comparison = comparisons.create()
    begin, chunks = snapshot_messages(comparison.id, png_bytes(scene()))
    comparisons.receive_begin(begin)
    for chunk in chunks:
        comparisons.receive_chunk(chunk)

    await wait_for(lambda: comparison.state is ComparisonState.FAILED)

    assert comparison.reason is FailureReason.PC_MISSING


async def test_only_the_last_five_comparisons_are_kept() -> None:
    comparisons = store(SETTLE_SECONDS)

    created = [comparisons.create().id for _ in range(MAX_COMPARISONS + 1)]

    with pytest.raises(ComparisonNotFoundError):
        comparisons.find(created[0])
    assert all(comparisons.find(comparison_id) for comparison_id in created[1:])
    await comparisons.close()


async def test_ending_the_session_fails_pending_comparisons() -> None:
    comparisons = store(SETTLE_SECONDS)
    comparison = comparisons.create()

    comparisons.end_session()

    assert (comparison.state, comparison.reason) == (ComparisonState.FAILED, FailureReason.SESSION_ENDED)
    await comparisons.close()


async def test_pc_upload_that_is_not_png_is_rejected() -> None:
    comparisons = store(SETTLE_SECONDS)
    comparison = comparisons.create()

    with pytest.raises(InvalidImageError):
        await comparisons.receive_pc(comparison.id, b"\xff\xd8\xff\xe0 jpeg")
    await comparisons.close()


def test_report_measures_a_known_darkening() -> None:
    phone = scene()
    darker = np.clip(phone.astype(int) - DARKER_CODES, 0, 255).astype(np.uint8)

    difference = image_difference(
        decoded_png(png_bytes(phone)), RgbSpace.SRGB, decoded_png(png_bytes(darker)), RgbSpace.SRGB
    )

    assert difference.correlation > 0.99
    assert not difference.mirrored
    assert difference.delta_l < -5
    assert difference.delta_e_mean > 3
    assert difference.delta_e_p90 >= difference.delta_e_median


def test_report_finds_a_mirrored_pc_image() -> None:
    phone = decoded_png(png_bytes(scene()))
    mirrored = decoded_png(png_bytes(np.ascontiguousarray(scene()[:, ::-1])))

    difference = image_difference(phone, RgbSpace.SRGB, mirrored, RgbSpace.SRGB)

    assert difference.mirrored
    assert difference.delta_e_mean < SAME_IMAGE_DELTA_E


def test_screen_color_space_comes_from_the_icc_profile() -> None:
    png = png_bytes(scene())

    assert png_color_space(with_icc(png, b"desc Display P3 profile")) is RgbSpace.DISPLAY_P3
    assert png_color_space(with_icc(png, b"desc sRGB IEC61966-2.1")) is RgbSpace.SRGB
    assert png_color_space(png) is RgbSpace.SRGB


def test_screenshot_is_aligned_under_the_interface_and_the_mirror() -> None:
    phone = scene()

    aligned, placement = aligned_screen(
        decoded_png(png_bytes(phone)), decoded_png(png_bytes(screenshot_of(phone, True)))
    )
    difference = image_difference(aligned, RgbSpace.SRGB, decoded_png(png_bytes(phone)), RgbSpace.SRGB)

    assert placement.mirrored
    assert placement.score > 0.9
    assert difference.delta_e_mean < 1.0


async def test_screenshot_upload_needs_a_ready_comparison() -> None:
    comparisons = store(SETTLE_SECONDS)
    comparison = comparisons.create()

    with pytest.raises(ComparisonNotReadyError):
        await comparisons.receive_screen(comparison.id, png_bytes(scene()))
    await comparisons.close()


async def test_screenshot_upload_reports_against_phone_and_pc() -> None:
    comparisons = store(SETTLE_SECONDS)
    phone = scene()
    comparison_id = await ready_comparison(comparisons, phone, phone)

    await comparisons.receive_screen(comparison_id, with_icc(png_bytes(screenshot_of(phone)), b"Display P3"))

    comparison = comparisons.find(comparison_id)
    assert comparison.screen is not None
    assert comparison.screen.color_space is RgbSpace.DISPLAY_P3
    assert comparison.screen_difference is not None
    assert comparison.screen_difference.phone.correlation > 0.9
    await comparisons.close()


async def test_screen_difference_reports_the_mirror_and_correlation_of_the_alignment() -> None:
    comparisons = store(SETTLE_SECONDS)
    phone = scene()
    comparison_id = await ready_comparison(comparisons, phone, phone)
    screen_png = png_bytes(screenshot_of(phone, mirrored=True))
    _, placement = aligned_screen(decoded_png(png_bytes(phone)), decoded_png(screen_png))

    await comparisons.receive_screen(comparison_id, screen_png)

    difference = comparisons.find(comparison_id).screen_difference
    assert difference is not None
    assert (difference.phone.mirrored, difference.pc.mirrored) == (True, True)
    assert difference.phone.correlation == difference.pc.correlation == placement.score
    await comparisons.close()


async def test_capture_gap_is_measured_on_the_pc_clock() -> None:
    comparisons = store(SETTLE_SECONDS)
    comparison = comparisons.create()
    begin, chunks = snapshot_messages(comparison.id, png_bytes(scene()))
    comparisons.receive_begin(begin)
    for chunk in chunks:
        comparisons.receive_chunk(chunk)
    pc_captured_at_ms = comparison.requested_at.timestamp() * MILLISECONDS + PC_CAPTURE_AFTER_REQUEST_MS

    await comparisons.receive_pc(comparison.id, png_bytes(scene()), pc_captured_at_ms)

    assert comparison.capture_gap_ms == round(PC_CAPTURE_AFTER_REQUEST_MS - CAPTURE_DELAY_MS)
    await comparisons.close()


@pytest.mark.parametrize(
    ("capture_delay_ms", "pc_capture"), [(None, PC_CAPTURE_AFTER_REQUEST_MS), (CAPTURE_DELAY_MS, None)]
)
async def test_capture_gap_is_unknown_without_both_pc_clock_times(
    capture_delay_ms: float | None, pc_capture: float | None
) -> None:
    comparisons = store(SETTLE_SECONDS)
    comparison = comparisons.create()
    begin, chunks = snapshot_messages(comparison.id, png_bytes(scene()), capture_delay_ms)
    comparisons.receive_begin(begin)
    for chunk in chunks:
        comparisons.receive_chunk(chunk)
    pc_captured_at_ms = None if pc_capture is None else comparison.requested_at.timestamp() * MILLISECONDS + pc_capture

    await comparisons.receive_pc(comparison.id, png_bytes(scene()), pc_captured_at_ms)

    assert comparison.capture_gap_ms is None
    await comparisons.close()


async def test_screenshot_from_the_phone_waits_for_a_pending_comparison() -> None:
    comparisons = store(SETTLE_SECONDS)
    phone = scene()
    comparison = comparisons.create()
    screen_begin, screen_chunks = screenshot_messages(comparison.id, png_bytes(screenshot_of(phone)))
    comparisons.receive_screenshot_begin(screen_begin)
    for chunk in reversed(screen_chunks):
        comparisons.receive_screenshot_chunk(chunk)
    assert comparison.screen is None
    begin, chunks = snapshot_messages(comparison.id, png_bytes(phone))
    comparisons.receive_begin(begin)
    for chunk in chunks:
        comparisons.receive_chunk(chunk)

    await comparisons.receive_pc(comparison.id, png_bytes(phone))
    await wait_for(lambda: comparison.screen_difference is not None)

    assert comparison.state is ComparisonState.READY
    assert comparison.screen is not None
    await comparisons.close()


async def test_starting_a_comparison_needs_a_live_session_and_asks_the_phone() -> None:
    factory = FakePeerFactory()
    comparisons = store(SETTLE_SECONDS)
    manager = SessionManager(factory, comparisons=comparisons)
    await manager.create_session(session_request_for(manager))
    factory.last.events.on_connected()

    with pytest.raises(NoLiveSessionError):
        manager.start_comparison()
    confirm_on_both_sides(manager, factory)
    comparison_id = manager.start_comparison()

    assert factory.last.sent[-1] == {"type": "snapshot_request", "id": comparison_id}
    await comparisons.close()


async def test_phone_images_without_dev_tools_are_ignored(caplog: pytest.LogCaptureFixture) -> None:
    factory = FakePeerFactory()
    await live_manager(factory)
    begin, _ = snapshot_messages("c1", png_bytes(scene()))

    with caplog.at_level(logging.WARNING):
        factory.last.events.on_message(begin.model_dump_json(by_alias=True))

    assert PHONE_IMAGE_WITHOUT_DEV_TOOLS in caplog.text


async def test_dev_routes_are_not_found_and_status_says_so_without_dev_tools(settings: Settings) -> None:
    manager = await connected_manager(FakePeerFactory())

    async with console_client(console_app(settings, manager)) as console:
        created = await console.post("/api/dev/comparisons")
        status = (await console.get("/api/status")).json()

    assert created.status_code == 404
    assert created.json()["error"]["code"] == "not_found"
    assert status["devTools"] is False


async def test_dev_routes_report_a_comparison_with_dev_tools(settings: Settings) -> None:
    factory = FakePeerFactory()
    comparisons = store(SETTLE_SECONDS)
    manager = SessionManager(factory, comparisons=comparisons)
    await manager.create_session(session_request_for(manager))
    factory.last.events.on_connected()
    confirm_on_both_sides(manager, factory)
    pipeline = opened_pipeline()
    services = AgentServices(manager, pipeline, CpuMonitor(), CameraFormatControl(pipeline), comparisons)
    app = create_console_app(settings, services, phone_page_url(settings, LAN))
    phone = scene()

    async with console_client(app) as console:
        comparison_id = (await console.post("/api/dev/comparisons")).json()["id"]
        begin, chunks = snapshot_messages(comparison_id, png_bytes(phone))
        for message in (begin, *chunks):
            factory.last.events.on_message(json.dumps(message.model_dump(by_alias=True)))
        requested_at = comparisons.find(comparison_id).requested_at.timestamp() * MILLISECONDS
        uploaded = await console.put(
            f"/api/dev/comparisons/{comparison_id}/pc",
            params={"capturedAt": requested_at + PC_CAPTURE_AFTER_REQUEST_MS},
            content=png_bytes(phone),
        )
        await wait_for(lambda: comparisons.find(comparison_id).state is ComparisonState.READY)
        report = (await console.get(f"/api/dev/comparisons/{comparison_id}")).json()
        image = await console.get(f"/api/dev/comparisons/{comparison_id}/phone.png")
        missing = await console.get("/api/dev/comparisons/unknown")
        status = (await console.get("/api/status")).json()

    assert uploaded.status_code == 204
    assert report["state"] == "ready"
    assert report["difference"]["deltaE2000"]["mean"] < SAME_IMAGE_DELTA_E
    assert len(report["correction"]["tables"]["y"]) == 256
    assert report["correction"]["display"] == "apple"
    assert report["phone"]["colorSpace"] == "srgb"
    assert report["pc"]["capturedAt"] is not None
    assert report["difference"]["captureGapMs"] == round(PC_CAPTURE_AFTER_REQUEST_MS - CAPTURE_DELAY_MS)
    assert image.headers["content-type"] == "image/png"
    assert missing.json()["error"]["code"] == "comparison_not_found"
    assert status["devTools"] is True
    await comparisons.close()


def session_request_for(manager: SessionManager) -> SessionRequest:
    return session_request(manager.open_pairing().token)

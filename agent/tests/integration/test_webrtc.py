import asyncio
import json
import logging
import socket
import ssl
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pytest
from aiortc import RTCConfiguration, RTCDataChannel, RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.rate import RemoteBitrateEstimator
from av import VideoFrame

from tests.conftest import console_app, console_client, opened_pipeline, phone_app, phone_client, services
from wcam.app import create_servers, serve
from wcam.config import Settings
from wcam.media import peer as peer_module
from wcam.media.peer import (
    PHONE_MAX_BITRATE_BPS,
    VIDEO_JITTER_BUFFER_PACKETS,
    AiortcPeer,
    aiortc_peer_factory,
    video_bitrate_estimator,
    video_jitter_buffer_capacity,
)
from wcam.media.pipeline import FramePipeline, FrameSource
from wcam.media.sdp_filter import candidate_addresses, sha256_fingerprint
from wcam.network.certificates import load_or_create_certificate
from wcam.network.lan import LanInterface, detect_lan_interface, is_in_network
from wcam.pairing.confirmation_code import confirmation_code
from wcam.sessions.manager import MediaPeer, PeerEvents, SessionManager
from wcam.virtualcam.fake_sink import FakeSink

WIDTH = 1920
HEIGHT = 1080
WAIT_SECONDS = 20.0
POLL_SECONDS = 0.05
I420_SHAPE = (HEIGHT * 3 // 2, WIDTH)
PLACEHOLDER_DEADLINE_SECONDS = 1.0
DETAILED_FRAME_SEED = 3
AIORTC_DEFAULT_VIDEO_JITTER_PACKETS = 128
ABS_SEND_TIME_FRACTION_BITS = 18
ABS_SEND_TIME_MASK = 0xFFFFFF
SIMULATED_PACKET_BYTES = 1200
SIMULATED_PACKET_INTERVAL_MS = 2
SIMULATED_DURATION_MS = 3000
SIMULATED_SSRC = 1
FIRST_REMB_MINIMUM_SHARE = 0.9
UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


class SyntheticVideo(VideoStreamTrack):
    async def recv(self) -> VideoFrame:
        pts, time_base = await self.next_timestamp()
        frame = VideoFrame(width=WIDTH, height=HEIGHT, format="yuv420p")
        frame.pts = pts
        frame.time_base = time_base
        return frame


class DetailedVideo(VideoStreamTrack):
    def __init__(self) -> None:
        super().__init__()
        generator = np.random.default_rng(DETAILED_FRAME_SEED)
        self._image = generator.integers(0, 256, size=(HEIGHT * 3 // 2, WIDTH), dtype=np.uint8)

    async def recv(self) -> VideoFrame:
        pts, time_base = await self.next_timestamp()
        frame = VideoFrame.from_ndarray(self._image, format="yuv420p")
        frame.pts = pts
        frame.time_base = time_base
        return frame


class RecordingPeerFactory:
    def __init__(self, network: LanInterface, pipeline: FramePipeline) -> None:
        self._create = aiortc_peer_factory(network.network, pipeline)
        self.peers: list[AiortcPeer] = []

    async def __call__(self, offer_sdp: str, events: PeerEvents) -> MediaPeer:
        peer = await self._create(offer_sdp, events)
        assert isinstance(peer, AiortcPeer)
        self.peers.append(peer)
        return peer


@dataclass(slots=True)
class PhoneClient:
    connection: RTCPeerConnection
    messages: asyncio.Queue[dict[str, str]]

    async def offer(self) -> str:
        await self.connection.setLocalDescription(await self.connection.createOffer())
        return self.connection.localDescription.sdp

    async def next_state(self) -> dict[str, str]:
        return await asyncio.wait_for(self.messages.get(), WAIT_SECONDS)


@dataclass(frozen=True, slots=True)
class FlowResult:
    token: str
    answer_sdp: str
    codes_match: bool
    received_before_confirmation: int
    released_before_confirmation: int
    video_before_confirmation: object
    states: list[str]
    video_after_confirmation: dict[str, Any]
    source_before_confirmation: FrameSource
    live_frame_shape: tuple[int, ...] | None
    seconds_to_placeholder: float


@pytest.fixture
def lan() -> LanInterface:
    return detect_lan_interface(None)


@pytest.fixture
def sink() -> FakeSink:
    return FakeSink()


@pytest.fixture
async def pipeline(sink: FakeSink) -> AsyncIterator[FramePipeline]:
    running = opened_pipeline(sink)
    task = asyncio.create_task(running.run())
    yield running
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


def phone_client_peer(track: VideoStreamTrack | None = None) -> PhoneClient:
    connection = RTCPeerConnection(RTCConfiguration(iceServers=[]))
    messages: asyncio.Queue[dict[str, str]] = asyncio.Queue()
    channel: RTCDataChannel = connection.createDataChannel("control")

    def receive(data: str) -> None:
        messages.put_nowait(json.loads(data))

    channel.on("message", receive)
    connection.addTrack(track or SyntheticVideo())
    return PhoneClient(connection, messages)


async def wait_until(condition: Callable[[], bool]) -> None:
    async with asyncio.timeout(WAIT_SECONDS):
        while True:
            if condition():
                return
            await asyncio.sleep(POLL_SECONDS)


async def current_status(console: httpx.AsyncClient) -> dict[str, Any]:
    return (await console.get("/api/status")).json()


async def run_pairing_flow(
    console: httpx.AsyncClient,
    phone: httpx.AsyncClient,
    factory: RecordingPeerFactory,
    pipeline: FramePipeline,
) -> FlowResult:
    client = phone_client_peer()
    try:
        token = (await console.post("/api/pairing")).json()["url"].split("#t=")[1]
        offer_sdp = await client.offer()
        created = (await phone.post("/api/sessions", json={"token": token, "sdp": offer_sdp})).json()
        await client.connection.setRemoteDescription(RTCSessionDescription(created["sdp"], "answer"))
        states = [(await client.next_state())["state"]]
        status = await current_status(console)
        own_code = confirmation_code(
            created["confirmationNonce"],
            sha256_fingerprint(offer_sdp) or "",
            sha256_fingerprint(created["sdp"]) or "",
        )
        gate = factory.peers[0].gate
        await wait_until(lambda: gate.received > 0)
        received, released = gate.received, gate.released
        video_before = (await current_status(console))["session"]["video"]
        source_before = pipeline.source
        await console.post("/api/sessions/current/confirm")
        states.append((await client.next_state())["state"])
        video = await wait_for_video(console)
        await wait_until(lambda: pipeline.source is FrameSource.PHONE)
        sink = pipeline.sink
        live_shape = sink.last_frame.shape if isinstance(sink, FakeSink) and sink.last_frame is not None else None
        disconnected_at = time.monotonic()
        await console.delete("/api/sessions/current")
        await wait_until(lambda: pipeline.source is FrameSource.PLACEHOLDER)
        seconds_to_placeholder = time.monotonic() - disconnected_at
        states.append((await client.next_state())["state"])
        return FlowResult(
            token,
            created["sdp"],
            own_code == status["session"]["confirmationCode"],
            received,
            released,
            video_before,
            states,
            video,
            source_before,
            live_shape,
            seconds_to_placeholder,
        )
    finally:
        await client.connection.close()


async def wait_for_video(console: httpx.AsyncClient) -> dict[str, Any]:
    video: dict[str, Any] | None = None
    async with asyncio.timeout(WAIT_SECONDS):
        while video is None:
            video = (await current_status(console))["session"]["video"]
            await asyncio.sleep(POLL_SECONDS)
    return video


async def test_aiortc_phone_goes_live_only_after_confirmation(
    settings: Settings,
    lan: LanInterface,
    pipeline: FramePipeline,
) -> None:
    factory = RecordingPeerFactory(lan, pipeline)
    manager = SessionManager(factory)

    async with (
        console_client(console_app(settings, manager, pipeline)) as console,
        phone_client(phone_app(settings, manager)) as phone,
    ):
        result = await run_pairing_flow(console, phone, factory, pipeline)

    assert result.codes_match
    assert result.received_before_confirmation > 0
    assert result.released_before_confirmation == 0
    assert result.video_before_confirmation is None
    assert result.states == ["awaiting_confirmation", "live", "ended"]
    assert (result.video_after_confirmation["width"], result.video_after_confirmation["height"]) == (WIDTH, HEIGHT)
    assert factory.peers[0].gate.released > 0
    assert result.source_before_confirmation is FrameSource.PLACEHOLDER
    assert result.live_frame_shape == I420_SHAPE
    assert result.seconds_to_placeholder < PLACEHOLDER_DEADLINE_SECONDS


async def test_answer_has_only_lan_candidates(
    settings: Settings,
    lan: LanInterface,
    pipeline: FramePipeline,
) -> None:
    factory = RecordingPeerFactory(lan, pipeline)
    manager = SessionManager(factory)

    async with (
        console_client(console_app(settings, manager, pipeline)) as console,
        phone_client(phone_app(settings, manager)) as phone,
    ):
        result = await run_pairing_flow(console, phone, factory, pipeline)

    addresses = candidate_addresses(result.answer_sdp)
    assert addresses
    assert all(is_in_network(address, lan.network) for address in addresses)
    assert "typ srflx" not in result.answer_sdp
    assert "typ relay" not in result.answer_sdp


async def test_peer_connection_has_no_ice_servers(lan: LanInterface, monkeypatch: pytest.MonkeyPatch) -> None:
    configurations: list[RTCConfiguration | None] = []

    class RecordingConnection(RTCPeerConnection):
        def __init__(self, configuration: RTCConfiguration | None = None) -> None:
            configurations.append(configuration)
            super().__init__(configuration)

    monkeypatch.setattr(peer_module, "RTCPeerConnection", RecordingConnection)
    client = phone_client_peer()
    create = aiortc_peer_factory(lan.network, opened_pipeline())
    peer = await create(await client.offer(), PeerEvents(lambda: None, lambda _: None))
    await peer.close()
    await client.connection.close()

    assert len(configurations) == 1
    assert configurations[0] is not None
    assert configurations[0].iceServers == []


async def test_video_receiver_jitter_buffer_holds_large_frames(lan: LanInterface, pipeline: FramePipeline) -> None:
    client = phone_client_peer()
    factory = RecordingPeerFactory(lan, pipeline)
    await factory(await client.offer(), PeerEvents(lambda: None, lambda _: None))
    peer = factory.peers[0]

    capacities = [
        video_jitter_buffer_capacity(transceiver.receiver)
        for transceiver in peer.connection.getTransceivers()
        if transceiver.kind == "video"
    ]
    await peer.close()
    await client.connection.close()

    assert capacities == [VIDEO_JITTER_BUFFER_PACKETS]
    assert VIDEO_JITTER_BUFFER_PACKETS > AIORTC_DEFAULT_VIDEO_JITTER_PACKETS


async def test_first_remb_already_announces_the_maximum_bitrate(lan: LanInterface, pipeline: FramePipeline) -> None:
    client = phone_client_peer()
    factory = RecordingPeerFactory(lan, pipeline)
    await factory(await client.offer(), PeerEvents(lambda: None, lambda _: None))
    peer = factory.peers[0]
    receiver = next(t.receiver for t in peer.connection.getTransceivers() if t.kind == "video")

    first_remb = first_remb_for_steady_stream(video_bitrate_estimator(receiver))
    await peer.close()
    await client.connection.close()

    assert first_remb is not None
    assert first_remb >= FIRST_REMB_MINIMUM_SHARE * PHONE_MAX_BITRATE_BPS


def first_remb_for_steady_stream(estimator: RemoteBitrateEstimator) -> int | None:
    for arrival_ms in range(0, SIMULATED_DURATION_MS, SIMULATED_PACKET_INTERVAL_MS):
        abs_send_time = (arrival_ms << ABS_SEND_TIME_FRACTION_BITS) // 1000 & ABS_SEND_TIME_MASK
        remb = estimator.add(arrival_ms, abs_send_time, SIMULATED_PACKET_BYTES, SIMULATED_SSRC)
        if remb is not None:
            return remb[0]
    return None


async def test_keyframe_larger_than_aiortc_default_buffer_is_decoded(
    lan: LanInterface, pipeline: FramePipeline
) -> None:
    client = phone_client_peer(DetailedVideo())
    factory = RecordingPeerFactory(lan, pipeline)
    await factory(await client.offer(), PeerEvents(lambda: None, lambda _: None))
    peer = factory.peers[0]
    await client.connection.setRemoteDescription(RTCSessionDescription(peer.answer_sdp, "answer"))

    try:
        await wait_until(lambda: peer.gate.received > 0)
    finally:
        await peer.close()
        await client.connection.close()

    assert peer.gate.received > 0


async def test_pairing_token_never_appears_in_logs(
    tmp_path: Path,
    web_dist: Path,
    lan: LanInterface,
    pipeline: FramePipeline,
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = Settings(data_dir=tmp_path, web_dist=web_dist, console_port=free_port(), phone_port=free_port())
    factory = RecordingPeerFactory(lan, pipeline)
    manager = SessionManager(factory)
    certificate = load_or_create_certificate(tmp_path, lan.ip)
    servers = create_servers(settings, lan, certificate, services(manager, pipeline))
    capture_all_logs(caplog)
    serving = asyncio.create_task(serve(servers))
    try:
        await wait_until(lambda: all(server.started for server in servers))
        async with (
            httpx.AsyncClient(base_url=f"http://127.0.0.1:{settings.console_port}") as console,
            httpx.AsyncClient(
                base_url=f"https://{lan.ip}:{settings.phone_port}", verify=trusting(certificate.certificate_path)
            ) as phone,
        ):
            result = await run_pairing_flow(console, phone, factory, pipeline)
    finally:
        for server in servers:
            server.should_exit = True
        await serving

    assert "POST /api/sessions" in caplog.text
    assert result.token not in caplog.text


def capture_all_logs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    for name in UVICORN_LOGGERS:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(caplog.handler)


def trusting(certificate_path: Path) -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certificate_path)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
        return port

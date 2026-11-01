import asyncio
import json
import logging
import socket
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pytest
from aiortc import RTCConfiguration, RTCDataChannel, RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame

from tests.conftest import console_app, console_client, phone_app, phone_client
from wcam.app import create_servers, serve
from wcam.config import Settings
from wcam.media import peer as peer_module
from wcam.media.peer import AiortcPeer, aiortc_peer_factory
from wcam.media.sdp_filter import candidate_addresses, sha256_fingerprint
from wcam.network.certificates import load_or_create_certificate
from wcam.network.lan import LanInterface, detect_lan_interface, is_in_network
from wcam.pairing.confirmation_code import confirmation_code
from wcam.sessions.manager import MediaPeer, PeerEvents, SessionManager

WIDTH = 1920
HEIGHT = 1080
WAIT_SECONDS = 20.0
POLL_SECONDS = 0.05
UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


class SyntheticVideo(VideoStreamTrack):
    async def recv(self) -> VideoFrame:
        pts, time_base = await self.next_timestamp()
        frame = VideoFrame(width=WIDTH, height=HEIGHT, format="yuv420p")
        frame.pts = pts
        frame.time_base = time_base
        return frame


class RecordingPeerFactory:
    def __init__(self, network: LanInterface) -> None:
        self._create = aiortc_peer_factory(network.network)
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


@pytest.fixture
def lan() -> LanInterface:
    return detect_lan_interface(None)


def phone_client_peer() -> PhoneClient:
    connection = RTCPeerConnection(RTCConfiguration(iceServers=[]))
    messages: asyncio.Queue[dict[str, str]] = asyncio.Queue()
    channel: RTCDataChannel = connection.createDataChannel("control")

    def receive(data: str) -> None:
        messages.put_nowait(json.loads(data))

    channel.on("message", receive)
    connection.addTrack(SyntheticVideo())
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
        await console.post("/api/sessions/current/confirm")
        states.append((await client.next_state())["state"])
        video = await wait_for_video(console)
        await console.delete("/api/sessions/current")
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


async def test_aiortc_phone_goes_live_only_after_confirmation(settings: Settings, lan: LanInterface) -> None:
    factory = RecordingPeerFactory(lan)
    manager = SessionManager(factory)

    async with (
        console_client(console_app(settings, manager)) as console,
        phone_client(phone_app(settings, manager)) as phone,
    ):
        result = await run_pairing_flow(console, phone, factory)

    assert result.codes_match
    assert result.received_before_confirmation > 0
    assert result.released_before_confirmation == 0
    assert result.video_before_confirmation is None
    assert result.states == ["awaiting_confirmation", "live", "ended"]
    assert (result.video_after_confirmation["width"], result.video_after_confirmation["height"]) == (WIDTH, HEIGHT)
    assert factory.peers[0].gate.released > 0


async def test_answer_has_only_lan_candidates(settings: Settings, lan: LanInterface) -> None:
    factory = RecordingPeerFactory(lan)
    manager = SessionManager(factory)

    async with (
        console_client(console_app(settings, manager)) as console,
        phone_client(phone_app(settings, manager)) as phone,
    ):
        result = await run_pairing_flow(console, phone, factory)

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
    peer = await aiortc_peer_factory(lan.network)(await client.offer(), PeerEvents(lambda: None, lambda _: None))
    await peer.close()
    await client.connection.close()

    assert len(configurations) == 1
    assert configurations[0] is not None
    assert configurations[0].iceServers == []


async def test_pairing_token_never_appears_in_logs(
    tmp_path: Path,
    web_dist: Path,
    lan: LanInterface,
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = Settings(data_dir=tmp_path, web_dist=web_dist, console_port=free_port(), phone_port=free_port())
    factory = RecordingPeerFactory(lan)
    manager = SessionManager(factory)
    certificate = load_or_create_certificate(tmp_path, lan.ip)
    servers = create_servers(settings, lan, certificate, manager)
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
            result = await run_pairing_flow(console, phone, factory)
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

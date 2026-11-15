import asyncio
import itertools
import json
import logging
import time
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import cast

import pytest
from aiortc import (
    MediaStreamTrack,
    RTCConfiguration,
    RTCPeerConnection,
    RTCRtpSender,
    RTCRtpTransceiver,
    RTCSessionDescription,
)
from aiortc.rtp import RtpPacket, is_rtcp
from av import VideoFrame
from av.packet import Packet
from av.video.stream import VideoStream

from tests.conftest import opened_pipeline
from tests.integration.test_webrtc import wait_until
from wcam.media import peer as peer_module
from wcam.media.episodes import EPISODE_LOGGER, open_episode_log
from wcam.media.peer import AiortcPeer, aiortc_peer_factory, video_jitter_buffer
from wcam.media.pipeline import FramePipeline
from wcam.network.lan import LanInterface, detect_lan_interface
from wcam.sessions.manager import PeerEvents
from wcam.tools.synthetic_h264 import CodedPacket, encode, h264_encoder, moving_frames

WIDTH = 1920
HEIGHT = 1080
FPS = 30
WIRE_BITRATE_BPS = 5_000_000
WIRE_BITRATE_TOLERANCE = 0.1
ENCODER_BITRATE_BPS = 4_100_000
CLIP_FRAMES = 150
WARMUP_FRAMES = 60
OBSERVE_SECONDS = 6.0
WAIT_SECONDS = 20.0
RECOVERY_DISABLED_SECONDS = 3600.0
RECOVERY_DEADLINE_SECONDS = 1.0
STALL_WITHOUT_RECOVERY_SECONDS = 1.0
H264_RTX = ("video/H264", "video/rtx")
SEQUENCE_NUMBER_BYTES = 2
BITS_PER_BYTE = 8


@pytest.fixture(scope="module")
def clip() -> list[CodedPacket]:
    return encode(moving_frames(WIDTH, HEIGHT, CLIP_FRAMES), h264_encoder(WIDTH, HEIGHT, FPS, ENCODER_BITRATE_BPS))


class PreEncodedVideo(MediaStreamTrack):
    kind = "video"

    def __init__(self, clip: list[CodedPacket]) -> None:
        super().__init__()
        self._clip = clip
        self._sent = 0
        self._position = 0
        self._started_at: float | None = None

    def request_keyframe(self) -> None:
        self._position = 0

    async def recv(self) -> "Packet[VideoStream]":
        await self._pace()
        packet = self._clip[self._position]
        packet.pts = self._sent
        packet.time_base = Fraction(1, FPS)
        self._sent += 1
        self._position = (self._position + 1) % len(self._clip)
        return cast("Packet[VideoStream]", packet)

    async def _pace(self) -> None:
        now = time.monotonic()
        if self._started_at is None:
            self._started_at = now
        await asyncio.sleep(max(0.0, self._started_at + self._sent / FPS - now))


@dataclass(slots=True)
class PacketDropper:
    armed: bool = False
    media_ssrc: int | None = None
    dropped_sequence: int | None = None
    dropped: list[str] = field(default_factory=list[str])
    armed_media_bytes: int = 0

    def keeps(self, data: bytes) -> bool:
        if is_rtcp(data):
            return True
        packet = RtpPacket.parse(data)
        if self.media_ssrc is None:
            self.media_ssrc = packet.ssrc
        if packet.ssrc == self.media_ssrc:
            return self._keeps_media(packet)
        return self._keeps_retransmission(packet)

    def _keeps_media(self, packet: RtpPacket) -> bool:
        if self.armed:
            self.armed_media_bytes += len(packet.payload)
        if self.armed and self.dropped_sequence is None:
            self.dropped_sequence = packet.sequence_number
        if packet.sequence_number != self.dropped_sequence:
            return True
        self.dropped.append("original")
        return False

    def _keeps_retransmission(self, packet: RtpPacket) -> bool:
        original = int.from_bytes(packet.payload[:SEQUENCE_NUMBER_BYTES])
        if original != self.dropped_sequence:
            return True
        self.dropped.append("retransmission")
        return False


class RecordingPipeline(FramePipeline):
    def __init__(self) -> None:
        pipeline = opened_pipeline()
        super().__init__(pipeline.sink)
        self.submitted_at: list[float] = []

    def submit(self, frame: VideoFrame) -> None:
        self.submitted_at.append(time.monotonic())
        super().submit(frame)


@dataclass(frozen=True, slots=True)
class StallMeasurement:
    longest_gap_seconds: float
    dropped: list[str]
    bitrate_bps: float
    stalls: int
    keyframe_requests: int


def phone_sender(clip: list[CodedPacket]) -> tuple[RTCPeerConnection, RTCRtpTransceiver, PreEncodedVideo]:
    connection = RTCPeerConnection(RTCConfiguration(iceServers=[]))
    connection.createDataChannel("control")
    track = PreEncodedVideo(clip)
    transceiver = connection.addTransceiver(track, direction="sendonly")
    capabilities = RTCRtpSender.getCapabilities("video")
    transceiver.setCodecPreferences([codec for codec in capabilities.codecs if codec.mimeType in H264_RTX])
    setattr(transceiver.sender, "_send_keyframe", track.request_keyframe)  # noqa: B010
    return connection, transceiver, track


def drop_through(transceiver: RTCRtpTransceiver, dropper: PacketDropper) -> None:
    transport = transceiver.sender.transport
    send: Callable[[bytes], Awaitable[None]] = transport._send_rtp  # pyright: ignore[reportPrivateUsage]

    async def send_unless_dropped(data: bytes) -> None:
        if dropper.keeps(data):
            await send(data)

    setattr(transport, "_send_rtp", send_unless_dropped)  # noqa: B010


async def measure_stall(lan: LanInterface, clip: list[CodedPacket]) -> StallMeasurement:
    pipeline = RecordingPipeline()
    delivering = asyncio.create_task(pipeline.run())
    channel_open = asyncio.Event()
    events = PeerEvents(channel_open.set, lambda _: None, lambda _: None)
    connection, transceiver, _ = phone_sender(clip)
    peer = await aiortc_peer_factory(lan.network, pipeline)(await offer(connection), events)
    assert isinstance(peer, AiortcPeer)
    try:
        await connection.setRemoteDescription(RTCSessionDescription(peer.answer_sdp, "answer"))
        await asyncio.wait_for(channel_open.wait(), WAIT_SECONDS)
        await wait_until(lambda: peer.gate.received > 0)
        peer.open_gate()
        dropper = PacketDropper()
        drop_through(transceiver, dropper)
        await wait_until(lambda: len(pipeline.submitted_at) >= WARMUP_FRAMES)
        armed_at = time.monotonic()
        dropper.armed = True
        await asyncio.sleep(OBSERVE_SECONDS)
        observed_bytes = dropper.armed_media_bytes
        observed_seconds = time.monotonic() - armed_at
        receiver = next(t.receiver for t in peer.connection.getTransceivers() if t.kind == "video")
        buffer = video_jitter_buffer(receiver)
    finally:
        await peer.close()
        await connection.close()
        delivering.cancel()
        await asyncio.gather(delivering, return_exceptions=True)
    bitrate = observed_bytes * BITS_PER_BYTE / observed_seconds
    return StallMeasurement(
        longest_gap_after(pipeline.submitted_at, armed_at),
        dropper.dropped,
        bitrate,
        buffer.stalls,
        buffer.keyframe_requests,
    )


async def offer(connection: RTCPeerConnection) -> str:
    await connection.setLocalDescription(await connection.createOffer())
    return connection.localDescription.sdp


def longest_gap_after(moments: list[float], start: float) -> float:
    relevant = [start, *(moment for moment in moments if moment > start)]
    return max(later - earlier for earlier, later in itertools.pairwise(relevant))


@pytest.fixture
def lan() -> LanInterface:
    return detect_lan_interface(None)


@pytest.fixture
def episode_log(tmp_path: Path) -> Iterator[Path]:
    handler = open_episode_log(tmp_path)
    yield Path(handler.baseFilename)
    logging.getLogger(EPISODE_LOGGER).removeHandler(handler)
    handler.close()


async def test_video_returns_within_one_second_after_losing_a_packet_and_its_retransmission(
    lan: LanInterface,
    clip: list[CodedPacket],
) -> None:
    measurement = await measure_stall(lan, clip)

    assert measurement.dropped[:2] == ["original", "retransmission"]
    assert measurement.bitrate_bps == pytest.approx(WIRE_BITRATE_BPS, rel=WIRE_BITRATE_TOLERANCE)
    assert measurement.stalls == 1
    assert measurement.keyframe_requests >= 1
    assert measurement.longest_gap_seconds <= RECOVERY_DEADLINE_SECONDS


async def test_aiortc_buffer_alone_still_stalls_on_a_lost_packet(
    lan: LanInterface,
    clip: list[CodedPacket],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(peer_module, "STALLED_BUFFER_SECONDS", RECOVERY_DISABLED_SECONDS)

    measurement = await measure_stall(lan, clip)

    assert measurement.dropped[:2] == ["original", "retransmission"]
    assert measurement.stalls == 0
    assert measurement.longest_gap_seconds > STALL_WITHOUT_RECOVERY_SECONDS


async def test_recovered_stall_is_logged_as_one_episode_without_addresses(
    lan: LanInterface,
    clip: list[CodedPacket],
    episode_log: Path,
) -> None:
    await measure_stall(lan, clip)

    content = read_log(episode_log)
    episodes = [json.loads(line) for line in content.splitlines()]
    assert len(episodes) == 1
    assert (episodes[0]["cause"], episodes[0]["action"]) == ("stalled", "frozen")
    assert episodes[0]["pliSent"] >= 1
    assert episodes[0]["rtpBytes"] > 0
    assert str(lan.ip) not in content
    assert "#t=" not in content
    assert "https://" not in content


def read_log(path: Path) -> str:
    return path.read_text(encoding="utf-8")

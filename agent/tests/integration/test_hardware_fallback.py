import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import cast

import av
import pytest
from aiortc import RTCSessionDescription

from tests.integration.test_stall_recovery import RecordingPipeline, offer, phone_sender
from tests.integration.test_webrtc import wait_until
from wcam.decoding.hardware import HardwareDecodeError, HardwareDecoder, HardwareFrames
from wcam.decoding.messages import EncodedPacket
from wcam.decoding.status import DecoderChange, DecoderKind, DecoderStatus, DecodingSource, FallbackReason
from wcam.media.peer import AiortcPeer, aiortc_peer_factory
from wcam.media.phone_decoder import PhoneDecoding
from wcam.network.lan import LanInterface, detect_lan_interface
from wcam.sessions.manager import PeerEvents
from wcam.tools.synthetic_h264 import CodedPacket, VideoDecoder, encode, h264_encoder, moving_frames

WIDTH = 640
HEIGHT = 360
FPS = 30
BITRATE_BPS = 1_000_000
CLIP_FRAMES = 90
WORKING_PACKETS = 20
FRAMES_AFTER_FAILURE = 20
WAIT_SECONDS = 20.0

type DecoderPath = tuple[DecoderKind, FallbackReason | None]


class FailingHardware:
    def __init__(self) -> None:
        self._software = cast(VideoDecoder, av.CodecContext.create("h264", "r"))
        self.decoded_packets = 0
        self.closed = False

    def open(self, codec: str, extradata: bytes | None) -> FallbackReason | None:
        return None

    def decode(self, packet: EncodedPacket) -> HardwareFrames:
        if self.decoded_packets >= WORKING_PACKETS:
            raise HardwareDecodeError(FallbackReason.STREAM_ERROR)
        self.decoded_packets += 1
        frames = self._software.decode(cast(CodedPacket, av.Packet(packet.data)))
        return HardwareFrames(frames, 1.0, 0.5)

    def close(self) -> None:
        self.closed = True


@dataclass(slots=True)
class FailingSession:
    hardware: FailingHardware = field(default_factory=FailingHardware)
    pipeline: RecordingPipeline = field(default_factory=RecordingPipeline)
    changes: list[tuple[DecoderKind, FallbackReason | None]] = field(
        default_factory=list[tuple[DecoderKind, FallbackReason | None]]
    )
    keyframe_requests: int = 0

    def start_hardware(self) -> HardwareDecoder:
        return self.hardware

    def record(self, change: DecoderChange) -> None:
        self.changes.append((change.decoder, change.reason))


async def run_until(lan: LanInterface, session: FailingSession, done: Callable[[], bool]) -> None:
    status = DecoderStatus(DecodingSource.PHONE)
    status.on_change(session.record)
    decoding = PhoneDecoding("auto", status, lambda _stage, _milliseconds: None, session.start_hardware)
    delivering = asyncio.create_task(session.pipeline.run())
    channel_open = asyncio.Event()
    events = PeerEvents(channel_open.set, lambda _: None, lambda _: None)
    clip = encode(moving_frames(WIDTH, HEIGHT, CLIP_FRAMES), h264_encoder(WIDTH, HEIGHT, FPS, BITRATE_BPS))
    connection, transceiver, track = phone_sender(clip)

    def phone_sends_keyframe() -> None:
        session.keyframe_requests += 1
        track.request_keyframe()

    setattr(transceiver.sender, "_send_keyframe", phone_sends_keyframe)  # noqa: B010
    peer = await aiortc_peer_factory(lan.network, session.pipeline, decoding)(await offer(connection), events)
    assert isinstance(peer, AiortcPeer)
    try:
        await connection.setRemoteDescription(RTCSessionDescription(peer.answer_sdp, "answer"))
        await asyncio.wait_for(channel_open.wait(), WAIT_SECONDS)
        await wait_until(lambda: peer.gate.received > 0)
        peer.open_gate()
        await wait_until(lambda: session.hardware.closed)
        await wait_until(done)
    finally:
        await peer.close()
        await connection.close()
        delivering.cancel()
        await asyncio.gather(delivering, return_exceptions=True)


@pytest.fixture
def lan() -> LanInterface:
    return detect_lan_interface(None)


async def test_video_card_failing_mid_stream_keeps_the_video_coming_in_software(lan: LanInterface) -> None:
    session = FailingSession()
    frames_at_failure: list[int] = []

    def frames_after_failure() -> bool:
        frames_at_failure[:] = frames_at_failure or [len(session.pipeline.submitted_at)]
        return len(session.pipeline.submitted_at) >= frames_at_failure[0] + FRAMES_AFTER_FAILURE

    await run_until(lan, session, frames_after_failure)

    assert session.hardware.decoded_packets == WORKING_PACKETS


async def test_video_card_failing_mid_stream_asks_the_phone_for_a_keyframe(lan: LanInterface) -> None:
    session = FailingSession()

    await run_until(lan, session, lambda: session.keyframe_requests > 0)

    assert session.keyframe_requests > 0


async def test_video_card_failing_mid_stream_reports_software_with_the_stream_error(lan: LanInterface) -> None:
    session = FailingSession()

    await run_until(lan, session, lambda: len(session.changes) == 2)

    assert session.changes == [(DecoderKind.HARDWARE, None), (DecoderKind.SOFTWARE, FallbackReason.STREAM_ERROR)]

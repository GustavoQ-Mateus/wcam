import asyncio
import json
from dataclasses import replace
from ipaddress import IPv4Network
from typing import Protocol, cast

from aiortc import MediaStreamTrack, RTCConfiguration, RTCDataChannel, RTCPeerConnection, RTCSessionDescription
from aiortc.jitterbuffer import JitterBuffer
from aiortc.mediastreams import MediaStreamError
from aiortc.rtcrtpreceiver import RTCRtpReceiver
from aiortc.stats import RTCTransportStats
from av import VideoFrame

from wcam.media.frame_gate import FrameGate
from wcam.media.metrics import VideoMeter, VideoStats
from wcam.media.pipeline import FramePipeline
from wcam.media.sdp_filter import keep_candidates_in_network, video_codec
from wcam.sessions.manager import EndReason, MediaPeer, PeerEvents, PeerFactory

CONTROL_CHANNEL = "control"
CLOSE_FLUSH_SECONDS = 0.2
VIDEO_JITTER_BUFFER_PACKETS = 2048
AIORTC_JITTER_BUFFER_ATTRIBUTE = "_RTCRtpReceiver__jitter_buffer"


class FrameSource(Protocol):
    async def recv(self) -> object: ...


def peer_configuration() -> RTCConfiguration:
    return RTCConfiguration(iceServers=[])


class AiortcPeer:
    def __init__(
        self,
        connection: RTCPeerConnection,
        network: IPv4Network,
        pipeline: FramePipeline,
        events: PeerEvents,
    ) -> None:
        self._connection = connection
        self._network = network
        self._pipeline = pipeline
        self._events = events
        self._channel: RTCDataChannel | None = None
        self._frame_task: asyncio.Task[None] | None = None
        self._answer_sdp = ""
        self.gate = FrameGate()
        self._meter = VideoMeter()

    @property
    def connection(self) -> RTCPeerConnection:
        return self._connection

    @property
    def answer_sdp(self) -> str:
        return self._answer_sdp

    @property
    def video(self) -> VideoStats | None:
        stats = self._meter.stats
        if stats is None:
            return None
        return replace(stats, codec=video_codec(self._answer_sdp), frames_scaled=self._pipeline.frames_scaled)

    async def answer(self, offer_sdp: str) -> None:
        self._connection.on("datachannel", self._handle_channel)
        self._connection.on("track", self._handle_track)
        self._connection.on("connectionstatechange", self._handle_connection_state)
        offer = RTCSessionDescription(keep_candidates_in_network(offer_sdp, self._network), "offer")
        await self._connection.setRemoteDescription(offer)
        enlarge_video_jitter_buffers(self._connection)
        await self._connection.setLocalDescription(await self._connection.createAnswer())
        self._answer_sdp = keep_candidates_in_network(self._connection.localDescription.sdp, self._network)

    def open_gate(self) -> None:
        self._pipeline.start_phone()
        self.gate.open()

    def send(self, message: dict[str, str]) -> None:
        if self._channel is not None and self._channel.readyState == "open":
            self._channel.send(json.dumps(message))

    async def close(self) -> None:
        if self.gate.is_open:
            self._pipeline.stop_phone()
        if self._frame_task is not None:
            self._frame_task.cancel()
            await asyncio.gather(self._frame_task, return_exceptions=True)
        if self._channel is not None and self._channel.readyState == "open":
            await asyncio.sleep(CLOSE_FLUSH_SECONDS)
        await self._connection.close()

    def _handle_channel(self, channel: RTCDataChannel) -> None:
        if channel.label != CONTROL_CHANNEL:
            return
        self._channel = channel
        channel.on("close", lambda: self._events.on_lost(EndReason.DISCONNECTED_BY_PHONE))
        self._events.on_connected()

    def _handle_track(self, track: MediaStreamTrack) -> None:
        if track.kind != "video" or self._frame_task is not None:
            return
        receiver = next(receiver for receiver in self._connection.getReceivers() if receiver.track is track)
        self._frame_task = asyncio.get_running_loop().create_task(self._consume_frames(track, receiver))

    def _handle_connection_state(self) -> None:
        state = self._connection.connectionState
        if state == "failed":
            self._events.on_lost(EndReason.CONNECTION_FAILED)
        elif state == "closed":
            self._events.on_lost(EndReason.DISCONNECTED_BY_PHONE)

    async def _consume_frames(self, track: FrameSource, receiver: RTCRtpReceiver) -> None:
        loop = asyncio.get_running_loop()
        while True:
            try:
                frame = await track.recv()
            except MediaStreamError:
                return
            if not self.gate.admit() or not isinstance(frame, VideoFrame):
                continue
            self._pipeline.submit(frame)
            self._meter.record_frame(loop.time(), frame.width, frame.height, await bytes_received(receiver))


def enlarge_video_jitter_buffers(connection: RTCPeerConnection) -> None:
    # aiortc 1.15 fixes the video jitter buffer at 128 packets and has no option for it; a detailed 1080p
    # keyframe needs more, so it would never be assembled.
    for transceiver in connection.getTransceivers():
        if transceiver.kind == "video":
            buffer = JitterBuffer(capacity=VIDEO_JITTER_BUFFER_PACKETS, is_video=True)
            setattr(transceiver.receiver, AIORTC_JITTER_BUFFER_ATTRIBUTE, buffer)


def video_jitter_buffer_capacity(receiver: RTCRtpReceiver) -> int:
    buffer: JitterBuffer = getattr(receiver, AIORTC_JITTER_BUFFER_ATTRIBUTE)
    return buffer.capacity


async def bytes_received(receiver: RTCRtpReceiver) -> int:
    report = cast(dict[str, object], await receiver.getStats())
    return sum(stats.bytesReceived for stats in report.values() if isinstance(stats, RTCTransportStats))


def aiortc_peer_factory(network: IPv4Network, pipeline: FramePipeline) -> PeerFactory:
    async def create(offer_sdp: str, events: PeerEvents) -> MediaPeer:
        peer = AiortcPeer(RTCPeerConnection(configuration=peer_configuration()), network, pipeline, events)
        try:
            await peer.answer(offer_sdp)
        except Exception:
            await peer.close()
            raise
        return peer

    return create

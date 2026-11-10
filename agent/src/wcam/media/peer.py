import asyncio
import json
import logging
import socket
from dataclasses import replace
from ipaddress import IPv4Network
from typing import Protocol, cast

from aiortc import MediaStreamTrack, RTCConfiguration, RTCDataChannel, RTCPeerConnection, RTCSessionDescription
from aiortc.clock import current_ms
from aiortc.mediastreams import MediaStreamError
from aiortc.rate import AimdRateControl, BandwidthUsage, RemoteBitrateEstimator
from aiortc.rtcrtpreceiver import RTCRtpReceiver
from aiortc.stats import RTCTransportStats
from av import VideoFrame

from wcam.media.color_correction import ColorCorrection
from wcam.media.episodes import EpisodeTracker, LinkSample, write_episode
from wcam.media.frame_gate import FrameGate
from wcam.media.metrics import VideoMeter, VideoStats
from wcam.media.pipeline import FramePipeline
from wcam.media.pipeline import FrameSource as OutputSource
from wcam.media.quality_preset import DEFAULT_QUALITY_PRESET
from wcam.media.recovering_jitter_buffer import STALLED_SECONDS, RecoveringJitterBuffer
from wcam.media.sdp_filter import keep_candidates_in_network, video_codec
from wcam.sessions.manager import EndReason, MediaPeer, PeerEvents, PeerFactory

CONTROL_CHANNEL = "control"
CLOSE_FLUSH_SECONDS = 0.2
EPISODE_SAMPLE_SECONDS = 0.1
VIDEO_JITTER_BUFFER_PACKETS = 2048
STALLED_BUFFER_SECONDS = STALLED_SECONDS
AIORTC_JITTER_BUFFER_ATTRIBUTE = "_RTCRtpReceiver__jitter_buffer"
AIORTC_BITRATE_ESTIMATOR_ATTRIBUTE = "_RTCRtpReceiver__remote_bitrate_estimator"
ICE_RECEIVE_BUFFER_BYTES = 4 * 1024 * 1024
AIORTC_ICE_CONNECTION_ATTRIBUTE = "_connection"
AIOICE_PROTOCOLS_ATTRIBUTE = "_protocols"
SOCKET_EXTRA_INFO = "socket"
ICE_SOCKETS_UNREACHABLE = (
    "ICE sockets are not reachable in this aiortc version; receive buffers keep the system default"
)

logger = logging.getLogger(__name__)


class FrameSource(Protocol):
    async def recv(self) -> object: ...


class CappedRateControl(AimdRateControl):
    def __init__(self, max_bitrate_bps: int) -> None:
        super().__init__()
        self.max_bitrate_bps = max_bitrate_bps
        self.set_estimate(max_bitrate_bps, current_ms())

    def limit(self, max_bitrate_bps: int) -> None:
        self.max_bitrate_bps = max_bitrate_bps
        self.set_estimate(max_bitrate_bps, current_ms())

    def update(
        self,
        bandwidth_usage: BandwidthUsage,
        estimated_throughput: int | None,
        now_ms: int,
    ) -> int | None:
        if super().update(bandwidth_usage, estimated_throughput, now_ms) is None:
            return None
        self.current_bitrate = min(self.current_bitrate, self.max_bitrate_bps)
        return self.current_bitrate


class StunProtocol(Protocol):
    transport: asyncio.DatagramTransport


class IceSocket(Protocol):
    def fileno(self) -> int: ...

    def setsockopt(self, level: int, option: int, value: int, /) -> None: ...

    def getsockopt(self, level: int, option: int, /) -> int: ...


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
        self._jitter_buffers: list[RecoveringJitterBuffer] = []
        self._episodes = EpisodeTracker(write_episode)
        self._episode_task: asyncio.Task[None] | None = None
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
        return replace(
            stats,
            codec=video_codec(self._answer_sdp),
            frames_scaled=self._pipeline.frames_scaled,
            color_range=self._pipeline.color_range,
            color_matrix=self._pipeline.color_matrix,
            color_correction=self._pipeline.color_correction,
        )

    async def answer(self, offer_sdp: str) -> None:
        self._connection.on("datachannel", self._handle_channel)
        self._connection.on("track", self._handle_track)
        self._connection.on("connectionstatechange", self._handle_connection_state)
        offer = RTCSessionDescription(keep_candidates_in_network(offer_sdp, self._network), "offer")
        await self._connection.setRemoteDescription(offer)
        self._jitter_buffers = install_recovering_jitter_buffers(self._connection)
        cap_video_estimate(self._connection, DEFAULT_QUALITY_PRESET.max_bitrate_bps)
        await self._connection.setLocalDescription(await self._connection.createAnswer())
        enlarge_ice_receive_buffers(self._connection)
        self._answer_sdp = keep_candidates_in_network(self._connection.localDescription.sdp, self._network)

    def open_gate(self) -> None:
        self._pipeline.start_phone()
        self.gate.open()
        self._episode_task = asyncio.get_running_loop().create_task(self._watch_episodes())

    def limit_bitrate(self, max_bitrate_bps: int) -> None:
        cap_video_estimate(self._connection, max_bitrate_bps)

    def set_color_correction(self, correction: ColorCorrection) -> None:
        self._pipeline.color_correction = correction

    def send(self, message: dict[str, str]) -> None:
        if self._channel is not None and self._channel.readyState == "open":
            self._channel.send(json.dumps(message))

    async def close(self) -> None:
        await self._stop_watching_episodes()
        if self.gate.is_open:
            self._pipeline.stop_phone()
        if self._frame_task is not None:
            self._frame_task.cancel()
            await asyncio.gather(self._frame_task, return_exceptions=True)
        if self._channel is not None and self._channel.readyState == "open":
            await asyncio.sleep(CLOSE_FLUSH_SECONDS)
        await self._connection.close()

    async def _watch_episodes(self) -> None:
        while True:
            await asyncio.sleep(EPISODE_SAMPLE_SECONDS)
            sample = self._link_sample()
            if sample is not None:
                self._episodes.observe(sample)

    async def _stop_watching_episodes(self) -> None:
        if self._episode_task is None:
            return
        self._episode_task.cancel()
        await asyncio.gather(self._episode_task, return_exceptions=True)
        sample = self._link_sample()
        if sample is not None:
            self._episodes.finish(sample)

    def _link_sample(self) -> LinkSample | None:
        frame_age = self._pipeline.phone_frame_age()
        if frame_age is None:
            return None
        return LinkSample(
            at=asyncio.get_running_loop().time(),
            frame_age=frame_age,
            portrait=self._pipeline.portrait,
            black=self._pipeline.source is OutputSource.PLACEHOLDER,
            rtp_bytes=sum(buffer.received_bytes for buffer in self._jitter_buffers),
            keyframe_requests=sum(buffer.keyframe_requests for buffer in self._jitter_buffers),
            stalls=sum(buffer.stalls for buffer in self._jitter_buffers),
        )

    def _handle_channel(self, channel: RTCDataChannel) -> None:
        if channel.label != CONTROL_CHANNEL:
            return
        self._channel = channel
        channel.on("close", lambda: self._events.on_lost(EndReason.DISCONNECTED_BY_PHONE))
        channel.on("message", self._events.on_message)
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

    def _admits_after_recovery(self, frame: VideoFrame) -> bool:
        return all(buffer.admits_decoded(frame.key_frame) for buffer in self._jitter_buffers)

    async def _consume_frames(self, track: FrameSource, receiver: RTCRtpReceiver) -> None:
        loop = asyncio.get_running_loop()
        while True:
            try:
                frame = await track.recv()
            except MediaStreamError:
                return
            if not isinstance(frame, VideoFrame) or not self._admits_after_recovery(frame):
                continue
            if not self.gate.admit():
                continue
            self._pipeline.submit(frame)
            self._meter.record_frame(loop.time(), frame.width, frame.height, await bytes_received(receiver))


def install_recovering_jitter_buffers(connection: RTCPeerConnection) -> list[RecoveringJitterBuffer]:
    # aiortc 1.15 fixes the video jitter buffer at 128 packets and has no option for it; a detailed 1080p
    # keyframe needs more, so it would never be assembled.
    buffers: list[RecoveringJitterBuffer] = []
    for transceiver in connection.getTransceivers():
        if transceiver.kind == "video":
            buffer = RecoveringJitterBuffer(VIDEO_JITTER_BUFFER_PACKETS, STALLED_BUFFER_SECONDS)
            setattr(transceiver.receiver, AIORTC_JITTER_BUFFER_ATTRIBUTE, buffer)
            buffers.append(buffer)
    return buffers


def cap_video_estimate(connection: RTCPeerConnection, max_bitrate_bps: int) -> None:
    # aiortc starts its REMB from the first measured throughput, grows it 8% per second and has no ceiling, which
    # keeps the phone near 0.5 Mbit/s for the first minute; it starts at the ceiling and congestion lowers it.
    for transceiver in connection.getTransceivers():
        if transceiver.kind != "video":
            continue
        estimator = video_bitrate_estimator(transceiver.receiver)
        if isinstance(estimator.rate_control, CappedRateControl):
            estimator.rate_control.limit(max_bitrate_bps)
        else:
            estimator.rate_control = CappedRateControl(max_bitrate_bps)


def video_bitrate_estimator(receiver: RTCRtpReceiver) -> RemoteBitrateEstimator:
    estimator: RemoteBitrateEstimator = getattr(receiver, AIORTC_BITRATE_ESTIMATOR_ATTRIBUTE)
    return estimator


def video_jitter_buffer(receiver: RTCRtpReceiver) -> RecoveringJitterBuffer:
    buffer: RecoveringJitterBuffer = getattr(receiver, AIORTC_JITTER_BUFFER_ATTRIBUTE)
    return buffer


def enlarge_ice_receive_buffers(connection: RTCPeerConnection) -> None:
    # Windows gives each UDP socket 64 KB, about 50 video packets, so a burst from the phone would be dropped.
    for ice_socket in ice_sockets(connection):
        ice_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, ICE_RECEIVE_BUFFER_BYTES)


def ice_sockets(connection: RTCPeerConnection) -> list[IceSocket]:
    found: dict[int, IceSocket] = {}
    try:
        for gatherer in ice_gatherers(connection):
            aioice_connection = getattr(gatherer, AIORTC_ICE_CONNECTION_ATTRIBUTE)
            protocols = cast(list[StunProtocol], getattr(aioice_connection, AIOICE_PROTOCOLS_ATTRIBUTE))
            for protocol in protocols:
                ice_socket = cast(IceSocket, protocol.transport.get_extra_info(SOCKET_EXTRA_INFO))
                found[ice_socket.fileno()] = ice_socket
    except AttributeError:
        logger.warning(ICE_SOCKETS_UNREACHABLE)
        return []
    return list(found.values())


def ice_gatherers(connection: RTCPeerConnection) -> list[object]:
    transports = [transceiver.receiver.transport for transceiver in connection.getTransceivers()]
    if connection.sctp is not None:
        transports.append(connection.sctp.transport)
    return [transport.transport.iceGatherer for transport in transports]


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

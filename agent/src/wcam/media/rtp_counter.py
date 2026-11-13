import logging
from collections.abc import Awaitable, Callable

from aiortc import RTCPeerConnection
from aiortc.rtp import RtpPacket

AIORTC_RTP_HANDLER_ATTRIBUTE = "_handle_rtp_packet"
VIDEO_BEFORE_LIVE = "Video packets arrived from the phone before both sides confirmed the code"

type RtpHandler = Callable[..., Awaitable[None]]

logger = logging.getLogger(__name__)


class RtpPacketCounter:
    def __init__(self) -> None:
        self.before_live = 0
        self._counting = True

    def stop(self) -> None:
        self._counting = False

    def record(self) -> None:
        if not self._counting:
            return
        if self.before_live == 0:
            logger.warning(VIDEO_BEFORE_LIVE)
        self.before_live += 1


def count_video_packets(connection: RTCPeerConnection, counter: RtpPacketCounter) -> None:
    # aiortc hands each routed RTP packet to its receiver here, before the jitter buffer and the decoder.
    for transceiver in connection.getTransceivers():
        if transceiver.kind != "video":
            continue
        receiver = transceiver.receiver
        handler: RtpHandler = getattr(receiver, AIORTC_RTP_HANDLER_ATTRIBUTE)
        setattr(receiver, AIORTC_RTP_HANDLER_ATTRIBUTE, counting_handler(handler, counter))


def counting_handler(handler: RtpHandler, counter: RtpPacketCounter) -> RtpHandler:
    async def handle(packet: RtpPacket, arrival_time_ms: int) -> None:
        counter.record()
        await handler(packet, arrival_time_ms=arrival_time_ms)

    return handle

from datetime import UTC, datetime, timedelta

from wcam.media.color_calibration import ColorSample
from wcam.media.metrics import VideoStats
from wcam.sessions.manager import MediaPeer, PeerEvents

START = datetime(2026, 11, 1, 18, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self) -> None:
        self.now = START

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta) -> None:
        self.now += delta


AGENT_FINGERPRINT = ":".join(["CD"] * 32)
PHONE_FINGERPRINT = ":".join(["AB"] * 32)
OFFER_SDP = "\r\n".join(
    [
        "v=0",
        "m=video 9 UDP/TLS/RTP/SAVPF 96",
        f"a=fingerprint:sha-256 {PHONE_FINGERPRINT}",
        "a=candidate:1 1 udp 2122260223 192.168.0.23 50000 typ host",
        "m=application 9 UDP/DTLS/SCTP webrtc-datachannel",
        "",
    ]
)


class FakePeer:
    def __init__(self, events: PeerEvents) -> None:
        self.events = events
        self.sent: list[dict[str, str]] = []
        self.gate_open = False
        self.closed = False
        self.video: VideoStats | None = None
        self.max_bitrate_bps: int | None = None
        self.color_samples: list[ColorSample] = []
        self.color_calibration_restarts = 0

    @property
    def answer_sdp(self) -> str:
        return f"v=0\r\na=fingerprint:sha-256 {AGENT_FINGERPRINT}\r\n"

    def open_gate(self) -> None:
        self.gate_open = True

    def limit_bitrate(self, max_bitrate_bps: int) -> None:
        self.max_bitrate_bps = max_bitrate_bps

    def add_color_sample(self, sample: ColorSample) -> None:
        self.color_samples.append(sample)

    def restart_color_calibration(self) -> None:
        self.color_calibration_restarts += 1

    def send(self, message: dict[str, str]) -> None:
        self.sent.append(message)

    async def close(self) -> None:
        self.closed = True


class FakePeerFactory:
    def __init__(self) -> None:
        self.peers: list[FakePeer] = []

    async def __call__(self, offer_sdp: str, events: PeerEvents) -> MediaPeer:
        peer = FakePeer(events)
        self.peers.append(peer)
        return peer

    @property
    def last(self) -> FakePeer:
        return self.peers[-1]

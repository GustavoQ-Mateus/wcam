from ipaddress import IPv4Network

from wcam.media.frame_gate import FrameGate
from wcam.media.metrics import VideoMeter, VideoStats
from wcam.media.sdp_filter import (
    candidate_addresses,
    is_publishable_offer,
    keep_candidates_in_network,
    sha256_fingerprint,
)

LAN_NETWORK = IPv4Network("192.168.0.0/24")
FINGERPRINT = ":".join(["ab"] * 32)
OFFER = "\r\n".join(
    [
        "v=0",
        "o=- 1 2 IN IP4 127.0.0.1",
        "s=-",
        "t=0 0",
        "m=video 9 UDP/TLS/RTP/SAVPF 96",
        "c=IN IP4 0.0.0.0",
        f"a=fingerprint:sha-256 {FINGERPRINT}",
        "a=candidate:1 1 udp 2122260223 192.168.0.23 50000 typ host",
        "a=candidate:2 1 udp 2122194687 172.24.48.1 50001 typ host",
        "a=candidate:3 1 udp 2122129151 4f1c2d3e-0000-4000-8000-000000000000.local 50002 typ host",
        "a=candidate:4 1 udp 1686052607 203.0.113.9 50003 typ srflx raddr 192.168.0.23 rport 50000",
        "a=candidate:5 1 udp 2122063615 fe80::1 50004 typ host",
        "a=end-of-candidates",
        "m=application 9 UDP/DTLS/SCTP webrtc-datachannel",
        "c=IN IP4 0.0.0.0",
        "a=candidate:1 1 udp 2122260223 192.168.0.23 50000 typ host",
        "",
    ]
)


def test_offer_candidates_outside_subnet_are_removed() -> None:
    filtered = keep_candidates_in_network(OFFER, LAN_NETWORK)

    assert candidate_addresses(filtered) == ["192.168.0.23", "192.168.0.23"]
    assert "a=end-of-candidates" in filtered


def test_fingerprint_is_read_in_upper_case() -> None:
    assert sha256_fingerprint(OFFER) == FINGERPRINT.upper()


def test_offer_with_video_and_data_channel_is_publishable() -> None:
    assert is_publishable_offer(OFFER)


def test_offer_without_data_channel_is_not_publishable() -> None:
    video_only = OFFER.split("m=application")[0]

    assert not is_publishable_offer(video_only)


def test_unreadable_offer_is_not_publishable() -> None:
    assert not is_publishable_offer("not an sdp")


def test_frames_do_not_pass_gate_before_confirmation() -> None:
    gate = FrameGate()

    admitted = [gate.admit() for _ in range(3)]

    assert admitted == [False, False, False]
    assert (gate.received, gate.released) == (3, 0)


def test_frames_pass_gate_after_confirmation() -> None:
    gate = FrameGate()
    gate.admit()

    gate.open()

    assert gate.admit()
    assert (gate.received, gate.released) == (2, 1)


def test_meter_reports_resolution_from_first_frame() -> None:
    meter = VideoMeter()

    meter.record_frame(10.0, 1920, 1080, 0)

    assert meter.stats == VideoStats(1920, 1080, 0.0, 0)


def test_meter_reports_fps_and_bitrate_of_last_second() -> None:
    meter = VideoMeter()
    frame_interval = 1 / 30
    bytes_per_frame = 40_000

    for index in range(31):
        meter.record_frame(10.0 + index * frame_interval, 1920, 1080, index * bytes_per_frame)

    assert meter.stats == VideoStats(1920, 1080, 30.0, 9600)

from aiortc.jitterbuffer import JitterBuffer, JitterFrame
from aiortc.rtp import RtpPacket

from wcam.media.recovering_jitter_buffer import STALLED_SECONDS, RecoveringJitterBuffer

CAPACITY = 64
FRAME_STEP = 3000
PAYLOAD = b"payload"


class SteppingClock:
    def __init__(self) -> None:
        self.now = 10.0

    def __call__(self) -> float:
        return self.now


def rtp(sequence_number: int, frame_index: int) -> RtpPacket:
    packet = RtpPacket(sequence_number=sequence_number, timestamp=frame_index * FRAME_STEP, payload=PAYLOAD)
    setattr(packet, "_data", PAYLOAD)  # noqa: B010
    return packet


def frames_from(buffer: JitterBuffer, packets: list[RtpPacket]) -> list[tuple[bool, JitterFrame | None]]:
    return [buffer.add(packet) for packet in packets]


def stalled_buffer() -> tuple[RecoveringJitterBuffer, SteppingClock]:
    clock = SteppingClock()
    buffer = RecoveringJitterBuffer(CAPACITY, clock=clock)
    frames_from(buffer, [rtp(0, 0), rtp(1, 1), rtp(3, 2), rtp(4, 3), rtp(5, 3), rtp(6, 4)])
    return buffer, clock


def test_complete_frames_pass_through_as_in_aiortc() -> None:
    buffer = RecoveringJitterBuffer(CAPACITY, clock=SteppingClock())

    results = frames_from(buffer, [rtp(0, 0), rtp(1, 0), rtp(2, 1)])

    assert [request for request, _ in results] == [False, False, False]
    frame = results[-1][1]
    assert frame is not None
    assert (frame.timestamp, frame.data) == (0, PAYLOAD * 2)
    assert buffer.stalls == 0


def test_missing_packet_holds_frames_until_half_a_second() -> None:
    buffer, clock = stalled_buffer()

    clock.now += STALLED_SECONDS - 0.01
    request, frame = buffer.add(rtp(7, 4))

    assert (request, frame) == (False, None)
    assert buffer.stalls == 0


def test_stalled_buffer_skips_to_the_next_whole_frame_and_asks_for_a_keyframe() -> None:
    buffer, clock = stalled_buffer()

    clock.now += STALLED_SECONDS + 0.01
    request, frame = buffer.add(rtp(7, 4))

    assert request
    assert frame is not None
    assert (frame.timestamp, frame.data) == (3 * FRAME_STEP, PAYLOAD * 2)
    assert (buffer.stalls, buffer.keyframe_requests, buffer.awaiting_keyframe) == (1, 1, True)


def test_plain_aiortc_buffer_stays_stalled_on_the_same_packets() -> None:
    buffer = JitterBuffer(CAPACITY, is_video=True)

    results = frames_from(buffer, [rtp(0, 0), rtp(1, 1), rtp(3, 2), rtp(4, 3), rtp(5, 3), rtp(6, 4), rtp(7, 4)])

    assert [frame.timestamp for _, frame in results if frame is not None] == [0]


def test_decoded_frames_wait_for_a_keyframe_after_recovery() -> None:
    buffer, clock = stalled_buffer()
    clock.now += STALLED_SECONDS + 0.01
    buffer.add(rtp(7, 4))

    assert not buffer.admits_decoded(is_keyframe=False)
    assert buffer.admits_decoded(is_keyframe=True)
    assert buffer.admits_decoded(is_keyframe=False)
    assert not buffer.awaiting_keyframe


def test_keyframe_is_asked_again_every_half_second_until_it_arrives() -> None:
    buffer, clock = stalled_buffer()
    clock.now += STALLED_SECONDS + 0.01
    buffer.add(rtp(7, 4))

    clock.now += STALLED_SECONDS + 0.01
    request, frame = buffer.add(rtp(8, 5))

    assert request
    assert frame is not None
    assert (buffer.stalls, buffer.keyframe_requests) == (1, 2)


def test_received_payload_bytes_are_counted() -> None:
    buffer = RecoveringJitterBuffer(CAPACITY, clock=SteppingClock())

    frames_from(buffer, [rtp(0, 0), rtp(1, 0)])

    assert buffer.received_bytes == 2 * len(PAYLOAD)

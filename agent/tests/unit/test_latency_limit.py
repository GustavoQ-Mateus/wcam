from collections import deque
from dataclasses import dataclass

from wcam.media.latency_limit import MAX_LAG_SECONDS, RTP_CLOCK_RATE, RTP_TIMESTAMP_MODULUS, LatencyLimit

FPS = 30
FRAME_SECONDS = 1 / FPS
FRAME_STEP = RTP_CLOCK_RATE // FPS
SLOW_DECODE_SECONDS = 0.040
KEYFRAME_ANSWER_SECONDS = 0.1
SIMULATED_SECONDS = 20.0
QUEUE_BOUND = round((MAX_LAG_SECONDS + KEYFRAME_ANSWER_SECONDS + SLOW_DECODE_SECONDS) * FPS) + 1
JITTER_SECONDS = 0.15
LASTING_NETWORK_DELAY_SECONDS = 0.5


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@dataclass(slots=True)
class Phone:
    keyframe_asked_at: float | None = None

    def ask_keyframe(self, now: float) -> None:
        self.keyframe_asked_at = now

    def sends_keyframe(self, index: int, sent_at: float) -> bool:
        if index == 0:
            return True
        if self.keyframe_asked_at is None or sent_at < self.keyframe_asked_at + KEYFRAME_ANSWER_SECONDS:
            return False
        self.keyframe_asked_at = None
        return True


def longest_queue_with_slow_decoding() -> int:
    clock = FakeClock()
    phone = Phone()
    limit = LatencyLimit(lambda: phone.ask_keyframe(clock.now), clock)
    queue: deque[tuple[int, bool]] = deque()
    next_index = 0
    longest = 0
    while clock.now < SIMULATED_SECONDS:
        if not queue:
            clock.now = max(clock.now, next_index * FRAME_SECONDS)
        while next_index * FRAME_SECONDS <= clock.now:
            queue.append((next_index * FRAME_STEP, phone.sends_keyframe(next_index, next_index * FRAME_SECONDS)))
            next_index += 1
        longest = max(longest, len(queue))
        timestamp, keyframe = queue.popleft()
        if limit.admits(timestamp, keyframe):
            clock.now += SLOW_DECODE_SECONDS
    return longest


def test_queue_stays_short_when_decoding_is_slower_than_the_frame_time() -> None:
    assert longest_queue_with_slow_decoding() <= QUEUE_BOUND


def test_frame_late_by_network_jitter_is_still_decoded() -> None:
    clock = FakeClock()
    limit = LatencyLimit(lambda: None, clock)
    limit.admits(0, True)

    clock.now = FRAME_SECONDS + JITTER_SECONDS

    assert limit.admits(FRAME_STEP, False)


def test_frames_after_falling_behind_are_skipped_until_the_next_keyframe() -> None:
    clock = FakeClock()
    requests: list[float] = []
    limit = LatencyLimit(lambda: requests.append(clock.now), clock)
    limit.admits(0, True)
    clock.now = 1.0

    admitted = [
        limit.admits(FRAME_STEP, False),
        limit.admits(2 * FRAME_STEP, False),
        limit.admits(3 * FRAME_STEP, True),
    ]

    assert admitted == [False, False, True]
    assert len(requests) == 1


def test_lasting_network_delay_skips_only_until_one_keyframe() -> None:
    clock = FakeClock()
    requests: list[float] = []
    limit = LatencyLimit(lambda: requests.append(clock.now), clock)
    limit.admits(0, True)
    clock.now = FRAME_SECONDS + LASTING_NETWORK_DELAY_SECONDS
    limit.admits(FRAME_STEP, False)
    clock.now = 2 * FRAME_SECONDS + LASTING_NETWORK_DELAY_SECONDS
    limit.admits(2 * FRAME_STEP, True)

    clock.now = 3 * FRAME_SECONDS + LASTING_NETWORK_DELAY_SECONDS

    assert limit.admits(3 * FRAME_STEP, False)
    assert len(requests) == 1


def test_rtp_timestamp_wrapping_around_is_not_taken_as_lag() -> None:
    clock = FakeClock()
    limit = LatencyLimit(lambda: None, clock)
    limit.admits(RTP_TIMESTAMP_MODULUS - FRAME_STEP, True)

    clock.now = FRAME_SECONDS

    assert limit.admits(0, False)

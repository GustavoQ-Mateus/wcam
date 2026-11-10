import time
from collections.abc import Callable

from aiortc.jitterbuffer import JitterBuffer, JitterFrame
from aiortc.rtp import RtpPacket

STALLED_SECONDS = 0.5


class RecoveringJitterBuffer(JitterBuffer):
    def __init__(
        self,
        capacity: int,
        stalled_seconds: float = STALLED_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(capacity=capacity, is_video=True)
        self._stalled_seconds = stalled_seconds
        self._clock = clock
        self._progress_at: float | None = None
        self.awaiting_keyframe = False
        self.received_bytes = 0
        self.keyframe_requests = 0
        self.stalls = 0

    def add(self, packet: RtpPacket) -> tuple[bool, JitterFrame | None]:
        now = self._clock()
        self.received_bytes += len(packet.payload)
        request_keyframe, frame = super().add(packet)
        if self._progress_at is None or (frame is not None and not self.awaiting_keyframe):
            self._progress_at = now
        elif now - self._progress_at > self._stalled_seconds:
            frame = frame or self._skip_stalled_frame(packet)
            self._progress_at = now
            self.awaiting_keyframe = True
            request_keyframe = True
        if request_keyframe:
            self.keyframe_requests += 1
        return request_keyframe, frame

    def admits_decoded(self, is_keyframe: bool) -> bool:
        if not self.awaiting_keyframe:
            return True
        if not is_keyframe:
            return False
        self.awaiting_keyframe = False
        self._progress_at = self._clock()
        return True

    def _skip_stalled_frame(self, packet: RtpPacket) -> JitterFrame | None:
        self.stalls += 1
        self.remove(self._next_frame_after_hole())
        return self._remove_frame(packet.sequence_number)

    def _next_frame_after_hole(self) -> int:
        origin = self._origin
        if origin is None:
            return 0
        hole_seen = False
        stalled_timestamp: int | None = None
        after_last_packet = 0
        for count in range(self.capacity):
            packet = self._packets[(origin + count) % self.capacity]
            if packet is None:
                hole_seen = True
                continue
            after_last_packet = count + 1
            if not hole_seen or stalled_timestamp == packet.timestamp:
                continue
            if stalled_timestamp is not None:
                return count
            stalled_timestamp = packet.timestamp
        return after_last_packet

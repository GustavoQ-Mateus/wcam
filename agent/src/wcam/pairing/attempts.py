from collections import deque
from datetime import datetime, timedelta

from wcam.clock import Clock, utc_now

MAX_FAILURES = 5
FAILURE_WINDOW = timedelta(seconds=60)
BLOCK_DURATION = timedelta(minutes=10)


class AttemptLimiter:
    def __init__(self, clock: Clock = utc_now) -> None:
        self._clock = clock
        self._failures: dict[str, deque[datetime]] = {}
        self._blocked_until: dict[str, datetime] = {}

    def is_blocked(self, ip: str) -> bool:
        blocked_until = self._blocked_until.get(ip)
        if blocked_until is None:
            return False
        if self._clock() < blocked_until:
            return True
        del self._blocked_until[ip]
        return False

    def record_failure(self, ip: str) -> None:
        now = self._clock()
        failures = self._failures.setdefault(ip, deque())
        failures.append(now)
        while failures[0] <= now - FAILURE_WINDOW:
            failures.popleft()
        if len(failures) < MAX_FAILURES:
            return
        self._blocked_until[ip] = now + BLOCK_DURATION
        del self._failures[ip]

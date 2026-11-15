import asyncio
import json
import logging
import threading
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime

from wcam.change_feed import running_loop
from wcam.clock import Clock, utc_now

KEPT_EVENTS = 50
EPISODE_EVENT = "episode"


@dataclass(frozen=True, slots=True)
class DevEvent:
    at: datetime
    kind: str
    data: Mapping[str, object]


class DevEventLog:
    def __init__(self, clock: Clock = utc_now) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._events: deque[DevEvent] = deque(maxlen=KEPT_EVENTS)
        self._queues: set[asyncio.Queue[DevEvent]] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subscriber_listeners: list[Callable[[int], None]] = []

    @property
    def subscribers(self) -> int:
        return len(self._queues)

    def on_subscribers_change(self, listener: Callable[[int], None]) -> None:
        self._subscriber_listeners.append(listener)

    def record(self, kind: str, data: Mapping[str, object]) -> None:
        event = DevEvent(self._clock(), kind, data)
        with self._lock:
            self._events.append(event)
        loop = self._loop
        if loop is None or not self._queues:
            return
        if running_loop() is loop:
            self._deliver(event)
            return
        loop.call_soon_threadsafe(self._deliver, event)

    def subscribe(self) -> asyncio.Queue[DevEvent]:
        self._loop = asyncio.get_running_loop()
        queue: asyncio.Queue[DevEvent] = asyncio.Queue()
        with self._lock:
            for event in self._events:
                queue.put_nowait(event)
        self._queues.add(queue)
        self._announce_subscribers()
        return queue

    def unsubscribe(self, queue: asyncio.Queue[DevEvent]) -> None:
        if queue not in self._queues:
            return
        self._queues.discard(queue)
        self._announce_subscribers()

    def _deliver(self, event: DevEvent) -> None:
        for queue in list(self._queues):
            queue.put_nowait(event)

    def _announce_subscribers(self) -> None:
        for listener in self._subscriber_listeners:
            listener(len(self._queues))


class EpisodeEvents(logging.Handler):
    def __init__(self, log: DevEventLog) -> None:
        super().__init__()
        self._log = log

    def emit(self, record: logging.LogRecord) -> None:
        self._log.record(EPISODE_EVENT, json.loads(record.getMessage()))

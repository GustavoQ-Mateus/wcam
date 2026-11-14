import asyncio


class ChangeFeed:
    def __init__(self) -> None:
        self._waiters: set[asyncio.Event] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self.closed = False

    @property
    def subscribers(self) -> int:
        return len(self._waiters)

    def subscribe(self) -> asyncio.Event:
        self._loop = asyncio.get_running_loop()
        waiter = asyncio.Event()
        self._waiters.add(waiter)
        return waiter

    def unsubscribe(self, waiter: asyncio.Event) -> None:
        self._waiters.discard(waiter)

    def publish(self) -> None:
        loop = self._loop
        if loop is None or not self._waiters:
            return
        if running_loop() is loop:
            self._wake()
            return
        loop.call_soon_threadsafe(self._wake)

    def close(self) -> None:
        self.closed = True
        self.publish()

    def _wake(self) -> None:
        for waiter in list(self._waiters):
            waiter.set()


def running_loop() -> asyncio.AbstractEventLoop | None:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None

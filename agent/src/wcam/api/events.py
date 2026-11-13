import asyncio
import contextlib
from collections.abc import AsyncGenerator, AsyncIterator, Callable

from fastapi.responses import StreamingResponse

from wcam.change_feed import ChangeFeed

EVENT_STREAM = "text/event-stream"
STREAM_HEADERS = {"Cache-Control": "no-cache"}
REPEAT_SECONDS = 1.0


def sse_event(name: str, data: str) -> str:
    return f"event: {name}\ndata: {data}\n\n"


async def repeated_events(
    feed: ChangeFeed,
    name: str,
    build: Callable[[], str],
    repeat_seconds: float = REPEAT_SECONDS,
) -> AsyncGenerator[str]:
    changed = feed.subscribe()
    try:
        while not feed.closed:
            changed.clear()
            yield sse_event(name, build())
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(changed.wait(), repeat_seconds)
    finally:
        feed.unsubscribe(changed)


def event_stream(events: AsyncIterator[str]) -> StreamingResponse:
    return StreamingResponse(events, media_type=EVENT_STREAM, headers=STREAM_HEADERS)

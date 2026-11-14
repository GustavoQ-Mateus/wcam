import asyncio
import contextlib
import json
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable

from fastapi.responses import StreamingResponse

from wcam.change_feed import ChangeFeed
from wcam.diagnostics.dev_console import iso_milliseconds
from wcam.diagnostics.dev_events import DevEvent, DevEventLog

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


async def developer_events(
    log: DevEventLog,
    metrics: Callable[[], Awaitable[dict[str, object]]],
    stopping: ChangeFeed,
    repeat_seconds: float = REPEAT_SECONDS,
) -> AsyncGenerator[str]:
    loop = asyncio.get_running_loop()
    events = log.subscribe()
    next_metrics = loop.time()
    try:
        while not stopping.closed:
            waiting = next_metrics - loop.time()
            if waiting <= 0:
                yield sse_event("metrics", json.dumps(await metrics()))
                next_metrics += repeat_seconds
                continue
            with contextlib.suppress(TimeoutError):
                event = await asyncio.wait_for(events.get(), waiting)
                yield sse_event("event", event_json(event))
    finally:
        log.unsubscribe(events)


def event_json(event: DevEvent) -> str:
    return json.dumps({"at": iso_milliseconds(event.at), "kind": event.kind, "data": event.data})


def event_stream(events: AsyncIterator[str]) -> StreamingResponse:
    return StreamingResponse(events, media_type=EVENT_STREAM, headers=STREAM_HEADERS)

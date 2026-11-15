import asyncio
import threading

from wcam.api.events import repeated_events, sse_event
from wcam.change_feed import ChangeFeed

WAIT_SECONDS = 1.0
LONG_REPEAT_SECONDS = 60.0


async def test_publish_from_another_thread_wakes_the_subscriber() -> None:
    feed = ChangeFeed()
    changed = feed.subscribe()

    worker = threading.Thread(target=feed.publish)
    worker.start()
    worker.join()

    await asyncio.wait_for(changed.wait(), WAIT_SECONDS)


def test_publish_without_subscribers_does_nothing() -> None:
    ChangeFeed().publish()


async def test_stream_sends_on_subscribing_and_again_on_a_change() -> None:
    feed = ChangeFeed()
    values = iter(["first", "second"])
    events = repeated_events(feed, "status", lambda: next(values), LONG_REPEAT_SECONDS)

    first = await anext(events)
    feed.publish()
    second = await asyncio.wait_for(anext(events), WAIT_SECONDS)

    assert [first, second] == [sse_event("status", "first"), sse_event("status", "second")]
    await events.aclose()


async def test_stream_repeats_without_changes() -> None:
    feed = ChangeFeed()
    events = repeated_events(feed, "status", lambda: "same", 0.01)

    await anext(events)
    repeated = await asyncio.wait_for(anext(events), WAIT_SECONDS)

    assert repeated == sse_event("status", "same")
    await events.aclose()


async def test_closing_the_feed_ends_the_stream_and_drops_the_subscriber() -> None:
    feed = ChangeFeed()
    events = repeated_events(feed, "status", lambda: "status", LONG_REPEAT_SECONDS)
    await anext(events)
    waiting = asyncio.ensure_future(anext(events))
    await asyncio.sleep(0)

    feed.close()

    assert isinstance(await asyncio.wait_for(asyncio.gather(waiting, return_exceptions=True), WAIT_SECONDS), list)
    assert waiting.exception() is not None
    assert feed.subscribers == 0

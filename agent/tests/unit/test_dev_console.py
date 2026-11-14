import asyncio
import json
import logging

from tests.conftest import opened_pipeline, services
from tests.fakes import FakePeerFactory
from tests.unit.test_pipeline import phone_frame
from tests.unit.test_session_manager import confirm_on_both_sides, session_request
from wcam.diagnostics.dev_events import KEPT_EVENTS, DevEventLog, EpisodeEvents
from wcam.diagnostics.stage_times import Stage
from wcam.media.metrics import ReceiveStats
from wcam.services import AgentServices
from wcam.sessions.controls import ControlsChange
from wcam.sessions.manager import SessionManager

PHONE_STATS = {
    "type": "stats",
    "at": 1_731_430_000_000,
    "outbound": {"framesPerSecond": 30, "framesSent": 900, "qualityLimitationReason": "none", "nackCount": None},
    "remoteInbound": None,
}


async def live_agent(factory: FakePeerFactory) -> AgentServices:
    agent = services(SessionManager(factory), opened_pipeline())
    manager = agent.manager
    await manager.create_session(session_request(manager.open_pairing().token))
    factory.last.events.on_connected()
    confirm_on_both_sides(manager, factory)
    return agent


def delivered_frame(agent: AgentServices) -> None:
    agent.pipeline.start_phone()
    agent.pipeline.deliver(phone_frame(), submitted_at=0.0)


async def test_without_a_listener_nothing_is_timed_or_asked_from_the_phone() -> None:
    factory = FakePeerFactory()
    agent = await live_agent(factory)

    delivered_frame(agent)

    assert agent.pipeline.stage_times.take().milliseconds == {}
    assert all(message["type"] != "stats_request" for message in factory.last.sent)


async def test_first_listener_turns_timing_on_and_asks_the_phone_for_statistics() -> None:
    factory = FakePeerFactory()
    agent = await live_agent(factory)
    factory.last.sent.clear()

    listening = agent.dev_events.subscribe()
    delivered_frame(agent)

    window = agent.pipeline.stage_times.take()
    assert {Stage.COLOR, Stage.DELIVER, Stage.TOTAL} <= window.milliseconds.keys()
    assert factory.last.sent == [{"type": "stats_request", "enabled": True}]
    agent.dev_events.unsubscribe(listening)


async def test_last_listener_leaving_turns_timing_off_and_tells_the_phone() -> None:
    factory = FakePeerFactory()
    agent = await live_agent(factory)
    listening = agent.dev_events.subscribe()
    factory.last.sent.clear()

    agent.dev_events.unsubscribe(listening)
    delivered_frame(agent)

    assert agent.pipeline.stage_times.take().milliseconds == {}
    assert factory.last.sent == [{"type": "stats_request", "enabled": False}]


async def test_going_live_with_a_listener_asks_the_phone_for_statistics() -> None:
    factory = FakePeerFactory()
    agent = services(SessionManager(factory), opened_pipeline())
    agent.dev_events.subscribe()
    manager = agent.manager
    await manager.create_session(session_request(manager.open_pairing().token))
    factory.last.events.on_connected()

    confirm_on_both_sides(manager, factory)

    assert factory.last.sent[-1] == {"type": "stats_request", "enabled": True}


async def test_metrics_carry_the_last_phone_statistics_without_the_type() -> None:
    factory = FakePeerFactory()
    agent = await live_agent(factory)

    factory.last.events.on_message(json.dumps(PHONE_STATS))
    metrics = await agent.dev_console.metrics()

    assert metrics["phone"] == {
        "at": PHONE_STATS["at"],
        "outbound": {
            "framesPerSecond": 30,
            "framesSent": 900,
            "framesEncoded": None,
            "keyFramesEncoded": None,
            "bytesSent": None,
            "qualityLimitationReason": "none",
            "nackCount": None,
            "pliCount": None,
            "frameWidth": None,
            "frameHeight": None,
        },
        "remoteInbound": None,
    }


async def test_live_metrics_have_stages_frames_and_the_receiver_numbers() -> None:
    factory = FakePeerFactory()
    agent = await live_agent(factory)
    agent.dev_events.subscribe()
    factory.last.received = ReceiveStats(packets_lost=4, jitter_ms=2.5)
    await agent.dev_console.metrics()
    factory.last.received = ReceiveStats(packets_lost=7, jitter_ms=2.5)
    delivered_frame(agent)

    metrics = await agent.dev_console.metrics()

    assert metrics["session"] is not None
    assert metrics["received"] == {"fps": None, "bitrateKbps": None, "packetsLost": 3, "jitterMs": 2.5}
    delivered = metrics["delivered"]
    assert isinstance(delivered, dict)
    assert (delivered["frames"], delivered["dropped"]) == (1, 0)
    stages = metrics["stages"]
    assert isinstance(stages, dict)
    assert stages["color"] is not None
    assert stages["decode"] is None
    assert metrics["frameTimesMs"] is not None
    assert metrics["budgetMs"] == 33.3
    assert metrics["ceilingKbps"] == 10_000


async def test_metrics_without_a_phone_have_no_session_numbers() -> None:
    agent = services()

    metrics = await agent.dev_console.metrics()

    assert (metrics["session"], metrics["received"], metrics["delivered"], metrics["stages"]) == (
        None,
        None,
        None,
        None,
    )
    assert metrics["frameTimesMs"] is None
    assert metrics["virtualCamera"] == {
        "format": "1080p30",
        "pendingFormat": None,
        "streamingApps": None,
        "source": "placeholder",
    }


async def test_new_listener_gets_the_last_fifty_events() -> None:
    log = DevEventLog()
    for index in range(KEPT_EVENTS + 5):
        log.record("controls", {"index": index})

    queue = log.subscribe()

    assert queue.qsize() == KEPT_EVENTS
    assert (await queue.get()).data == {"index": 5}


async def test_session_and_controls_changes_become_events() -> None:
    factory = FakePeerFactory()
    agent = await live_agent(factory)
    queue = agent.dev_events.subscribe()
    while not queue.empty():
        queue.get_nowait()

    agent.manager.change_controls(ControlsChange(mirror=True))
    await agent.manager.disconnect()
    await asyncio.sleep(0)

    events = [queue.get_nowait() for _ in range(queue.qsize())]
    assert [(event.kind, event.data) for event in events if event.kind != "virtual_camera"] == [
        ("controls", {"mirror": True}),
        ("session_state", {"state": "ended", "reason": "disconnected_by_pc"}),
    ]


async def test_episode_lines_become_events() -> None:
    log = DevEventLog()
    queue = log.subscribe()
    logger = logging.getLogger("wcam.test.episodes")
    handler = EpisodeEvents(log)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info(json.dumps({"cause": "silence", "durationMs": 800}))
    logger.removeHandler(handler)

    event = queue.get_nowait()
    assert (event.kind, event.data) == ("episode", {"cause": "silence", "durationMs": 800})

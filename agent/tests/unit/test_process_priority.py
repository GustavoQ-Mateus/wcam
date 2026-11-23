import asyncio
import threading

import pytest

from wcam.media.pipeline import FramePipeline
from wcam.process_priority import CAPTURE_TASK, SUCCESS, ProcessScheduling
from wcam.virtualcam.fake_sink import FakeSink

ACCESS_DENIED = 5
DELIVERY_SECONDS = 0.2


class FakeSchedulingCalls:
    def __init__(self, error: int = SUCCESS) -> None:
        self.error = error
        self.calls: list[str] = []
        self.joined_threads: list[tuple[str, int]] = []

    def set_above_normal_priority(self) -> int:
        self.calls.append("above_normal")
        return self.error

    def disable_power_throttling(self) -> int:
        self.calls.append("power_throttling_off")
        return self.error

    def join_multimedia_task(self, task: str) -> int:
        self.joined_threads.append((task, threading.get_ident()))
        return self.error


def test_raising_the_process_sets_above_normal_priority_and_turns_off_power_throttling() -> None:
    calls = FakeSchedulingCalls()

    ProcessScheduling(calls).raise_process()

    assert calls.calls == ["above_normal", "power_throttling_off"]


def test_refused_priority_change_is_logged_without_stopping_the_agent(caplog: pytest.LogCaptureFixture) -> None:
    calls = FakeSchedulingCalls(error=ACCESS_DENIED)

    ProcessScheduling(calls).raise_process()

    assert calls.calls == ["above_normal", "power_throttling_off"]
    assert len(caplog.records) == 2


def test_thread_joins_the_capture_task_once() -> None:
    calls = FakeSchedulingCalls()
    scheduling = ProcessScheduling(calls)

    scheduling.join_capture_task()
    scheduling.join_capture_task()

    assert calls.joined_threads == [(CAPTURE_TASK, threading.get_ident())]


def test_each_thread_joins_the_capture_task_on_its_own() -> None:
    calls = FakeSchedulingCalls()
    scheduling = ProcessScheduling(calls)
    other = threading.Thread(target=scheduling.join_capture_task)

    scheduling.join_capture_task()
    other.start()
    other.join()

    assert len({thread for _, thread in calls.joined_threads}) == 2


def test_without_windows_nothing_is_changed() -> None:
    scheduling = ProcessScheduling(None)

    scheduling.raise_process()
    scheduling.join_capture_task()


async def test_delivery_thread_joins_the_capture_task(monkeypatch: pytest.MonkeyPatch) -> None:
    joined: list[int] = []
    monkeypatch.setattr("wcam.media.pipeline.join_capture_task", lambda: joined.append(threading.get_ident()))
    pipeline = FramePipeline(FakeSink())
    pipeline.open()
    running = asyncio.create_task(pipeline.run())

    await asyncio.sleep(DELIVERY_SECONDS)
    running.cancel()
    await asyncio.gather(running, return_exceptions=True)

    assert len(joined) == 1
    assert joined[0] != threading.get_ident()

import asyncio
import os

from wcam.parent_pipe import pipe_probe, stop_when_parent_closes

POLL_SECONDS = 0.01
WATCH_SECONDS = 0.1


class ClosingProbe:
    def __init__(self, open_checks: int) -> None:
        self.open_checks = open_checks

    def is_open(self) -> bool:
        self.open_checks -= 1
        return self.open_checks >= 0


def test_pipe_with_the_writer_still_open_is_open() -> None:
    reader, writer = os.pipe()
    try:
        assert pipe_probe(reader).is_open()
    finally:
        os.close(reader)
        os.close(writer)


def test_pipe_whose_writer_closed_is_closed() -> None:
    reader, writer = os.pipe()
    os.close(writer)
    try:
        assert not pipe_probe(reader).is_open()
    finally:
        os.close(reader)


async def test_agent_stops_once_the_parent_closes_the_pipe() -> None:
    stops: list[bool] = []

    await stop_when_parent_closes(ClosingProbe(open_checks=3), lambda: stops.append(True), POLL_SECONDS)

    assert stops == [True]


async def test_agent_keeps_running_while_the_parent_keeps_the_pipe_open() -> None:
    stops: list[bool] = []
    watching = asyncio.create_task(
        stop_when_parent_closes(ClosingProbe(open_checks=1000), lambda: stops.append(True), POLL_SECONDS)
    )

    await asyncio.sleep(WATCH_SECONDS)
    watching.cancel()
    await asyncio.gather(watching, return_exceptions=True)

    assert stops == []

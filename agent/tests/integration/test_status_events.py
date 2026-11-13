import asyncio
import json
import time
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx

from tests.conftest import opened_pipeline, services
from tests.fakes import FakePeerFactory
from tests.integration.test_webrtc import free_port, wait_until
from wcam.app import create_servers, serve
from wcam.config import Settings
from wcam.network.certificates import load_or_create_certificate
from wcam.network.lan import detect_lan_interface
from wcam.services import AgentServices
from wcam.sessions.manager import SessionManager

CHANGE_DEADLINE_SECONDS = 0.3
SHUTDOWN_DEADLINE_SECONDS = 1.0
REPEAT_TOLERANCE_SECONDS = 1.5
EVENT_PREFIX = "event: "
DATA_PREFIX = "data: "


@asynccontextmanager
async def running_agent(tmp_path: Path, web_dist: Path) -> AsyncGenerator[tuple[httpx.AsyncClient, AgentServices]]:
    settings = Settings(data_dir=tmp_path, web_dist=web_dist, console_port=free_port(), phone_port=free_port())
    lan = detect_lan_interface(None)
    agent = services(SessionManager(FakePeerFactory()), opened_pipeline())
    servers = create_servers(settings, lan, load_or_create_certificate(tmp_path, lan.ip), agent)
    serving = asyncio.create_task(serve(servers))
    try:
        await wait_until(lambda: all(server.started for server in servers))
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{settings.console_port}") as console:
            yield console, agent
    finally:
        for server in servers:
            server.should_exit = True
        await serving


async def next_event(lines: AsyncIterator[str]) -> tuple[str, dict[str, Any]]:
    name = ""
    async for line in lines:
        if line.startswith(EVENT_PREFIX):
            name = line.removeprefix(EVENT_PREFIX)
        elif line.startswith(DATA_PREFIX):
            return name, json.loads(line.removeprefix(DATA_PREFIX))
    raise AssertionError("stream ended")


async def test_events_start_with_the_same_status_as_the_status_route(tmp_path: Path, web_dist: Path) -> None:
    async with running_agent(tmp_path, web_dist) as (console, _):
        status = (await console.get("/api/status")).json()
        async with console.stream("GET", "/api/events") as stream:
            name, first = await next_event(stream.aiter_lines())
            content_type = stream.headers["content-type"]

    assert content_type.startswith("text/event-stream")
    assert name == "status"
    assert first.keys() == status.keys()
    assert first["controls"] == status["controls"]


async def test_control_change_reaches_the_stream_in_less_than_300_ms(tmp_path: Path, web_dist: Path) -> None:
    async with running_agent(tmp_path, web_dist) as (console, _), console.stream("GET", "/api/events") as stream:
        lines = stream.aiter_lines()
        await next_event(lines)
        started = time.monotonic()
        await console.patch("/api/controls", json={"mirror": True})
        _, changed = await next_event(lines)
        elapsed = time.monotonic() - started

    assert changed["controls"]["mirror"]
    assert elapsed < CHANGE_DEADLINE_SECONDS


async def test_status_repeats_every_second_without_changes(tmp_path: Path, web_dist: Path) -> None:
    async with running_agent(tmp_path, web_dist) as (console, _), console.stream("GET", "/api/events") as stream:
        lines = stream.aiter_lines()
        await next_event(lines)
        started = time.monotonic()
        await next_event(lines)
        elapsed = time.monotonic() - started

    assert elapsed < REPEAT_TOLERANCE_SECONDS


async def test_open_stream_does_not_hold_the_shutdown(tmp_path: Path, web_dist: Path) -> None:
    async with running_agent(tmp_path, web_dist) as (console, agent), console.stream("GET", "/api/events") as stream:
        lines = stream.aiter_lines()
        await next_event(lines)
        started = time.monotonic()
        agent.status_changes.close()
        async for _ in lines:
            pass
        stopped_after = time.monotonic() - started

    assert stopped_after < SHUTDOWN_DEADLINE_SECONDS

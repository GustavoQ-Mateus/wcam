import asyncio
from collections.abc import AsyncIterator
from typing import Any

import httpx
import numpy as np
import pytest
from aiortc import RTCSessionDescription, VideoStreamTrack
from av import VideoFrame

from tests.conftest import console_app, console_client, opened_pipeline, phone_app, phone_client
from tests.integration.test_webrtc import (
    RecordingPeerFactory,
    current_status,
    phone_client_peer,
    wait_for_video,
    wait_until,
)
from tests.unit.test_color_calibration import color_sample_message, phone_sample, scene_planes
from wcam.config import Settings
from wcam.media.color_range import ColorRange
from wcam.media.pipeline import FramePipeline, FrameSource
from wcam.network.lan import LanInterface, detect_lan_interface
from wcam.sessions.manager import SessionManager
from wcam.virtualcam.sink import OUTPUT_HEIGHT, OUTPUT_WIDTH

SCENE_SEED = 21
SAMPLES = 5
SAMPLE_INTERVAL_SECONDS = 1.0
APPLIED_DELTA_E = 2.0
ENCODER_WARMUP_SECONDS = 3.0
LAST_FIT_SECONDS = 3.0
SETTLE_SECONDS = 20.0
POLL_SECONDS = 0.1


class StillScene(VideoStreamTrack):
    def __init__(self) -> None:
        super().__init__()
        luma, blue, red = scene_planes(SCENE_SEED, OUTPUT_WIDTH, OUTPUT_HEIGHT)
        self._image = np.concatenate([luma, blue.reshape(-1, OUTPUT_WIDTH), red.reshape(-1, OUTPUT_WIDTH)])

    async def recv(self) -> VideoFrame:
        pts, time_base = await self.next_timestamp()
        frame = VideoFrame.from_ndarray(self._image, format="yuv420p")
        frame.pts = pts
        frame.time_base = time_base
        return frame


async def calibration_after_samples(console: httpx.AsyncClient, phone: httpx.AsyncClient) -> dict[str, Any]:
    client = phone_client_peer(StillScene())
    planes = scene_planes(SCENE_SEED, OUTPUT_WIDTH, OUTPUT_HEIGHT)
    try:
        token = (await console.post("/api/pairing")).json()["url"].split("#t=")[1]
        created = (await phone.post("/api/sessions", json={"token": token, "sdp": await client.offer()})).json()
        await client.connection.setRemoteDescription(RTCSessionDescription(created["sdp"], "answer"))
        await client.next_state()
        await console.post("/api/sessions/current/confirm")
        await client.next_state()
        video = await wait_for_video(console)
        assert video["colorCalibration"] == {"state": "measuring", "deltaE": None}
        await asyncio.sleep(ENCODER_WARMUP_SECONDS)
        for _ in range(SAMPLES):
            client.channel.send(color_sample_message(phone_sample(planes, color_range=ColorRange.LIMITED)))
            await asyncio.sleep(SAMPLE_INTERVAL_SECONDS)
        await asyncio.sleep(LAST_FIT_SECONDS)
        calibration = await settled_calibration(console)
        await console.delete("/api/sessions/current")
        return calibration
    finally:
        await client.connection.close()


async def settled_calibration(console: httpx.AsyncClient) -> dict[str, Any]:
    async with asyncio.timeout(SETTLE_SECONDS):
        while True:
            calibration: dict[str, Any] = (await current_status(console))["session"]["video"]["colorCalibration"]
            if calibration["state"] != "measuring":
                return calibration
            await asyncio.sleep(POLL_SECONDS)


@pytest.fixture
def lan() -> LanInterface:
    return detect_lan_interface(None)


@pytest.fixture
async def pipeline() -> AsyncIterator[FramePipeline]:
    running = opened_pipeline()
    task = asyncio.create_task(running.run())
    yield running
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


async def test_each_connection_measures_and_applies_the_phone_color(
    settings: Settings,
    lan: LanInterface,
    pipeline: FramePipeline,
) -> None:
    manager = SessionManager(RecordingPeerFactory(lan, pipeline))

    async with (
        console_client(console_app(settings, manager, pipeline)) as console,
        phone_client(phone_app(settings, manager)) as phone,
    ):
        first = await calibration_after_samples(console, phone)
        await wait_until(lambda: pipeline.source is FrameSource.PLACEHOLDER)
        second = await calibration_after_samples(console, phone)

    assert first["state"] == "applied"
    assert first["deltaE"] < APPLIED_DELTA_E
    assert second["state"] == "applied"

import asyncio
from typing import cast

import httpx
import numpy as np
from aiortc import RTCConfiguration, RTCPeerConnection, RTCSessionDescription
from av import VideoFrame

from tests.conftest import console_client, services
from tests.fakes import FakePeerFactory
from tests.integration.test_webrtc import WAIT_SECONDS, pipeline, sink, wait_until
from tests.unit.test_color_range import flat_i420
from tests.unit.test_pipeline import random_i420
from wcam.app import create_console_app
from wcam.config import Settings
from wcam.media.loopback_ice import LOOPBACK, gather_only_on_loopback
from wcam.media.peer import FrameSource as ReceivedTrack
from wcam.media.pipeline import FramePipeline, i420_planes
from wcam.media.preview import PREVIEW_HEIGHT, PREVIEW_WIDTH, decimated, preview_size, reduced_frame
from wcam.media.sdp_filter import candidate_addresses
from wcam.services import AgentServices
from wcam.sessions.manager import SessionManager

__all__ = ["pipeline", "sink"]


def console_peer() -> RTCPeerConnection:
    connection = RTCPeerConnection(RTCConfiguration(iceServers=[]))
    connection.addTransceiver("video", direction="recvonly")
    gather_only_on_loopback(connection)
    return connection


async def open_preview(console: httpx.AsyncClient, connection: RTCPeerConnection) -> httpx.Response:
    await connection.setLocalDescription(await connection.createOffer())
    return await console.post("/api/preview", json={"sdp": connection.localDescription.sdp})


async def first_frame(connection: RTCPeerConnection) -> VideoFrame:
    track = cast(ReceivedTrack, connection.getTransceivers()[0].receiver.track)
    frame = await asyncio.wait_for(track.recv(), WAIT_SECONDS)
    assert isinstance(frame, VideoFrame)
    return frame


def preview_services(pipeline: FramePipeline) -> AgentServices:
    return services(SessionManager(FakePeerFactory()), pipeline)


def test_preview_is_960x540_or_the_format_height_when_smaller() -> None:
    assert preview_size(1920, 1080) == (PREVIEW_WIDTH, PREVIEW_HEIGHT)
    assert preview_size(3840, 2160) == (PREVIEW_WIDTH, PREVIEW_HEIGHT)
    assert preview_size(640, 360) == (640, 360)


async def test_preview_sends_the_reduced_camera_frame_over_loopback(
    settings: Settings, pipeline: FramePipeline
) -> None:
    agent = preview_services(pipeline)
    connection = console_peer()

    async with console_client(create_console_app(settings, agent, "https://phone/cam")) as console:
        response = await open_preview(console, connection)
        await connection.setRemoteDescription(RTCSessionDescription(response.json()["sdp"], "answer"))
        frame = await first_frame(connection)
        await agent.preview.shutdown()
    await connection.close()

    assert response.status_code == 201
    assert set(candidate_addresses(response.json()["sdp"])) == {LOOPBACK}
    assert (frame.width, frame.height) == (PREVIEW_WIDTH, PREVIEW_HEIGHT)


async def test_closing_the_preview_ends_its_connection(settings: Settings, pipeline: FramePipeline) -> None:
    agent = preview_services(pipeline)
    connection = console_peer()

    async with console_client(create_console_app(settings, agent, "https://phone/cam")) as console:
        response = await open_preview(console, connection)
        await connection.setRemoteDescription(RTCSessionDescription(response.json()["sdp"], "answer"))
        await first_frame(connection)
        closed = await console.delete("/api/preview")
        await wait_until(lambda: connection.connectionState in ("closed", "failed"))
    await connection.close()

    assert closed.status_code == 204
    assert not agent.preview.is_open


async def test_new_preview_replaces_the_previous_one(settings: Settings, pipeline: FramePipeline) -> None:
    agent = preview_services(pipeline)
    first, second = console_peer(), console_peer()

    async with console_client(create_console_app(settings, agent, "https://phone/cam")) as console:
        answer = (await open_preview(console, first)).json()["sdp"]
        await first.setRemoteDescription(RTCSessionDescription(answer, "answer"))
        await first_frame(first)
        replacement = await open_preview(console, second)
        await second.setRemoteDescription(RTCSessionDescription(replacement.json()["sdp"], "answer"))
        await first_frame(second)
        await wait_until(lambda: first.connectionState in ("closed", "failed"))
        await agent.preview.shutdown()
    await first.close()
    await second.close()

    assert replacement.status_code == 201


async def test_delete_without_a_preview_answers_no_content(settings: Settings, pipeline: FramePipeline) -> None:
    async with console_client(create_console_app(settings, preview_services(pipeline), "https://phone/cam")) as console:
        response = await console.delete("/api/preview")

    assert response.status_code == 204


async def test_offer_without_video_is_refused(settings: Settings, pipeline: FramePipeline) -> None:
    async with console_client(create_console_app(settings, preview_services(pipeline), "https://phone/cam")) as console:
        garbage = await console.post("/api/preview", json={"sdp": "not an sdp"})
        missing = await console.post("/api/preview", json={})

    assert garbage.status_code == 422
    assert garbage.json()["error"]["code"] == "invalid_request"
    assert missing.status_code == 422


def test_2160p_frame_is_reduced_to_the_preview_size_keeping_flat_colors() -> None:
    frame = flat_i420(3840, 2160, luma=180, chroma=90)

    reduced = reduced_frame(frame).to_ndarray()

    assert reduced.shape == (PREVIEW_HEIGHT * 3 // 2, PREVIEW_WIDTH)
    assert (reduced[:PREVIEW_HEIGHT] == 180).all()
    assert (reduced[PREVIEW_HEIGHT:] == 90).all()


def test_decimation_keeps_every_other_pixel_of_each_plane() -> None:
    frame = random_i420(8, 4)

    smaller = decimated(frame, 8, 4, 2)

    luma, blue, red = i420_planes(frame, 8, 4)
    expected = np.concatenate([plane[::2, ::2].reshape(-1) for plane in (luma, blue, red)])
    assert smaller.reshape(-1).tobytes() == expected.tobytes()

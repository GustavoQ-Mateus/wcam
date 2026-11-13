import asyncio
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass

from tests.fakes import FakePeer, FakePeerFactory
from tests.unit.test_session_manager import confirm_on_both_sides, session_request
from tests.unit.test_video_format import video_format_message
from wcam.media.camera_format import CameraFormatControl
from wcam.media.pipeline import FramePipeline
from wcam.media.video_format import VideoFormat
from wcam.sessions.manager import SessionManager
from wcam.virtualcam.fake_sink import FakeSink

POLL_SECONDS = 0.01
WAIT_SECONDS = 2.0
CAPABILITIES = (
    '{"type": "camera_capabilities", "width": 3840, "height": 2160, "frameRate": 60, '
    '"facingMode": "environment", "codecs": ["video/H264"]}'
)
ALL_FORMATS = [str(video_format) for video_format in VideoFormat]


@dataclass(frozen=True, slots=True)
class Agent:
    sink: FakeSink
    pipeline: FramePipeline
    control: CameraFormatControl
    manager: SessionManager
    peer: FakePeer


@asynccontextmanager
async def live_agent(holds_formats: bool = False) -> AsyncGenerator[Agent]:
    sink = FakeSink()
    sink.holds_formats = holds_formats
    sink.reports_changes = holds_formats
    pipeline = FramePipeline(sink)
    pipeline.open()
    control = CameraFormatControl(pipeline, POLL_SECONDS)
    factory = FakePeerFactory()
    manager = SessionManager(factory, camera=control)
    control.start()
    await manager.create_session(session_request(manager.open_pairing().token))
    factory.last.events.on_connected()
    confirm_on_both_sides(manager, factory)
    factory.last.events.on_message(CAPABILITIES)
    factory.last.sent.clear()
    try:
        yield Agent(sink, pipeline, control, manager, factory.last)
    finally:
        await control.close()
        await manager.shutdown()


async def eventually(condition: Callable[[], bool]) -> None:
    async with asyncio.timeout(WAIT_SECONDS):
        while True:
            if condition():
                return
            await asyncio.sleep(POLL_SECONDS)


def formats_sent(peer: FakePeer) -> list[object]:
    return [message["format"] for message in peer.sent if message["type"] == "video_format"]


async def test_accepted_format_reaches_camera_pipeline_and_phone() -> None:
    async with live_agent() as agent:
        agent.manager.set_video_format(VideoFormat.HD_60)
        await eventually(lambda: agent.peer.sent != [])

        state = agent.manager.status().video_format
        assert agent.sink.requests[-1] == (1280, 720, 60)
        assert (state.selected, state.camera, state.pending) == (VideoFormat.HD_60, VideoFormat.HD_60, False)
        assert (agent.pipeline.output.width, agent.pipeline.output.height, agent.pipeline.output.fps) == (1280, 720, 60)
        assert agent.peer.sent == [video_format_message("720p60", ALL_FORMATS)]
        assert agent.peer.max_bitrate_bps == VideoFormat.HD_60.size.max_bitrate_bps


async def test_pending_format_keeps_the_phone_on_the_announced_one() -> None:
    async with live_agent(holds_formats=True) as agent:
        agent.manager.set_video_format(VideoFormat.UHD_30)
        await eventually(lambda: agent.manager.status().video_format.pending)

        state = agent.manager.status().video_format
        assert (state.selected, state.camera) == (VideoFormat.UHD_30, VideoFormat.FULL_HD_30)
        assert set(formats_sent(agent.peer)) <= {"1080p30"}
        assert agent.peer.max_bitrate_bps == VideoFormat.FULL_HD_30.size.max_bitrate_bps
        assert agent.pipeline.output.width == VideoFormat.FULL_HD_30.size.width


async def test_pending_format_reaches_the_phone_when_the_camera_applies_it() -> None:
    async with live_agent(holds_formats=True) as agent:
        agent.manager.set_video_format(VideoFormat.UHD_30)
        await eventually(lambda: agent.manager.status().video_format.pending)

        agent.sink.apply_held_format()
        await eventually(lambda: not agent.manager.status().video_format.pending)

        assert agent.manager.status().video_format.camera is VideoFormat.UHD_30
        assert formats_sent(agent.peer)[-1] == "2160p30"
        assert agent.peer.max_bitrate_bps == VideoFormat.UHD_30.size.max_bitrate_bps
        assert agent.pipeline.output.width == VideoFormat.UHD_30.size.width


async def test_choosing_the_announced_format_again_cancels_the_pending_change() -> None:
    async with live_agent(holds_formats=True) as agent:
        agent.manager.set_video_format(VideoFormat.UHD_30)
        await eventually(lambda: agent.manager.status().video_format.pending)

        agent.manager.set_video_format(VideoFormat.FULL_HD_30)
        await eventually(lambda: not agent.manager.status().video_format.pending)
        agent.sink.apply_held_format()
        await asyncio.sleep(POLL_SECONDS * 5)

        state = agent.manager.status().video_format
        assert (state.selected, state.camera, state.pending) == (VideoFormat.FULL_HD_30, VideoFormat.FULL_HD_30, False)


async def test_refused_format_keeps_the_camera_and_the_phone_where_they_were() -> None:
    async with live_agent() as agent:
        agent.sink.accepts_formats = False

        agent.manager.set_video_format(VideoFormat.HD_30)
        await eventually(lambda: agent.sink.requests != [])
        await asyncio.sleep(POLL_SECONDS * 5)

        state = agent.manager.status().video_format
        assert (state.selected, state.camera, state.pending) == (VideoFormat.HD_30, VideoFormat.FULL_HD_30, False)
        assert agent.peer.sent == []


async def test_camera_without_format_reports_is_not_polled() -> None:
    async with live_agent() as agent:
        agent.sink.holds_formats = True
        agent.manager.set_video_format(VideoFormat.HD_30)
        await eventually(lambda: agent.sink.requests != [])
        await asyncio.sleep(POLL_SECONDS * 5)

        agent.sink.apply_held_format()
        await asyncio.sleep(POLL_SECONDS * 5)

        assert agent.manager.status().video_format.pending


async def test_closing_stops_the_polling() -> None:
    sink = FakeSink()
    sink.reports_changes = True
    pipeline = FramePipeline(sink)
    pipeline.open()
    control = CameraFormatControl(pipeline, POLL_SECONDS)
    changes: list[None] = []
    control.start()
    control.on_change(lambda: changes.append(None))

    await control.close()
    sink.holds_formats = True
    sink.request_format(1280, 720, 30)
    await asyncio.sleep(POLL_SECONDS * 5)

    assert changes == []

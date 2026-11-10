import copy
from collections.abc import Iterator

import pytest
from aiortc import RTCConfiguration, RTCPeerConnection, RTCRtpSender, RTCSessionDescription, VideoStreamTrack
from aiortc import codecs as aiortc_codecs
from aiortc.rtcrtpparameters import RTCRtpCodecParameters

from wcam.media.h264_level import (
    ANSWER_PROFILE_LEVEL_IDS,
    PROFILE_LEVEL_ID,
    UnexpectedAiortcCodecsError,
    declare_h264_level_5_1,
    h264_codecs,
)

H264_FORMATS = ("video/H264", "video/rtx")


@pytest.fixture
def video_codecs() -> Iterator[list[RTCRtpCodecParameters]]:
    saved = copy.deepcopy(aiortc_codecs.CODECS["video"])
    yield aiortc_codecs.CODECS["video"]
    aiortc_codecs.CODECS["video"] = saved


def profile_level_ids() -> set[str]:
    return {str(codec.parameters[PROFILE_LEVEL_ID]) for codec in h264_codecs()}


def test_aiortc_h264_codecs_are_the_ones_this_adjustment_knows(
    video_codecs: list[RTCRtpCodecParameters],
) -> None:
    assert len(h264_codecs()) == 2


def test_declared_level_is_5_1_for_both_profiles(video_codecs: list[RTCRtpCodecParameters]) -> None:
    declare_h264_level_5_1()

    assert profile_level_ids() == ANSWER_PROFILE_LEVEL_IDS == {"420033", "42e033"}


def test_declaring_twice_keeps_level_5_1(video_codecs: list[RTCRtpCodecParameters]) -> None:
    declare_h264_level_5_1()
    declare_h264_level_5_1()

    assert profile_level_ids() == ANSWER_PROFILE_LEVEL_IDS


def test_unknown_aiortc_codecs_fail_loudly(video_codecs: list[RTCRtpCodecParameters]) -> None:
    next(codec for codec in video_codecs if codec.mimeType == "video/H264").parameters[PROFILE_LEVEL_ID] = "640c1f"

    with pytest.raises(UnexpectedAiortcCodecsError):
        declare_h264_level_5_1()


async def test_answer_declares_level_5_1(video_codecs: list[RTCRtpCodecParameters]) -> None:
    declare_h264_level_5_1()
    phone = RTCPeerConnection(RTCConfiguration(iceServers=[]))
    agent = RTCPeerConnection(RTCConfiguration(iceServers=[]))
    transceiver = phone.addTransceiver(VideoStreamTrack(), direction="sendonly")
    transceiver.setCodecPreferences(
        [codec for codec in RTCRtpSender.getCapabilities("video").codecs if codec.mimeType in H264_FORMATS]
    )
    try:
        await phone.setLocalDescription(await phone.createOffer())
        await agent.setRemoteDescription(RTCSessionDescription(phone.localDescription.sdp, "offer"))
        await agent.setLocalDescription(await agent.createAnswer())
        answer = agent.localDescription.sdp
    finally:
        await phone.close()
        await agent.close()

    assert "profile-level-id=42e033" in answer
    assert "profile-level-id=420033" in answer
    assert "profile-level-id=42e01f" not in answer

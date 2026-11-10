from aiortc import codecs as aiortc_codecs
from aiortc.rtcrtpparameters import RTCRtpCodecParameters

H264_MIME_TYPE = "video/H264"
PROFILE_LEVEL_ID = "profile-level-id"
AIORTC_PROFILE_LEVEL_IDS = frozenset({"42001f", "42e01f"})
LEVEL_5_1 = "33"
PROFILE_HEX_DIGITS = 4
ANSWER_PROFILE_LEVEL_IDS = frozenset(profile[:PROFILE_HEX_DIGITS] + LEVEL_5_1 for profile in AIORTC_PROFILE_LEVEL_IDS)


class UnexpectedAiortcCodecsError(RuntimeError):
    pass


def declare_h264_level_5_1() -> None:
    # aiortc 1.15 answers with its own H.264 parameters, fixed at level 3.1 (1280x720); 2160p30 needs level 5.1.
    # The Safari ignores the answered level, so this keeps the answer true to what the agent decodes.
    for codec in h264_codecs():
        profile_level_id = str(codec.parameters[PROFILE_LEVEL_ID])
        codec.parameters[PROFILE_LEVEL_ID] = profile_level_id[:PROFILE_HEX_DIGITS] + LEVEL_5_1


def h264_codecs() -> list[RTCRtpCodecParameters]:
    codecs = [codec for codec in aiortc_codecs.CODECS["video"] if codec.mimeType == H264_MIME_TYPE]
    found = frozenset(str(codec.parameters.get(PROFILE_LEVEL_ID)) for codec in codecs)
    if found not in (AIORTC_PROFILE_LEVEL_IDS, ANSWER_PROFILE_LEVEL_IDS):
        raise UnexpectedAiortcCodecsError(f"aiortc H.264 codecs changed: {sorted(found)}")
    return codecs

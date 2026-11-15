from wcam.errors import AgentError


class VideoTooLargeError(AgentError):
    code = "video_too_large"


class VideoUnsupportedError(AgentError):
    code = "video_unsupported"


class NoVideoFileError(AgentError):
    code = "no_video_file"


class NoVideoFileToUseError(NoVideoFileError):
    status_code = 409


class VideoSourceActiveError(AgentError):
    code = "video_source_active"


class VideoSourceInactiveError(AgentError):
    code = "video_source_inactive"


class InvalidVideoPositionError(AgentError):
    code = "invalid_request"


class MissingVideoNameError(AgentError):
    code = "invalid_request"

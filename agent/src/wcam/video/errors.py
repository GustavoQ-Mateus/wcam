from wcam.errors import AgentError


class VideoTooLargeError(AgentError):
    code = "video_too_large"


class VideoUnsupportedError(AgentError):
    code = "video_unsupported"


class VideoLibraryFullError(AgentError):
    code = "video_library_full"


class VideoNotFoundError(AgentError):
    code = "video_not_found"


class TimelineEmptyError(AgentError):
    code = "timeline_empty"


class VideoSourceActiveError(AgentError):
    code = "video_source_active"


class VideoSourceInactiveError(AgentError):
    code = "video_source_inactive"


class InvalidTimelineError(AgentError):
    code = "invalid_request"


class InvalidVideoPositionError(AgentError):
    code = "invalid_request"


class MissingVideoNameError(AgentError):
    code = "invalid_request"

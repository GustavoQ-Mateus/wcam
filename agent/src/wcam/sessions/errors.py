from wcam.errors import AgentError


class TooManyAttemptsError(AgentError):
    code = "too_many_attempts"


class SessionAlreadyActiveError(AgentError):
    code = "session_already_active"


class InvalidOfferError(AgentError):
    code = "invalid_request"


class NoSessionAwaitingConfirmationError(AgentError):
    code = "no_session_awaiting_confirmation"


class NoActiveSessionError(AgentError):
    code = "no_active_session"


class NoLiveSessionError(AgentError):
    code = "no_live_session"


class UnavailableVideoFormatError(AgentError):
    code = "invalid_request"

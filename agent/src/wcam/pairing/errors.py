from wcam.errors import AgentError


class PairingTokenInvalidError(AgentError):
    code = "pairing_token_invalid"


class PairingTokenExpiredError(AgentError):
    code = "pairing_token_expired"


class PairingWindowClosedError(AgentError):
    code = "pairing_window_closed"

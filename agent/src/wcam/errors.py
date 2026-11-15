class AgentError(Exception):
    code: str = "internal_error"
    status_code: int | None = None

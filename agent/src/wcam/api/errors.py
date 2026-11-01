from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from wcam.errors import AgentError

HTTP_ERROR_CODES = {404: "not_found", 405: "method_not_allowed"}
SERVER_ERROR_THRESHOLD = 500
INTERNAL_ERROR = (500, "Something went wrong in the agent.")
AGENT_ERRORS = {
    "pairing_token_invalid": (401, "The pairing token is not valid."),
    "pairing_token_expired": (401, "The pairing token expired."),
    "pairing_window_closed": (403, "No pairing window is open."),
    "too_many_attempts": (429, "Too many attempts from this address."),
    "session_already_active": (409, "Another session is already active."),
    "invalid_request": (422, "The request is not valid."),
    "no_session_awaiting_confirmation": (409, "No session is waiting for confirmation."),
    "no_active_session": (404, "No session is active."),
}


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AgentError, handle_agent_error)
    app.add_exception_handler(HTTPException, handle_http_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)


async def handle_agent_error(request: Request, exception: Exception) -> JSONResponse:
    code = exception.code if isinstance(exception, AgentError) else "internal_error"
    status_code, message = AGENT_ERRORS.get(code, INTERNAL_ERROR)
    return error_response(status_code, code, message)


async def handle_http_error(request: Request, exception: Exception) -> JSONResponse:
    status_code = exception.status_code if isinstance(exception, HTTPException) else SERVER_ERROR_THRESHOLD
    return error_response(status_code, http_error_code(status_code), "The request failed.")


def http_error_code(status_code: int) -> str:
    if status_code in HTTP_ERROR_CODES:
        return HTTP_ERROR_CODES[status_code]
    return "internal_error" if status_code >= SERVER_ERROR_THRESHOLD else "invalid_request"


async def handle_validation_error(request: Request, exception: Exception) -> JSONResponse:
    return error_response(422, "invalid_request", "The request is not valid.")


async def handle_unexpected_error(request: Request, exception: Exception) -> JSONResponse:
    status_code, message = INTERNAL_ERROR
    return error_response(status_code, "internal_error", message)

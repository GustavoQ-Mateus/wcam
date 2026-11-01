from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

HTTP_ERROR_CODES = {404: "not_found", 405: "method_not_allowed"}


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, handle_http_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)


async def handle_http_error(request: Request, exception: Exception) -> JSONResponse:
    status_code = exception.status_code if isinstance(exception, HTTPException) else 500
    return error_response(status_code, HTTP_ERROR_CODES.get(status_code, "http_error"), "The request failed.")


async def handle_validation_error(request: Request, exception: Exception) -> JSONResponse:
    return error_response(422, "invalid_request", "The request is not valid.")


async def handle_unexpected_error(request: Request, exception: Exception) -> JSONResponse:
    return error_response(500, "internal_error", "Something went wrong in the agent.")

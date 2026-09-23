"""One domain error type and one handler. Routers raise AppError, clients get clean JSON."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class UpstreamError(AppError):
    """External service (OpenAI, DB) failed or timed out."""

    def __init__(self, message: str = "External service unavailable") -> None:
        super().__init__(message, status_code=502)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, error: AppError) -> JSONResponse:
        return JSONResponse({"detail": error.message}, status_code=error.status_code)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse({"detail": "Internal error"}, status_code=500)

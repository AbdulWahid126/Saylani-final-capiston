from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import logger


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        code: str = "INTERNAL_SERVER_ERROR",
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}


class NotFoundError(AppException):
    def __init__(self, resource: str, identifier: Any = None) -> None:
        msg = f"{resource} not found" if not identifier else f"{resource} '{identifier}' not found"
        super().__init__(
            message=msg,
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
        )


class AuthenticationError(AppException):
    def __init__(self, message: str = "Invalid credentials or token expired") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="AUTHENTICATION_FAILED",
        )


class ForbiddenError(AppException):
    def __init__(self, message: str = "You do not have permission to access this resource") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
        )


class ConflictError(AppException):
    def __init__(
        self, message: str = "Resource conflict or duplicate entry", details: Any = None
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            code="CONFLICT",
            details=details,
        )


class BadRequestError(AppException):
    def __init__(self, message: str = "Bad request", details: Any = None) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BAD_REQUEST",
            details=details,
        )


class ValidationException(AppException):
    def __init__(self, message: str = "Validation failed", details: Any = None) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            details=details,
        )


NotFoundException = NotFoundError
ValidationError = ValidationException


class TerminalIntegrationError(AppException):
    def __init__(
        self, message: str, details: Any = None, code: str = "MT5_INTEGRATION_ERROR"
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=code,
            details=details,
        )


class MT5Error(TerminalIntegrationError):
    """Base exception for all MT5 operations."""

    def __init__(self, message: str, details: Any = None, code: str = "MT5_ERROR") -> None:
        super().__init__(message=message, details=details, code=code)


class MT5InitializationError(MT5Error):
    """Raised when MT5 terminal initialization or IPC connection fails."""

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message=message, details=details, code="MT5_INITIALIZATION_ERROR")


class MT5AccountError(MT5Error):
    """Raised when account information cannot be read or credentials fail."""

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message=message, details=details, code="MT5_ACCOUNT_ERROR")


class MT5QueryError(MT5Error):
    """Raised when reading historical deals or positions fails."""

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message=message, details=details, code="MT5_QUERY_ERROR")


def setup_exception_handlers(app: FastAPI) -> None:
    """Registers standard JSON response format for all application errors."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(
            f"Handled error: {exc.code} - {exc.message} on {request.method} {request.url.path}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            {"loc": err["loc"], "msg": err["msg"], "type": err["type"]} for err in exc.errors()
        ]
        logger.info(f"Validation error on {request.method} {request.url.path}: {errors}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request payload validation failed",
                    "details": errors,
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            f"Unhandled server error on {request.method} {request.url.path}: {exc}", exc_info=True
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected server error occurred",
                },
            },
        )

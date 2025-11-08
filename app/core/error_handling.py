"""
Enhanced error handling and logging utilities
"""
import logging
import traceback
from typing import Optional, Dict, Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import sentry_sdk

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception"""
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(AppException):
    """Validation error exception"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=422, details=details)


class NotFoundException(AppException):
    """Resource not found exception"""
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=404, details=details)


class UnauthorizedException(AppException):
    """Unauthorized access exception"""
    def __init__(self, message: str = "Unauthorized", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=401, details=details)


class ForbiddenException(AppException):
    """Forbidden access exception"""
    def __init__(self, message: str = "Forbidden", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=403, details=details)


class ConflictException(AppException):
    """Resource conflict exception"""
    def __init__(self, message: str = "Resource conflict", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=409, details=details)


def log_error(error: Exception, request: Optional[Request] = None, context: Optional[Dict[str, Any]] = None):
    """
    Log error with context and send to Sentry if configured
    """
    error_context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc(),
    }
    
    if request:
        error_context.update({
            "path": request.url.path,
            "method": request.method,
            "client": request.client.host if request.client else None,
        })
    
    if context:
        error_context.update(context)
    
    # Log to application logger
    logger.error(f"Error occurred: {error_context}")
    
    # Send to Sentry if configured
    try:
        sentry_sdk.capture_exception(error, contexts={"custom": error_context})
    except Exception:
        pass  # Sentry not configured or error sending to Sentry


async def app_exception_handler(request: Request, exc: AppException):
    """Handle application exceptions"""
    log_error(exc, request)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.message,
                "type": type(exc).__name__,
                "details": exc.details,
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation exceptions with better formatting"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })
    
    log_error(exc, request, {"validation_errors": errors})
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "message": "Validation error",
                "type": "ValidationError",
                "details": {
                    "errors": errors
                }
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    log_error(exc, request)
    
    # Don't expose internal errors in production
    import os
    is_development = os.getenv("ENVIRONMENT", "development") == "development"
    
    error_detail = {
        "message": str(exc) if is_development else "Internal server error",
        "type": type(exc).__name__,
    }
    
    if is_development:
        error_detail["traceback"] = traceback.format_exc().split("\n")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": error_detail
        }
    )


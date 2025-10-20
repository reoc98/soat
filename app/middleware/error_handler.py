import logging
from typing import Callable

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


logger = logging.getLogger(__name__)
class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware.
    Catches unhandled exceptions and returns proper responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> object:
        """Handle errors globally."""
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            logger.error(
                f"Unhandled exception: {str(exc)}",
                exc_info=True,
                extra={"path": request.url.path, "method": request.method},
            )
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "internal_server_error",
                    "message": "An unexpected error occurred",
                    "request_id": getattr(request.state, "request_id", None),
                },
            )
import logging
from os import getenv
import time
from typing import Callable, Dict, Any, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import jwt
from jwt import PyJWKClient

from app.core.config import settings
from app.core.auth.utils import validate_cognito_token

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """Handles AWS Cognito JWT authentication and validation."""

    PUBLIC_PATHS = {
        "/health",
        "/api/docs",
        "/api/redoc",
        "/api/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/token/refresh",
        "/api/v1/health",
    }

    def __init__(self, app):
        super().__init__(app)
        self._jwks_url = (
            f"https://cognito-idp.{getenv('AWS_REGION')}.amazonaws.com/"
            f"{getenv('COGNITO_USER_POOL_ID')}/.well-known/jwks.json"
        )
        # self._jwks = _get_jwks(self._jwks_url)

    async def dispatch(self, request: Request, call_next: Callable):
        """Intercepts all requests and validates Cognito JWT tokens."""

        # CORS preflight requests
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Allow public routes
        if any(request.url.path.startswith(p) for p in self.PUBLIC_PATHS):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "auth_missing", "message": "Missing Bearer token"},
            )

        token = auth_header.split(" ")[1]

        try:
            payload = validate_cognito_token(token)

            # Attach user info to request
            request.state.user_id = payload.get("sub")
            request.state.username = payload.get("username") or payload.get("cognito:username")
            request.state.email = payload.get("email")
            request.state.groups = payload.get("cognito:groups", [])
            request.state.scopes = payload.get("scope", "").split() if "scope" in payload else []

            logger.debug(f"✅ Auth OK - user: {request.state.username}")

        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "token_expired", "message": "Token has expired"},
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "invalid_token", "message": "Token is invalid"},
            )
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "auth_error", "message": "Token validation error"},
            )

        return await call_next(request)

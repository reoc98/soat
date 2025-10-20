import logging
from os import getenv
import time
import requests
import jwt
from jwt import PyJWKClient
from jwt.algorithms import RSAAlgorithm
from typing import Dict, Any, Optional
from functools import lru_cache
from fastapi import HTTPException
from app.core.config import settings

logger = logging.getLogger(__name__)

_jwks_url = (
    f"https://cognito-idp.{getenv('AWS_REGION')}.amazonaws.com/"
    f"{getenv('COGNITO_USER_POOL_ID')}/.well-known/jwks.json"
)

@lru_cache(maxsize=1)
def _get_jwks(jwks_url: str) -> Dict[str, Any]:
    """Fetch JWKS from Cognito with caching (1 per process)."""
    try:
        response = requests.get(jwks_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        raise HTTPException(status_code=500, detail="Authentication service unavailable")


@lru_cache(maxsize=1)
def get_jwk_client(jwk_url: str) -> PyJWKClient:
    return PyJWKClient(jwk_url)


def validate_cognito_token(token: str) -> Dict[str, Any]:
    """Validate AWS Cognito JWT token and return payload."""
    
    # Decode without verifying to read claims
    unverified_header = jwt.get_unverified_header(token)
    unverified_claims = jwt.decode(token, options={"verify_signature": False})
    token_use = unverified_claims.get("token_use")
    issuer = unverified_claims.get("iss")
    
    if not token_use:
        raise jwt.InvalidTokenError('Missing "token_use" claim')
    if not issuer:
        raise jwt.InvalidTokenError('Missing "iss" claim')

    # Obtain public signing key
    # signing_key = jwk_client.get_signing_key_from_jwt(token).key
    jwks = _get_jwks(_jwks_url)
    key = next((k for k in jwks["keys"] if k["kid"] == unverified_header["kid"]), None)
    if not key:
        raise jwt.InvalidTokenError("Public key not found in JWKS")
    
    # Build public signing key
    signing_key = RSAAlgorithm.from_jwk(key)

    # Validate depending on token type
    if token_use == "id":
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=getenv('COGNITO_APP_CLIENT_ID'),
            issuer=issuer,
        )

    elif token_use == "access":
        # Access token: no tiene aud, solo validar issuer
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=issuer,
        )
    else:
        raise jwt.InvalidTokenError(f"Unknown token_use claim: {token_use}")

    return payload


def get_sponsor_from_claims(claims: Dict[str, Any]) -> Optional[str]:
    """Extract sponsor ID from JWT claims."""
    if "custom:sponsor" in claims:
        return claims["custom:sponsor"]
    return None


def get_user_role(claims: Dict[str, Any]) -> str:
    """Determine user role based on Cognito groups."""
    groups = claims.get("cognito:groups", [])
    if "admin" in groups:
        return "admin"
    elif "sponsor" in groups:
        return "sponsor"
    elif "insurer" in groups:
        return "insurer"
    return "user"

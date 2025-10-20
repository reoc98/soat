import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.auth.utils import (
    validate_cognito_token,
    get_sponsor_from_claims,
    get_user_role,
)
from jwt import PyJWKClient

logger = logging.getLogger(__name__)

class CognitoHTTPBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(
            scheme_name="BearerAuth",
            auto_error=auto_error,
        )

security = CognitoHTTPBearer()

_jwk_client = PyJWKClient(
    f"https://cognito-idp.{settings.AWS_REGION}.amazonaws.com/"
    f"{settings.COGNITO_USER_POOL_ID}/.well-known/jwks.json"
)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """Dependency to get current authenticated user."""

    if not credentials:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    token = credentials.credentials
    claims = validate_cognito_token(token)

    sponsor = get_sponsor_from_claims(claims)
    if not sponsor:
        raise HTTPException(status_code=401, detail="Sponsor not found") # in token

    role = get_user_role(claims)

    return {
        "sub": claims.get("sub"),
        "username": claims.get("cognito:username"),
        "email": claims.get("email"),
        "sponsor": sponsor,
        "role": role,
        "groups": claims.get("cognito:groups", []),
        "claims": claims,
    }


def require_role(required_role: str):
    """
    Factory function to create a dependency that requires a specific role.
    
    Usage:
        @router.post("/admin-only")
        async def admin_endpoint(user: Dict[str, Any] = Depends(require_role("admin"))):
            ...
    
    Args:
        required_role: The role required to access the endpoint (e.g., "admin", "user")
    
    Returns:
        Dependency function that validates the role
    """
    async def role_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if user.get("role") != required_role:
            logger.warning(
                f"Access denied for user {user.get('username')} - "
                f"Required role: {required_role}, User role: {user.get('role')}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}",
            )
        return user
    return role_checker


def require_any_role(*allowed_roles: str):
    """
    Factory function to create a dependency that requires any of the specified roles.
    
    Usage:
        @router.post("/admin-or-moderator")
        async def endpoint(user: Dict[str, Any] = Depends(require_any_role("admin", "moderator"))):
            ...
    
    Args:
        *allowed_roles: Variable number of allowed roles
    
    Returns:
        Dependency function that validates the user has at least one of the roles
    """
    async def role_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = user.get("role")
        if user_role not in allowed_roles:
            logger.warning(
                f"Access denied for user {user.get('username')} - "
                f"Required roles: {allowed_roles}, User role: {user_role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required one of: {', '.join(allowed_roles)}",
            )
        return user
    return role_checker


def require_admin():
    """
    Convenience dependency to require admin role.
    
    Usage:
        @router.post("/admin-only")
        async def admin_endpoint(user: Dict[str, Any] = Depends(require_admin())):
            ...
    """
    return require_role("admin")


def require_group(*allowed_groups: str):
    """
    Factory function to require user belongs to specific Cognito group(s).
    
    Uses cognito:groups from JWT token instead of custom role field.
    
    Usage:
        @router.post("/admin-action")
        async def endpoint(user: Dict[str, Any] = Depends(require_group("Admins"))):
            ...
    
    Args:
        *allowed_groups: One or more Cognito group names
    
    Returns:
        Dependency function that validates group membership
    """
    async def group_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_groups = user.get("groups", [])
        
        # Check if user belongs to any of the allowed groups
        if not any(group in user_groups for group in allowed_groups):
            logger.warning(
                f"Access denied for user {user.get('username')} - "
                f"Required groups: {allowed_groups}, User groups: {user_groups}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required group: {', '.join(allowed_groups)}",
            )
        return user
    return group_checker


def require_all_roles(*required_roles: str):
    """
    Factory function requiring ALL specified roles (AND logic).
    
    Usage:
        @router.post("/super-admin")
        async def endpoint(user: Dict[str, Any] = Depends(require_all_roles("admin", "supervisor"))):
            # User must have BOTH admin AND supervisor roles
            ...
    
    Note: This is useful if you store multiple roles in a list field.
    
    Args:
        *required_roles: All roles that must be present
    
    Returns:
        Dependency function that validates all roles
    """
    async def all_roles_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = user.get("role")
        user_groups = user.get("groups", [])
        
        # Check if user has all required roles (in either role field or groups)
        has_all_roles = all(
            role == user_role or role in user_groups 
            for role in required_roles
        )
        
        if not has_all_roles:
            logger.warning(
                f"Access denied for user {user.get('username')} - "
                f"Required ALL roles: {required_roles}, User role: {user_role}, Groups: {user_groups}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required all of: {', '.join(required_roles)}",
            )
        return user
    return all_roles_checker


def with_audit_log(action: str):
    """
    Decorator factory for automatic audit logging on endpoints.
    
    Usage:
        @router.post("/sensitive-action")
        @with_audit_log("BLOCK_FORM")
        async def endpoint(user: Dict[str, Any] = Depends(require_admin())):
            ...
    
    Args:
        action: Action name for logging
    
    Returns:
        Dependency that logs the action
    """
    async def audit_logger(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        logger.info(
            f"AUDIT - {action}",
            extra={
                "action": action,
                "user": user.get("username"),
                "user_id": user.get("sub"),
                "role": user.get("role"),
                "sponsor": user.get("sponsor"),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        return user
    return audit_logger


async def require_tenant_access(
    tenant_id: str, user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Ensure user has access to a specific tenant."""
    if user["tenant_id"] != tenant_id and user["role"] not in ["admin", "insurer"]:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")
    return user

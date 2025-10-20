from typing import Optional, Dict, Any
from fastapi import status


class AppException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "APP_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AppException):
    """Raised when validation fails."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class AuthenticationError(AppException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class AuthorizationError(AppException):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class TenantNotFoundError(AppException):
    """Raised when tenant cannot be found."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        super().__init__(
            message=f"Tenant '{tenant_id}' not found",
            error_code="TENANT_NOT_FOUND",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class TenantConfigurationError(AppException):
    """Raised when tenant configuration is invalid."""

    def __init__(self, tenant_id: str, message: str):
        super().__init__(
            message=message,
            error_code="TENANT_CONFIG_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"tenant_id": tenant_id},
        )


class DatabaseError(AppException):
    """Raised when database operation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class ResourceNotFoundError(AppException):
    """Raised when resource cannot be found."""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"{resource_type} with ID '{resource_id}' not found",
            error_code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={
                "resource_type": resource_type,
                "resource_id": resource_id
            },
        )


class ConflictError(AppException):
    """Raised when resource conflict occurs."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFLICT_ERROR",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class ExternalServiceError(AppException):
    """Raised when external service fails."""

    def __init__(
        self,
        service_name: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=f"{service_name.upper()}_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details or {"service": service_name},
        )


class RUNTError(ExternalServiceError):
    """Raised when RUNT API fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("RUNT", message, details)


class SegurosMundialError(ExternalServiceError):
    """Raised when Seguros Mundial API fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("SEGUROS_MUNDIAL", message, details)


class BusinessRuleError(AppException):
    """Raised when business rule is violated."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="BUSINESS_RULE_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )
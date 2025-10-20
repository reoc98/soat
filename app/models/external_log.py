from sqlalchemy import Index, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import VARCHAR, TEXT, DECIMAL
from typing import Optional
import enum

from app.models.base import Base, TimestampMixin


class RequestStatus(str, enum.Enum):
    """Request status enum."""
    
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"


class ExternalServiceLog(Base, TimestampMixin):
    """
    External service log reference table (MySQL).
    Stores metadata and reference to full payload in DynamoDB.
    """

    __tablename__ = "external_service_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Service information
    service_name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    endpoint: Mapped[str] = mapped_column(VARCHAR(500), nullable=False)
    http_method: Mapped[str] = mapped_column(VARCHAR(10), nullable=False)
    
    # Request metadata
    status: Mapped[RequestStatus] = mapped_column(
        SQLEnum(RequestStatus),
        nullable=False,
        index=True
    )
    status_code: Mapped[Optional[int]] = mapped_column(nullable=True)
    response_time_ms: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    # DynamoDB reference
    dynamodb_log_id: Mapped[str] = mapped_column(
        VARCHAR(100), nullable=False, unique=True, index=True
    )
    
    # Additional metadata
    client_id: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)

    # Error information (if any)
    error_message: Mapped[Optional[str]] = mapped_column(TEXT, nullable=True)

    def __repr__(self) -> str:
        return f"<ExternalServiceLog(id={self.id}, service={self.service_name}, status={self.status}, dynamodb_id={self.dynamodb_log_id})>"

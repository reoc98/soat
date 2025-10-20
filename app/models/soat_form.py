"""
SOAT Form Model

Manages SOAT form numbers and their lifecycle states.
Forms are assigned to sessions during pre-expedition and must not be reused.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from enum import Enum
from typing import Optional

from app.models.base import Base


class FormStatus(str, Enum):
    """Status of a SOAT form."""
    
    AVAILABLE = "available"  # Form is available for use
    RESERVED = "reserved"    # Form is temporarily reserved for a session
    USED = "used"           # Form has been used for pre-expedition/expedition
    BLOCKED = "blocked"     # Form is blocked (manual intervention)
    EXPIRED = "expired"     # Reservation expired without use


class SoatForm(Base):
    """
    SOAT Form management.
    
    Manages form numbers obtained from Mundial Seguros and tracks their usage
    to prevent duplicate assignments.
    """
    
    __tablename__ = "forms"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Form identification
    form_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
        comment="Form number from Mundial Seguros"
    )
    
    # Mundial Seguros codes
    cod_suc: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Sucursal code"
    )
    
    cod_agente: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Agent code"
    )
    
    cod_pto_vta: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Point of sale code"
    )
    
    # Status tracking
    status: Mapped[FormStatus] = mapped_column(
        SQLEnum(FormStatus, name="formstatus", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=FormStatus.AVAILABLE,
        index=True,
        comment="Current status of the form"
    )
    
    # Session association
    session_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="Insurance session ID using this form"
    )
    
    # Timestamps
    reserved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="When form was reserved"
    )
    
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="When form was used"
    )
    
    blocked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="When form was blocked"
    )
    
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
        comment="When reservation expires (if reserved)"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="When form was added to database"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="Last update timestamp"
    )
    
    # Additional tracking
    blocked_reason: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Reason for blocking (if blocked)"
    )
    
    notes: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Additional notes"
    )
    
    def __repr__(self) -> str:
        return f"<SoatForm(form_number={self.form_number}, status={self.status}, session={self.session_slug})>"
    
    def is_available(self) -> bool:
        """Check if form is available for use."""
        return self.status == FormStatus.AVAILABLE
    
    def is_reserved(self) -> bool:
        """Check if form is reserved."""
        return self.status == FormStatus.RESERVED
    
    def is_used(self) -> bool:
        """Check if form has been used."""
        return self.status == FormStatus.USED
    
    def is_blocked(self) -> bool:
        """Check if form is blocked."""
        return self.status == FormStatus.BLOCKED
    
    def can_be_assigned(self) -> bool:
        """Check if form can be assigned to a session."""
        return self.status in [FormStatus.AVAILABLE, FormStatus.EXPIRED]

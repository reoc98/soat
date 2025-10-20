from sqlalchemy import Boolean, Index, text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import VARCHAR
from typing import List, Optional
import enum

from app.models.base import Base, TimestampMixin


class SponsorStatus(str, enum.Enum):
    """Sponsor status enum."""

    active = "active"
    inactive = "inactive"
    suspended = "suspended"
    archived = "archived"


class Sponsor(Base, TimestampMixin):
    """Master table: Sponsor configuration."""

    __tablename__ = "sponsors"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(
        VARCHAR(50), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    legal_name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    status: Mapped[SponsorStatus] = mapped_column(
        SQLEnum(SponsorStatus),
        default=SponsorStatus.active,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False)
    contact_email: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    contact_phone: Mapped[Optional[str]] = mapped_column(VARCHAR(20), nullable=True)


    def __repr__(self) -> str:
        return f"<Sponsor(slug={self.slug}, name={self.name})>"

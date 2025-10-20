from sqlalchemy import Boolean, Index, text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import VARCHAR
from typing import List, Optional
import enum

from app.models.base import AuditMixin, Base, TimestampMixin

class UserRoles(str, enum.Enum):
    """User roles enum."""

    admin = "admin"
    insured = "insured"
    sponsor = "sponsor"

class User(Base, TimestampMixin):
    """Master table: User configuration."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    password: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    fullname: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    role: Mapped[UserRoles] = mapped_column(
        SQLEnum(UserRoles),
        default=UserRoles.sponsor,
        nullable=False,
    )
    status: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


    def __repr__(self) -> str:
        return f"<User(email={self.email}, fullname={self.fullname}, role={self.role})>"
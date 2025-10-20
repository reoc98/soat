from sqlalchemy import Index, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import VARCHAR, DECIMAL
from typing import Optional
import enum

from app.models.base import Base, TimestampMixin


class DocumentType(Base, TimestampMixin):
    """Document type table - stores types of identification documents."""

    __tablename__ = "document_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(VARCHAR(8), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    description: Mapped[str] = mapped_column(VARCHAR(255), nullable=True)
    soat_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    soat_code: Mapped[Optional[str]] = mapped_column(VARCHAR(8), nullable=True)
    runt_code: Mapped[Optional[str]] = mapped_column(VARCHAR(8), nullable=True)
    status: Mapped[int] = mapped_column(default=1, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<DocumentType(code={self.code}, name={self.name}, description={self.description})>"
from sqlalchemy import Index, ForeignKey, Enum as SQLEnum, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import VARCHAR
from typing import Optional
from datetime import date

from app.models.base import AuditMixin, Base, TimestampMixin
from app.models.document_type import DocumentType
from app.models.city import City
from app.models.gender import Gender


class Client(Base, TimestampMixin):
    """Client table - stores customer information."""

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_type_id: Mapped[int] = mapped_column(
        ForeignKey("document_types.id"), nullable=False
    )
    document_number: Mapped[str] = mapped_column(
        VARCHAR(50), nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(VARCHAR(255), nullable=True)
    first_name: Mapped[str] = mapped_column(VARCHAR(125), nullable=True)
    middle_name: Mapped[str] = mapped_column(VARCHAR(125), nullable=True)
    last_name: Mapped[str] = mapped_column(VARCHAR(125), nullable=True)
    second_last_name: Mapped[Optional[str]] = mapped_column(VARCHAR(125), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(VARCHAR(20), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    city_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("cities.id", name="clients_ibfk_2"),
        nullable=True,
        index=True
    )
    gender_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("genders.id", name="clients_ibfk_3"),
        nullable=True
    )

    # relationships
    document_type: Mapped[DocumentType] = relationship()
    city: Mapped[City] = relationship("City")
    gender: Mapped[Gender] = relationship("Gender")

    def __repr__(self) -> str:
        return f"<Client(document_type={self.document_type_id}, document_number={self.document_number}, name={self.first_name} {self.last_name})>"


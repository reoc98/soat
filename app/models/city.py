from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import VARCHAR

from app.models.base import Base, TimestampMixin
from app.models.department import Department


class City(Base, TimestampMixin):
    """City table - stores city information."""

    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(VARCHAR(5), nullable=False, unique=True, index=True)
    code_department: Mapped[str] = mapped_column(
        ForeignKey("departments.code", name="cities_ibfk_1"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    status: Mapped[int] = mapped_column(nullable=False, default=True)

    # relationships
    department: Mapped[Department] = relationship("Department")

    def __repr__(self) -> str:
        return f"<City(code={self.code}, name={self.name}, status={self.status}, department={self.department})>"

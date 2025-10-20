from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import VARCHAR, INTEGER
from app.models.base import Base, TimestampMixin


class Department(Base, TimestampMixin):
    """Department table - stores department information."""

    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(VARCHAR(5), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    status: Mapped[int] = mapped_column(INTEGER, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<Department(code={self.code}, name={self.name}, status={self.status})>"

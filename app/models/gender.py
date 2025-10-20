from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import VARCHAR
from app.models.base import Base, TimestampMixin


class Gender(Base, TimestampMixin):
    """Gender table - stores gender information."""

    __tablename__ = "genders"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(VARCHAR(5), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    status: Mapped[int] = mapped_column(nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<Gender(code={self.code}, name={self.name}, status={self.status})>"

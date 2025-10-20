from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import VARCHAR, TINYINT
from typing import TYPE_CHECKING, Optional

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.quote_product import QuoteProduct


class Product(Base, TimestampMixin):
    """Product table - stores available insurance products."""
    
    __tablename__ = "products"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    mandatory: Mapped[bool] = mapped_column(TINYINT(1), nullable=False, default=False)
    has_options: Mapped[bool] = mapped_column(TINYINT(1), nullable=True, default=True)
    status: Mapped[bool] = mapped_column(TINYINT(1), nullable=False, default=True)
    
    # Relationships
    quote_products: Mapped[list["QuoteProduct"]] = relationship(
        "QuoteProduct",
        back_populates="product",
        # cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_code", "code"),
        Index("idx_status", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<Product(code={self.code}, name={self.name}, mandatory={self.mandatory}, status={self.status})>"

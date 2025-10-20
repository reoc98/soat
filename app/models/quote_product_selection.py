"""
Quote Product Selection Model

Stores the user's selected plan for each product in their quote.
"""

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.quote_product import QuoteProduct
    from app.models.quote_product_option import QuoteProductOption


class QuoteProductSelection(Base, TimestampMixin):
    """Quote product selection table - stores user's selected plan for each product."""
    
    __tablename__ = "quote_product_selection"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    quote_product_id: Mapped[int] = mapped_column(
        ForeignKey("quote_products.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    option_id: Mapped[int] = mapped_column(
        ForeignKey("quote_product_options.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Relationships
    quote_product: Mapped["QuoteProduct"] = relationship("QuoteProduct", back_populates="selection")
    option: Mapped["QuoteProductOption"] = relationship("QuoteProductOption")
    
    __table_args__ = (
        Index("idx_quote_product_selection_quote_product_id", "quote_product_id"),
        Index("idx_quote_product_selection_option_id", "option_id"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<QuoteProductSelection(id={self.id}, quote_product_id={self.quote_product_id}, "
            f"option_id={self.option_id})>"
        )

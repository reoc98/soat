"""
Quote Product Options Model

Stores plan options for insurance products that have configurable options.
For example, AP (Accidentes Personales) has different plans (PLATA, PLATINO, GOLD).
"""

from sqlalchemy import JSON, Boolean, ForeignKey, Index, DECIMAL, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import VARCHAR, TINYINT
from typing import TYPE_CHECKING, Optional
from enum import Enum

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.quote_product import QuoteProduct


class OptionAvailabilityStatus(str, Enum):
    """Availability status for quote product options."""
    AVAILABLE = "available"  # Plan is available for the selected vehicle class
    UNAVAILABLE_CLASS = "unavailable_class"  # Plan not available for the vehicle class
    INACTIVE = "inactive"  # Plan is inactive/disabled


class QuoteProductOption(Base, TimestampMixin):
    """Quote product options table - stores plan options for products."""
    
    __tablename__ = "quote_product_options"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    quote_product_id: Mapped[int] = mapped_column(
        ForeignKey("quote_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    plan_name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    price: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=True)
    coverage: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    availability_status: Mapped[str] = mapped_column(
        SQLEnum(OptionAvailabilityStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=OptionAvailabilityStatus.AVAILABLE,
        index=True
    )
    
    # Relationships
    quote_product: Mapped["QuoteProduct"] = relationship("QuoteProduct", back_populates="options")
    
    __table_args__ = (
        Index("idx_quote_product_options_quote_product_id", "quote_product_id"),
        Index("idx_quote_product_options_plan_name", "plan_name"),
        Index("idx_quote_product_options_availability_status", "availability_status"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<QuoteProductOption(id={self.id}, quote_product_id={self.quote_product_id}, "
            f"plan_name={self.plan_name}, price={self.price}, coverage={self.coverage})>"
        )

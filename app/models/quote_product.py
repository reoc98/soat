from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import VARCHAR, TINYINT
from typing import Optional, TYPE_CHECKING, List

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.external_log import ExternalServiceLog
    from app.models.insurance_session import InsuranceSession
    from app.models.product import Product
    from app.models.quote_product_option import QuoteProductOption
    from app.models.quote_product_selection import QuoteProductSelection

class QuoteProduct(Base, TimestampMixin):
    """Quote product table - stores products associated with quotes."""
    
    __tablename__ = "quote_products"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("insurance_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
        index=True
    )
    external_service_log_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("external_service_logs.id"),
        nullable=True
    )
    status: Mapped[bool] = mapped_column(TINYINT(1), nullable=False, default=True)
    
    # Relationship
    session: Mapped["InsuranceSession"] = relationship("InsuranceSession", back_populates="quote_products")
    product: Mapped["Product"] = relationship("Product", back_populates="quote_products")
    external_service_log: Mapped["ExternalServiceLog"] = relationship("ExternalServiceLog")
    options: Mapped[List["QuoteProductOption"]] = relationship(
        "QuoteProductOption",
        back_populates="quote_product",
        # cascade="all, delete-orphan"
    )
    selection: Mapped[Optional["QuoteProductSelection"]] = relationship(
        "QuoteProductSelection",
        back_populates="quote_product",
        uselist=False
    )
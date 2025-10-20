from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import VARCHAR, INTEGER
from typing import Optional, TYPE_CHECKING

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.insurance_session import InsuranceSession


class VehicleHomologation(Base, TimestampMixin):
    """Vehicle homologation table - stores homologation data from RUNT."""
    
    __tablename__ = "vehicle_homologations"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("insurance_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Homologation details from RUNT
    class_code: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)
    class_description: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    transport_type_code: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)
    brand_code: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)
    line_code: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)
    destination_code: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)
    
    # Relationship
    session: Mapped["InsuranceSession"] = relationship("InsuranceSession", back_populates="homologations")
    
    def __repr__(self) -> str:
        return f"<VehicleHomologation(session_id={self.session_id}, class_code={self.class_code}, brand_code={self.brand_code}, line_code={self.line_code})>"

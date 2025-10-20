"""
Plan AP Model

Stores available AP insurance plans from Mundial Seguros.
"""

from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import VARCHAR, DECIMAL
from typing import TYPE_CHECKING, List

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.plan_vehicle_class import PlanVehicleClass


class PlanAP(Base, TimestampMixin):
    """AP Plans table - stores available AP insurance plans."""
    
    __tablename__ = "plans_ap"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    description: Mapped[str] = mapped_column(VARCHAR(500), nullable=True)
    # insured_value: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=True)
    # policy_value: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=True)
    status: Mapped[bool] = mapped_column(nullable=False, default=True)
    
    # Relationships
    vehicle_classes: Mapped[List["PlanVehicleClass"]] = relationship(
        "PlanVehicleClass",
        back_populates="plan",
        # cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_plan_ap_code", "code"),
        Index("idx_plan_ap_status", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<PlanAP(id={self.id}, code={self.code}, name={self.name})>"

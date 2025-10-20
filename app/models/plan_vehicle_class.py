"""
Plan Vehicle Class Association Model

Many-to-many relationship between AP plans and vehicle classes.
Determines which AP plans are available for which vehicle classes.
"""

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.plan_ap import PlanAP
    from app.models.vehicle_class import VehicleClass


class PlanVehicleClass(Base, TimestampMixin):
    """Plan Vehicle Class Association table - links plans to allowed vehicle classes."""
    
    __tablename__ = "plan_vehicle_classes"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plans_ap.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    vehicle_class_id: Mapped[int] = mapped_column(
        ForeignKey("vehicle_classes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    status: Mapped[bool] = mapped_column(nullable=False, default=True)
    
    # Relationships
    plan: Mapped["PlanAP"] = relationship("PlanAP", back_populates="vehicle_classes")
    vehicle_class: Mapped["VehicleClass"] = relationship("VehicleClass", back_populates="plan_associations")
    
    __table_args__ = (
        UniqueConstraint("plan_id", "vehicle_class_id", name="uq_plan_vehicle_class"),
        Index("idx_plan_vehicle_class_plan_id", "plan_id"),
        Index("idx_plan_vehicle_class_vehicle_class_id", "vehicle_class_id"),
    )
    
    def __repr__(self) -> str:
        return f"<PlanVehicleClass(plan_id={self.plan_id}, vehicle_class_id={self.vehicle_class_id})>"

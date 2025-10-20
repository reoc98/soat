"""
Vehicle Class Model

Stores vehicle class codes and descriptions used for insurance classification.
"""

from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import VARCHAR
from typing import TYPE_CHECKING, List

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.plan_vehicle_class import PlanVehicleClass


class VehicleClass(Base, TimestampMixin):
    """Vehicle Classes table - stores vehicle classification codes."""
    
    __tablename__ = "vehicle_classes"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    status: Mapped[bool] = mapped_column(nullable=False, default=True)
    
    # Relationships
    plan_associations: Mapped[List["PlanVehicleClass"]] = relationship(
        "PlanVehicleClass",
        back_populates="vehicle_class",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_vehicle_class_code", "code"),
        Index("idx_vehicle_class_status", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<VehicleClass(id={self.id}, code={self.code}, description={self.description})>"

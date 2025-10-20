from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.insurance_session import InsuranceSession
    from app.models.vehicle_homologation import VehicleHomologation


class VehicleHomologationSelection(Base, TimestampMixin):
    """Vehicle homologation selection table - stores the selected homologation for a session."""
    
    __tablename__ = "vehicle_homologations_selection"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("insurance_sessions.id", name="vehicle_homologations_selection_ibfk_1"),
        nullable=False,
        index=True
    )
    vehicle_class_id: Mapped[int] = mapped_column(
        ForeignKey("vehicle_homologations.id", name="vehicle_homologations_selection_ibfk_2"),
        nullable=False,
        index=True
    )
    
    # Relationships
    session: Mapped["InsuranceSession"] = relationship("InsuranceSession")
    vehicle_homologation: Mapped["VehicleHomologation"] = relationship("VehicleHomologation")
    
    def __repr__(self) -> str:
        return f"<VehicleHomologationSelection(session_id={self.session_id}, vehicle_class_id={self.vehicle_class_id})>"

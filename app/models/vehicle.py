from typing import Optional
from sqlalchemy import VARCHAR, DECIMAL, INT, TIMESTAMP, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class Vehicle(Base, TimestampMixin):
    """Vehicle table - stores detailed vehicle information."""

    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    consultation_id: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    consultation_success: Mapped[bool] = mapped_column(default=False)
    service_observation: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)

    license_plate: Mapped[str] = mapped_column(VARCHAR(20), nullable=False, unique=True, index=True)

    # Vehicle characteristics
    service_type_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    service_type: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)

    vehicle_class_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    vehicle_class: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)

    brand_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)

    line_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    line: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)

    model_year: Mapped[Optional[int]] = mapped_column(nullable=True)

    color_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    color: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)

    serial_number: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)
    engine_number: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)
    chassis_number: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)
    vin_number: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)

    engine_cc: Mapped[Optional[int]] = mapped_column(nullable=True)
    tonnage: Mapped[Optional[float]] = mapped_column(DECIMAL(6, 2), nullable=True)
    gross_weight: Mapped[Optional[int]] = mapped_column(nullable=True)
    seats: Mapped[Optional[int]] = mapped_column(nullable=True)

    body_type_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    body_type: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)

    fuel_type_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    fuel_type: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)

    vehicle_state: Mapped[Optional[str]] = mapped_column(VARCHAR(20), nullable=True)
    transit_authority: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)

    __table_args__ = (
        Index("idx_vehicle_license_plate", "license_plate"),
    )

    def __repr__(self) -> str:
        return (
            f"<Vehicle(plate={self.license_plate}, brand={self.brand}, "
            f"line={self.line}, model_year={self.model_year})>"
        )

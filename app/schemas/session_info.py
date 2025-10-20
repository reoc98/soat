"""
Session Information Schemas

Pydantic schemas for session information endpoint.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class OwnerInfoResponse(BaseModel):
    """Owner information response (visible only in pre-quote states)."""
    
    client_id: int
    document_type: Optional[str] = None
    document_type_name: Optional[str] = None
    document_number: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    second_last_name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "client_id": 123,
                "document_type": "CC",
                "document_type_name": "Cédula de Ciudadanía",
                "document_number": "1234567890",
                "first_name": "Juan",
                "last_name": "Pérez",
                "second_last_name": "García",
                "full_name": "Juan Pérez García",
                "email": "juan.perez@example.com",
                "phone": "3001234567",
                "address": "Calle 123 #45-67",
                "city": "Bogotá",
                "birth_date": "1990-01-15",
                "gender": "Masculino"
            }
        }


class VehicleHomologationInfo(BaseModel):
    """Vehicle homologation information."""
    
    id: int
    class_code: str
    class_description: Optional[str] = None
    transport_type_code: Optional[str] = None
    brand_code: Optional[str] = None
    line_code: Optional[str] = None
    destination_code: Optional[str] = None


class VehicleInfoResponse(BaseModel):
    """Vehicle information response (visible only in pre-quote states)."""
    
    vehicle_id: int
    license_plate: str
    brand: Optional[str] = None
    line: Optional[str] = None
    model_year: Optional[int] = None
    vehicle_class: Optional[str] = None
    vehicle_class_id: Optional[int] = None
    service_type: Optional[str] = None
    service_type_id: Optional[int] = None
    color: Optional[str] = None
    engine_cc: Optional[int] = None
    fuel_type: Optional[str] = None
    chassis_number: Optional[str] = None
    engine_number: Optional[str] = None
    vin_number: Optional[str] = None
    serial_number: Optional[str] = None
    seats: Optional[int] = None
    tonnage: Optional[float] = None
    gross_weight: Optional[float] = None
    body_type: Optional[str] = None
    homologations: List[VehicleHomologationInfo] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "vehicle_id": 456,
                "license_plate": "ABC123",
                "brand": "TOYOTA",
                "line": "COROLLA",
                "model_year": 2020,
                "vehicle_class": "Automóvil",
                "vehicle_class_id": "05",
                "service_type": "Particular",
                "service_type_id": 1,
                "color": "Blanco",
                "engine_cc": 1800,
                "fuel_type": "Gasolina",
                "homologations": [
                    {
                        "id": 1,
                        "class_code": "05",
                        "class_description": "AUTOMOVIL",
                        "transport_type_code": "01",
                        "brand_code": "TOY",
                        "line_code": "COR",
                        "destination_code": "01"
                    }
                ]
            }
        }


class SessionInfoResponse(BaseModel):
    """
    Session information response with conditional visibility.
    
    Owner and vehicle information is only included when session is in
    pre-quote states (created, validating, validated, validation_failed).
    
    For post-quote states, only session status and metadata is returned.
    """
    
    session_slug: str = Field(..., description="Session UUID slug")
    session_id: int = Field(..., description="Session database ID")
    status: str = Field(..., description="Current session status code")
    status_display: str = Field(..., description="Human-readable status")
    is_owner: bool = Field(..., description="Whether ownership is validated")
    created_at: str = Field(..., description="Session creation timestamp")
    updated_at: str = Field(..., description="Session last update timestamp")
    can_view_details: bool = Field(
        ...,
        description="Whether owner/vehicle details are visible (true only in pre-quote states)"
    )
    owner_info: Optional[OwnerInfoResponse] = Field(
        None,
        description="Owner information (only visible in pre-quote states)"
    )
    vehicle_info: Optional[VehicleInfoResponse] = Field(
        None,
        description="Vehicle information (only visible in pre-quote states)"
    )
    message: str = Field(..., description="Contextual message based on session status")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "summary": "Pre-quote state (details visible)",
                    "value": {
                        "session_slug": "550e8400-e29b-41d4-a716-446655440000",
                        "session_id": 123,
                        "status": "validated",
                        "status_display": "Propietario validado",
                        "is_owner": True,
                        "created_at": "2025-10-18T10:00:00",
                        "updated_at": "2025-10-18T10:05:00",
                        "can_view_details": True,
                        "owner_info": {
                            "client_id": 123,
                            "document_type": "CC",
                            "document_number": "1234567890",
                            "full_name": "Juan Pérez García"
                        },
                        "vehicle_info": {
                            "vehicle_id": 456,
                            "license_plate": "ABC123",
                            "brand": "TOYOTA",
                            "line": "COROLLA",
                            "model_year": 2020,
                            "homologations": []
                        },
                        "message": "Propietario validado exitosamente. Puede proceder a cotizar."
                    }
                },
                {
                    "summary": "Post-quote state (details hidden)",
                    "value": {
                        "session_slug": "550e8400-e29b-41d4-a716-446655440000",
                        "session_id": 123,
                        "status": "quoted",
                        "status_display": "Cotización generada",
                        "is_owner": True,
                        "created_at": "2025-10-18T10:00:00",
                        "updated_at": "2025-10-18T10:15:00",
                        "can_view_details": False,
                        "owner_info": None,
                        "vehicle_info": None,
                        "message": "Información de propietario y vehículo no disponible. La sesión está en proceso de cotización o posterior."
                    }
                }
            ]
        }

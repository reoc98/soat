from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum


class DocumentTypeEnum(str, Enum):
    """Document type enum for API."""
    
    CC = "CC"
    CE = "CE"
    TI = "TI"
    NIT = "NIT"
    PASSPORT = "PASSPORT"


class PreQuoteRequest(BaseModel):
    """Pre-quote validation request schema."""
    
    document_type: DocumentTypeEnum = Field(..., description="Document type")
    document_number: str = Field(..., min_length=5, max_length=50, description="Document number")
    license_plate: str = Field(..., min_length=6, max_length=10, description="Vehicle license plate")

    @validator('document_number')
    def validate_document_number(cls, v):
        """Remove whitespace and validate format."""
        return v.strip().upper()
    
    @validator('license_plate')
    def validate_license_plate(cls, v):
        """Remove whitespace and validate format."""
        return v.strip().upper().replace("-", "").replace(" ", "")

    class Config:
        json_schema_extra = {
            "example": {
                "document_type": "CC",
                "document_number": "1234567890",
                "license_plate": "ABC123"
            }
        }


class OwnerInfo(BaseModel):
    """Owner information schema."""
    
    client_id: int
    document_type: str
    document_number: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    second_last_name: Optional[str] = None
    full_name: str


class VehicleInfo(BaseModel):
    """Vehicle information schema."""
    
    license_plate: str
    brand: str
    model: str
    year: int
    vehicle_class: Optional[str] = None
    vehicle_type: Optional[str] = None
    engine_number: Optional[str] = None
    chassis_number: Optional[str] = None
    cylinder_capacity: Optional[int] = None
    fuel_type: Optional[str] = None
    color: Optional[str] = None
    service_type: Optional[str] = None
    homologations: Optional[List[Dict[str, Any]]] = []


class PreQuoteResponse(BaseModel):
    """Pre-quote validation response schema."""
    
    is_owner: bool = Field(..., description="Whether the person is the vehicle owner")
    message: str = Field(..., description="Response message")
    owner_info: Optional[OwnerInfo] = Field(None, description="Owner information")
    vehicle_info: Optional[VehicleInfo] = Field(None, description="Vehicle information")
    session_id: Optional[str] = Field(None, description="Session ID for tracking")
    # client_id: Optional[int] = Field(None, description="Client ID in database")

    class Config:
        json_schema_extra = {
            "example": {
                "is_owner": True,
                "message": "Owner validated successfully",
                "owner_info": {
                    "client_id": 123,
                    "document_type": "CC",
                    "document_number": "1234567890",
                    "first_name": "Juan",
                    "last_name": "Pérez",
                    "full_name": "Juan Pérez"
                },
                "vehicle_info": {
                    "license_plate": "ABC123",
                    "brand": "Toyota",
                    "model": "Corolla",
                    "year": 2020,
                    "vehicle_class": "Automóvil",
                    "color": "Blanco",
                    "homologations": [
                        {
                            "id": 1,
                            "code": "05",
                            "description": "AUTOMOVIL"
                        }
                    ]
                },
                "session_id": "2c536559-cff0-400f-9ac0-a2eea2ce6c6b",
            }
        }

"""
SOAT Forms Schemas

Pydantic schemas for SOAT forms management endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class FormInfo(BaseModel):
    """Information about a single SOAT form."""
    
    id: int
    form_number: str
    status: str
    cod_suc: str
    cod_agente: str
    cod_pto_vta: str
    session_id: Optional[int] = None
    session_slug: Optional[str] = None
    sponsor: str
    reserved_at: Optional[datetime] = None
    used_at: Optional[datetime] = None
    blocked_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    blocked_reason: Optional[str] = None
    notes: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "form_number": "92432248",
                "status": "available",
                "cod_suc": "14",
                "cod_agente": "13158",
                "cod_pto_vta": "41647",
                "session_id": None,
                "session_slug": None,
                "sponsor": "rappi",
                "reserved_at": None,
                "used_at": None,
                "blocked_at": None,
                "expires_at": None,
                "created_at": "2025-10-17T10:00:00",
                "blocked_reason": None,
                "notes": None
            }
        }


class FetchFormsResponse(BaseModel):
    """Response from fetching forms from external service."""
    
    success: bool
    new_forms: int
    existing_forms: int
    total_fetched: int
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "new_forms": 25,
                "existing_forms": 5,
                "total_fetched": 30,
                "message": "Formularios sincronizados exitosamente"
            }
        }


class FormsStatsResponse(BaseModel):
    """Statistics about SOAT forms."""
    
    total: int
    available: int
    reserved: int
    used: int
    blocked: int
    expired: int
    needs_refill: bool
    
    class Config:
        json_schema_extra = {
            "example": {
                "total": 50,
                "available": 35,
                "reserved": 5,
                "used": 8,
                "blocked": 1,
                "expired": 1,
                "needs_refill": False
            }
        }


class BlockFormRequest(BaseModel):
    """Request to block a form."""
    
    form_number: str = Field(
        ...,
        description="Form number to block",
        min_length=1
    )
    reason: str = Field(
        ...,
        description="Reason for blocking",
        min_length=1,
        max_length=255
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "form_number": "92432248",
                "reason": "Form number reported as invalid"
            }
        }


class UnblockFormRequest(BaseModel):
    """Request to unblock a form."""
    
    form_number: str = Field(
        ...,
        description="Form number to unblock",
        min_length=1
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "form_number": "92432248"
            }
        }


class FormActionResponse(BaseModel):
    """Response for form actions (block, unblock, etc)."""
    
    success: bool
    message: str
    form: FormInfo
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Formulario bloqueado exitosamente",
                "form": {
                    "id": 1,
                    "form_number": "92432248",
                    "status": "blocked",
                    "cod_suc": "14",
                    "cod_agente": "13158",
                    "cod_pto_vta": "41647",
                    "sponsor": "rappi",
                    "blocked_at": "2025-10-17T10:30:00",
                    "blocked_reason": "Form number reported as invalid",
                    "created_at": "2025-10-17T10:00:00"
                }
            }
        }


class ListFormsResponse(BaseModel):
    """Response for listing forms."""
    
    forms: List[FormInfo]
    total: int
    page: int
    page_size: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "forms": [],
                "total": 50,
                "page": 1,
                "page_size": 20
            }
        }

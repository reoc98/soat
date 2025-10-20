"""
Expedition Schemas

Pydantic schemas for expedition endpoints (plan selection, pre-expedition, and final expedition).
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional


class PlanSelection(BaseModel):
    """Single plan selection for a product."""
    
    product_code: str = Field(
        ...,
        description="Product code (SOAT, AP, RCE, etc.)",
        min_length=1,
        max_length=50
    )
    option_id: int = Field(
        ...,
        description="ID of the plan option to select",
        gt=0
    )
    
    @validator('product_code')
    def validate_product_code(cls, v):
        """Remove whitespace and convert to uppercase."""
        return v.strip().upper()
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_code": "SOAT",
                "option_id": 125
            }
        }


class SelectPlanRequest(BaseModel):
    """Request to select plans for one or multiple products."""
    
    selections: List[PlanSelection] = Field(
        ...,
        description="List of plan selections (one per product)",
        min_length=1
    )
    
    @validator('selections')
    def validate_unique_products(cls, v):
        """Ensure each product appears only once."""
        product_codes = [s.product_code for s in v]
        if len(product_codes) != len(set(product_codes)):
            raise ValueError('Duplicate product_code found. Each product can only be selected once.')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "selections": [
                    {
                        "product_code": "SOAT",
                        "option_id": 125
                    },
                    {
                        "product_code": "AP",
                        "option_id": 124
                    }
                ]
            }
        }


class SelectedPlanInfo(BaseModel):
    """Information about a selected plan."""
    
    product_code: str
    product_name: str
    selected_option: Dict[str, Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_code": "SOAT",
                "product_name": "Seguro Obligatorio de Accidentes de Tránsito",
                "selected_option": {
                    "option_id": 125,
                    "plan_name": "SOAT Standard",
                    "price": 250710.0,
                    "coverage": {
                        "premium_value": 174900,
                        "total_to_pay": 250710
                    }
                }
            }
        }


class SelectPlanResponse(BaseModel):
    """Response after selecting plans."""
    
    session_slug: str
    message: str
    selected_plans: List[SelectedPlanInfo]
    total_selected: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_slug": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Planes seleccionados exitosamente",
                "selected_plans": [
                    {
                        "product_code": "SOAT",
                        "product_name": "Seguro Obligatorio de Accidentes de Tránsito",
                        "selected_option": {
                            "option_id": 125,
                            "plan_name": "SOAT Standard",
                            "price": 250710.0,
                            "coverage": {
                                "premium_value": 174900,
                                "total_to_pay": 250710
                            }
                        }
                    },
                    {
                        "product_code": "AP",
                        "product_name": "Accidentes Personales",
                        "selected_option": {
                            "option_id": 124,
                            "plan_name": "PLAN PLATA",
                            "price": 19900.0,
                            "coverage": {
                                "code_type": "3",
                                "insured_value": 7000000
                            }
                        }
                    }
                ],
                "total_selected": 2
            }
        }


class PreExpeditionRequest(BaseModel):
    """Request for pre-expedition (quote mode issuance) with plan selections."""
    
    selections: List[PlanSelection] = Field(
        ...,
        description="List of plan selections (one per product)",
        min_length=1
    )
    address: str = Field(
        ...,
        description="Dirección del cliente",
        min_length=1,
        max_length=100
    )
    phone: str = Field(
        ...,
        description="Número de celular del cliente",
        min_length=7,
        max_length=20
    )
    email: str = Field(
        ...,
        description="Correo electrónico del cliente",
        min_length=5,
        max_length=255
    )
    city_id: int = Field(
        ...,
        description="ID de la ciudad del cliente",
        gt=0
    )
    gender_id: int = Field(
        ...,
        description="ID del género del cliente",
        gt=0
    )
    birth_date: Optional[str] = Field(
        None,
        description="Fecha de nacimiento (requerida si se selecciona AP). Formato: YYYY-MM-DD",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    
    @validator('selections')
    def validate_unique_products(cls, v):
        """Ensure each product appears only once."""
        product_codes = [s.product_code for s in v]
        if len(product_codes) != len(set(product_codes)):
            raise ValueError('Duplicate product_code found. Each product can only be selected once.')
        return v
    
    @validator('email')
    def validate_email(cls, v):
        """Basic email validation."""
        if '@' not in v or '.' not in v:
            raise ValueError('Email inválido')
        return v.strip().lower()
    
    @validator('phone')
    def validate_phone(cls, v):
        """Remove spaces and validate phone format."""
        phone = v.strip().replace(' ', '').replace('-', '')
        if not phone.isdigit():
            raise ValueError('El teléfono debe contener solo números')
        return phone
    
    @validator('birth_date')
    def validate_birth_date_for_ap(cls, v, values):
        """Validate birth_date is provided when AP is selected."""
        if 'selections' in values:
            has_ap = any(s.product_code == 'AP' for s in values['selections'])
            if has_ap and not v:
                raise ValueError('La fecha de nacimiento es requerida cuando se selecciona AP')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "selections": [
                    {
                        "product_code": "SOAT",
                        "option_id": 125
                    },
                    {
                        "product_code": "AP",
                        "option_id": 124
                    }
                ],
                "address": "Calle 123 #45-67",
                "phone": "3001234567",
                "email": "cliente@example.com",
                "city_id": 1,
                "gender_id": 1,
                "birth_date": "1990-05-15"
            }
        }


class ExpeditionProductResult(BaseModel):
    """Result of expedition for a single product."""
    
    product_code: str
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_code": "SOAT",
                "success": True,
                "message": "Pre-expedición exitosa",
                "details": {
                    "imp_prima_total": 324200,
                    "imp_pagado": 326600
                }
            }
        }


class PreExpeditionResponse(BaseModel):
    """Response after pre-expedition process."""
    
    session_slug: str
    message: str
    results: List[ExpeditionProductResult]
    total_processed: int
    all_success: bool
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_slug": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Pre-expedición completada exitosamente",
                "results": [
                    {
                        "product_code": "SOAT",
                        "success": True,
                        "message": "Pre-expedición exitosa",
                        "details": {
                            "imp_prima_total": 324200,
                            "imp_pagado": 326600
                        }
                    },
                    {
                        "product_code": "AP",
                        "success": True,
                        "message": "AP procesado con SOAT",
                        "details": {}
                    }
                ],
                "total_processed": 2,
                "all_success": True
            }
        }


class ExpeditionResponse(BaseModel):
    """Response after final expedition process."""
    
    session_slug: str
    message: str
    results: List[ExpeditionProductResult]
    total_processed: int
    all_success: bool
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_slug": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Expedición completada exitosamente",
                "results": [
                    {
                        "product_code": "SOAT",
                        "success": True,
                        "message": "Póliza expedida exitosamente",
                        "details": {
                            "policy_number": "123456789",
                            "imp_prima_total": 324200,
                            "imp_pagado": 326600
                        }
                    },
                    {
                        "product_code": "AP",
                        "success": True,
                        "message": "Póliza expedida exitosamente",
                        "details": {
                            "policy_number": "987654321"
                        }
                    }
                ],
                "total_processed": 2,
                "all_success": True
            }
        }

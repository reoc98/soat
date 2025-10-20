from pydantic import BaseModel, Field, validator
from typing import Any, Optional, List, Dict
from datetime import datetime


class QuoteRequest(BaseModel):
    """Quote request schema."""
    
    session_id: str = Field(
        ..., 
        description="Insurance session UUID slug",
        min_length=36,
        max_length=50
    )
    class_code: str = Field(
        ..., 
        description="Vehicle class code from homologations",
        min_length=1,
        max_length=50
    )
    products: List[str] = Field(
        ...,
        description="List of product codes to quote",
        min_items=1
    )
    
    @validator('session_id')
    def validate_session_id(cls, v):
        """Remove whitespace."""
        return v.strip()
    
    @validator('class_code')
    def validate_class_code(cls, v):
        """Remove whitespace and convert to uppercase."""
        return v.strip().upper()
    
    @validator('products')
    def validate_products(cls, v):
        """Remove whitespace from product codes and remove duplicates."""
        cleaned = [code.strip().upper() for code in v]
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for code in cleaned:
            if code not in seen:
                seen.add(code)
                unique.append(code)
        return unique
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "class_code": "AUTO001",
                "products": ["SOAT", "RC"]
            }
        }


class HomologationInfo(BaseModel):
    """Homologation information schema."""
    
    id: int
    class_code: str
    class_description: Optional[str] = None
    transport_type_code: Optional[str] = None
    brand_code: Optional[str] = None
    line_code: Optional[str] = None
    destination_code: Optional[str] = None


class ProductInfo(BaseModel):
    """Product information schema."""
    
    product_code: str
    product_name: str
    plans: Optional[List[Any]] = None 
    mandatory: Optional[bool] = False
    success: Optional[bool] = None


class ExternalQuoteInfo(BaseModel):
    """External quote information schema."""
    
    product_code: str
    product_name: str
    # mandatory: bool
    plans: Optional[List[Any]] = None 
    success: Optional[bool] = None
    # provider: str
    # success: bool
    # total: Optional[float] = None
    # premium: Optional[float] = None
    # start_date: Optional[str] = None
    # end_date: Optional[str] = None
    # error_message: Optional[str] = None


class QuoteResponse(BaseModel):
    """Quote response schema."""
    
    success: bool = Field(..., description="Whether quote was created successfully")
    message: str = Field(..., description="Response message")
    # session_id: int = Field(..., description="Insurance session database ID")
    session_slug: str = Field(..., description="Insurance session UUID slug")
    # selected_homologation_id: int = Field(..., description="Selected vehicle homologation ID")
    # class_code: str = Field(..., description="Selected vehicle class code")
    # selection_id: int = Field(..., description="Vehicle homologation selection ID")
    products: List[ProductInfo] = Field(..., description="Validated products for the quote")
    # external_quotes: List[ExternalQuoteInfo] = Field(default=[], description="External provider quotes")
    
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Quote created successfully",
                "session_id": 123,
                "session_slug": "550e8400-e29b-41d4-a716-446655440000",
                "selected_homologation_id": 456,
                "class_code": "AUTO001",
                "selection_id": 789,
                "products": [
                    {"code": "SOAT", "name": "Seguro Obligatorio de Accidentes de Tránsito", "mandatory": True},
                    {"code": "RCE", "name": "Responsabilidad Civil Extracontractual", "mandatory": False}
                ],
                "external_quotes": [
                    {
                        "product_code": "SOAT",
                        "provider": "Mundial Seguros",
                        "success": True,
                        "total": 326600.0,
                        "premium": 213300.0,
                        "start_date": "2025-10-16T00:00:00",
                        "end_date": "2026-10-15T00:00:00",
                        "error_message": None
                    }
                ]
            }
        }


class SelectedProductQuote(BaseModel):
    """Selected product quote information."""
    
    product_code: str
    product_name: str
    selected_plan: Dict[str, Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_code": "SOAT",
                "product_name": "Seguro Obligatorio de Accidentes de Tránsito",
                "selected_plan": {
                    "option_id": 125,
                    "plan_name": "SOAT Standard",
                    "price": 250710.0,
                    "coverages": {
                        "premium_value": 174900,
                        "total_to_pay": 250710
                    }
                }
            }
        }


class SelectedHomologationResponse(BaseModel):
    """Selected homologation response schema with selected quote information."""
    
    selection_id: int
    session_slug: str
    id: int
    class_code: str
    class_description: Optional[str] = None
    transport_type_code: Optional[str] = None
    brand_code: Optional[str] = None
    line_code: Optional[str] = None
    destination_code: Optional[str] = None
    selected_at: str
    selected_products: Optional[List[SelectedProductQuote]] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "selection_id": 789,
                "session_slug": "550e8400-e29b-41d4-a716-446655440000",
                "id": 456,
                "class_code": "AUTO001",
                "class_description": "Automóvil",
                "transport_type_code": "PART",
                "brand_code": "TOYOTA",
                "line_code": "COROLLA",
                "destination_code": "PARTICULAR",
                "selected_at": "2025-10-15T10:30:00",
                "selected_products": [
                    {
                        "product_code": "SOAT",
                        "product_name": "Seguro Obligatorio de Accidentes de Tránsito",
                        "selected_plan": {
                            "option_id": 125,
                            "plan_name": "SOAT Standard",
                            "price": 250710.0,
                            "coverages": {
                                "premium_value": 174900,
                                "total_to_pay": 250710
                            }
                        }
                    },
                    {
                        "product_code": "AP",
                        "product_name": "Accidentes Personales",
                        "selected_plan": {
                            "option_id": 124,
                            "plan_name": "PLAN PLATA",
                            "price": 19900.0,
                            "coverages": {
                                "code_type": "3",
                                "insured_value": 7000000
                            }
                        }
                    }
                ]
            }
        }


class AvailableHomologationsResponse(BaseModel):
    """Available homologations response schema."""
    
    session_slug: str
    homologations: List[HomologationInfo]
    count: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_slug": "550e8400-e29b-41d4-a716-446655440000",
                "homologations": [
                    {
                        "homologation_id": 456,
                        "class_code": "AUTO001",
                        "class_description": "Automóvil",
                        "transport_type_code": "PART",
                        "brand_code": "TOYOTA",
                        "line_code": "COROLLA",
                        "destination_code": "PARTICULAR"
                    }
                ],
                "count": 1
            }
        }


class QuoteOptionsResponse(BaseModel):
    """Quote options response schema - shows available plans for each product."""
    
    session_slug: str
    products: List[ExternalQuoteInfo]
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_slug": "550e8400-e29b-41d4-a716-446655440000",
                "products": [
                    {
                        "product_code": "SOAT",
                        "product_name": "Seguro Obligatorio de Accidentes de Tránsito",
                        "plans": [
                            {
                                "option_id": 1,
                                "plan_name": "SOAT Standard",
                                "price": 250710.0,
                                "coverage": {
                                    "premium_value": 174900,
                                    "total_to_pay": 250710
                                }
                            }
                        ],
                        "success": True
                    },
                    {
                        "product_code": "AP",
                        "product_name": "Accidentes Personales",
                        "plans": [
                            {
                                "option_id": 2,
                                "plan_name": "PLAN PLATA",
                                "price": 19900.0,
                                "coverage": {
                                    "code_type": "3",
                                    "insured_value": 7000000
                                }
                            }
                        ],
                        "success": True
                    }
                ]
            }
        }


class PlanSelection(BaseModel):
    """Single plan selection for a product."""
    
    product_code: str = Field(
        ...,
        description="Product code (SOAT, AP, etc.)",
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
                "product_code": "AP",
                "option_id": 2
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
                "product_code": "AP",
                "product_name": "Accidentes Personales",
                "selected_option": {
                    "option_id": 2,
                    "plan_name": "PLAN PLATA",
                    "price": 19900.0,
                    "coverage": {"code_type": "3"}
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
                        "product_name": "SOAT",
                        "selected_option": {
                            "option_id": 125,
                            "plan_name": "SOAT Standard",
                            "price": 250710.0,
                            "coverage": {}
                        }
                    },
                    {
                        "product_code": "AP",
                        "product_name": "Accidentes Personales",
                        "selected_option": {
                            "option_id": 124,
                            "plan_name": "PLAN PLATA",
                            "price": 19900.0,
                            "coverage": {}
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


class PreExpeditionProductResult(BaseModel):
    """Result of pre-expedition for a single product."""
    
    product_code: str
    # product_name: str
    success: bool
    policy_number: Optional[str] = None
    message: str
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_code": "SOAT",
                "product_name": "SOAT",
                "success": True,
                "policy_number": "PRE-123456789",
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
    results: List[PreExpeditionProductResult]
    total_processed: int
    all_success: bool
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_slug": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Pre-expedición completada",
                "results": [
                    {
                        "product_code": "SOAT",
                        "product_name": "SOAT",
                        "success": True,
                        "policy_number": "PRE-123456789",
                        "message": "Pre-expedición exitosa",
                        "details": {}
                    },
                    {
                        "product_code": "AP",
                        "product_name": "Accidentes Personales",
                        "success": True,
                        "policy_number": "PRE-987654321",
                        "message": "Pre-expedición exitosa",
                        "details": {}
                    }
                ],
                "total_processed": 2,
                "all_success": True
            }
        }




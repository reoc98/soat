"""
Catalog Schemas

Pydantic schemas for catalog endpoints (departments, cities, document types, genders, etc.).
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class DepartmentResponse(BaseModel):
    """Department information."""
    
    id: int
    code: str
    name: str
    status: int
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "code": "05",
                "name": "ANTIOQUIA",
                "status": 1
            }
        }


class CityResponse(BaseModel):
    """City information with department."""
    
    id: int
    code: str
    name: str
    code_department: str
    department_name: Optional[str] = None
    status: int
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "code": "05001",
                "name": "MEDELLÍN",
                "code_department": "05",
                "department_name": "ANTIOQUIA",
                "status": 1
            }
        }


class DocumentTypeResponse(BaseModel):
    """Document type information."""
    
    id: int
    code: str
    name: str
    description: Optional[str] = None
    soat_id: Optional[int] = None
    soat_code: Optional[str] = None
    runt_code: Optional[str] = None
    status: int
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "code": "CC",
                "name": "Cédula de Ciudadanía",
                "description": "Documento de identificación colombiano",
                "soat_id": 1,
                "soat_code": "CC",
                "runt_code": "1",
                "status": 1
            }
        }


class GenderResponse(BaseModel):
    """Gender information."""
    
    id: int
    code: str
    name: str
    status: int
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "code": "M",
                "name": "MASCULINO",
                "status": 1
            }
        }


class DepartmentListResponse(BaseModel):
    """Response with list of departments."""
    
    total: int
    departments: List[DepartmentResponse]
    
    class Config:
        json_schema_extra = {
            "example": {
                "total": 32,
                "departments": [
                    {
                        "id": 1,
                        "code": "05",
                        "name": "ANTIOQUIA",
                        "status": 1
                    },
                    {
                        "id": 2,
                        "code": "08",
                        "name": "ATLÁNTICO",
                        "status": 1
                    }
                ]
            }
        }


class CityListResponse(BaseModel):
    """Response with list of cities."""
    
    total: int
    cities: List[CityResponse]
    
    class Config:
        json_schema_extra = {
            "example": {
                "total": 1122,
                "cities": [
                    {
                        "id": 1,
                        "code": "05001",
                        "name": "MEDELLÍN",
                        "code_department": "05",
                        "department_name": "ANTIOQUIA",
                        "status": 1
                    },
                    {
                        "id": 2,
                        "code": "11001",
                        "name": "BOGOTÁ D.C.",
                        "code_department": "11",
                        "department_name": "CUNDINAMARCA",
                        "status": 1
                    }
                ]
            }
        }


class DocumentTypeListResponse(BaseModel):
    """Response with list of document types."""
    
    total: int
    document_types: List[DocumentTypeResponse]
    
    class Config:
        json_schema_extra = {
            "example": {
                "total": 5,
                "document_types": [
                    {
                        "id": 1,
                        "code": "CC",
                        "name": "Cédula de Ciudadanía",
                        "description": "Documento de identificación colombiano",
                        "soat_id": 1,
                        "soat_code": "CC",
                        "runt_code": "1",
                        "status": 1
                    },
                    {
                        "id": 2,
                        "code": "NIT",
                        "name": "Número de Identificación Tributaria",
                        "description": "Identificación para empresas",
                        "soat_id": 2,
                        "soat_code": "NIT",
                        "runt_code": "2",
                        "status": 1
                    }
                ]
            }
        }


class GenderListResponse(BaseModel):
    """Response with list of genders."""
    
    total: int
    genders: List[GenderResponse]
    
    class Config:
        json_schema_extra = {
            "example": {
                "total": 2,
                "genders": [
                    {
                        "id": 1,
                        "code": "M",
                        "name": "MASCULINO",
                        "status": 1
                    },
                    {
                        "id": 2,
                        "code": "F",
                        "name": "FEMENINO",
                        "status": 1
                    }
                ]
            }
        }

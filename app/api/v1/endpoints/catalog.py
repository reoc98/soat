"""
Catalog Endpoints

API endpoints for retrieving catalog data (departments, cities, document types, genders, etc.).
"""

import logging
from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Dict, Any, Optional

from app.schemas.catalog import (
    DepartmentListResponse,
    DepartmentResponse,
    CityListResponse,
    CityResponse,
    DocumentTypeListResponse,
    DocumentTypeResponse,
    GenderListResponse,
    GenderResponse
)
from app.services.catalog import CatalogService
from app.middleware.dependencies import get_current_user
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/departments", response_model=DepartmentListResponse)
async def get_departments(
    active_only: bool = Query(True, description="Return only active departments"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> DepartmentListResponse:
    """
    Get list of all departments.
    
    Returns all departments in Colombia, optionally filtered by status.
    By default, only active departments are returned.
    
    **Query Parameters:**
    - `active_only`: If true, returns only active departments (status=1). Default: true
    
    **Use Cases:**
    - Populate department dropdown in forms
    - Display available departments for address selection
    - Filter cities by department
    
    **Example Response:**
    ```json
    {
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
    ```
    
    Args:
        active_only: Filter by active status
        current_user: Current user information from token
        
    Returns:
        DepartmentListResponse with list of departments
        
    Raises:
        500: Internal server error
    """
    try:
        catalog_service = CatalogService(current_user.get("sponsor"))
        result = await catalog_service.get_departments(active_only=active_only)
        return DepartmentListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error retrieving departments: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/departments/{code}", response_model=DepartmentResponse)
async def get_department_by_code(
    code: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> DepartmentResponse:
    """
    Get department by code.
    
    Returns detailed information about a specific department.
    
    **Path Parameters:**
    - `code`: Department code (e.g., "05" for Antioquia, "11" for Cundinamarca)
    
    **Example Response:**
    ```json
    {
      "id": 1,
      "code": "05",
      "name": "ANTIOQUIA",
      "status": 1
    }
    ```
    
    Args:
        code: Department code
        current_user: Current user information from token
        
    Returns:
        DepartmentResponse with department details
        
    Raises:
        404: Department not found
        500: Internal server error
    """
    try:
        catalog_service = CatalogService(current_user.get("sponsor"))
        result = await catalog_service.get_department_by_code(code)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Department with code '{code}' not found"
            )
        
        return DepartmentResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving department: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/cities", response_model=CityListResponse)
async def get_cities(
    department_code: Optional[str] = Query(None, description="Filter by department code"),
    active_only: bool = Query(True, description="Return only active cities"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> CityListResponse:
    """
    Get list of all cities, optionally filtered by department.
    
    Returns all cities in Colombia with their department information.
    Can be filtered by department code to get cities within a specific department.
    By default, only active cities are returned.
    
    **Query Parameters:**
    - `department_code`: Optional filter by department code (e.g., "05" for Antioquia)
    - `active_only`: If true, returns only active cities (status=1). Default: true
    
    **Use Cases:**
    - Populate city dropdown after department selection
    - Display available cities for address selection
    - Get all cities in a specific department
    
    **Example Response - All Cities:**
    ```json
    {
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
    ```
    
    **Example Response - Filtered by Department:**
    ```
    GET /catalogs/cities?department_code=05
    
    {
      "total": 125,
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
          "code": "05002",
          "name": "ABEJORRAL",
          "code_department": "05",
          "department_name": "ANTIOQUIA",
          "status": 1
        }
      ]
    }
    ```
    
    Args:
        department_code: Optional department code filter
        active_only: Filter by active status
        current_user: Current user information from token
        
    Returns:
        CityListResponse with list of cities
        
    Raises:
        500: Internal server error
    """
    try:
        catalog_service = CatalogService(current_user.get("sponsor"))
        result = await catalog_service.get_cities(
            department_code=department_code,
            active_only=active_only
        )
        return CityListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error retrieving cities: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/cities/{code}", response_model=CityResponse)
async def get_city_by_code(
    code: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> CityResponse:
    """
    Get city by code.
    
    Returns detailed information about a specific city including its department.
    
    **Path Parameters:**
    - `code`: City code (e.g., "05001" for Medellín, "11001" for Bogotá)
    
    **Example Response:**
    ```json
    {
      "id": 1,
      "code": "05001",
      "name": "MEDELLÍN",
      "code_department": "05",
      "department_name": "ANTIOQUIA",
      "status": 1
    }
    ```
    
    Args:
        code: City code
        current_user: Current user information from token
        
    Returns:
        CityResponse with city details
        
    Raises:
        404: City not found
        500: Internal server error
    """
    try:
        catalog_service = CatalogService(current_user.get("sponsor"))
        result = await catalog_service.get_city_by_code(code)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"City with code '{code}' not found"
            )
        
        return CityResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving city: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/document-types", response_model=DocumentTypeListResponse)
async def get_document_types(
    active_only: bool = Query(True, description="Return only active document types"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> DocumentTypeListResponse:
    """
    Get list of all document types.
    
    Returns all available document types (CC, NIT, CE, etc.) with their codes
    and mapping to external systems (SOAT, RUNT).
    By default, only active document types are returned.
    
    **Query Parameters:**
    - `active_only`: If true, returns only active document types (status=1). Default: true
    
    **Use Cases:**
    - Populate document type dropdown in forms
    - Validate document type selection
    - Map document types to external systems
    
    **Example Response:**
    ```json
    {
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
    ```
    
    Args:
        active_only: Filter by active status
        current_user: Current user information from token
        
    Returns:
        DocumentTypeListResponse with list of document types
        
    Raises:
        500: Internal server error
    """
    try:
        catalog_service = CatalogService(current_user.get("sponsor"))
        result = await catalog_service.get_document_types(active_only=active_only)
        return DocumentTypeListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error retrieving document types: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/document-types/{code}", response_model=DocumentTypeResponse)
async def get_document_type_by_code(
    code: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> DocumentTypeResponse:
    """
    Get document type by code.
    
    Returns detailed information about a specific document type.
    
    **Path Parameters:**
    - `code`: Document type code (e.g., "CC", "NIT", "CE", "PAS")
    
    **Example Response:**
    ```json
    {
      "id": 1,
      "code": "CC",
      "name": "Cédula de Ciudadanía",
      "description": "Documento de identificación colombiano",
      "soat_id": 1,
      "soat_code": "CC",
      "runt_code": "1",
      "status": 1
    }
    ```
    
    Args:
        code: Document type code
        current_user: Current user information from token
        
    Returns:
        DocumentTypeResponse with document type details
        
    Raises:
        404: Document type not found
        500: Internal server error
    """
    try:
        catalog_service = CatalogService(current_user.get("sponsor"))
        result = await catalog_service.get_document_type_by_code(code)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document type with code '{code}' not found"
            )
        
        return DocumentTypeResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document type: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/genders", response_model=GenderListResponse)
async def get_genders(
    active_only: bool = Query(True, description="Return only active genders"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> GenderListResponse:
    """
    Get list of all genders.
    
    Returns all available gender options.
    By default, only active genders are returned.
    
    **Query Parameters:**
    - `active_only`: If true, returns only active genders (status=1). Default: true
    
    **Use Cases:**
    - Populate gender dropdown in forms
    - Validate gender selection
    
    **Example Response:**
    ```json
    {
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
    ```
    
    Args:
        active_only: Filter by active status
        current_user: Current user information from token
        
    Returns:
        GenderListResponse with list of genders
        
    Raises:
        500: Internal server error
    """
    try:
        catalog_service = CatalogService(current_user.get("sponsor"))
        result = await catalog_service.get_genders(active_only=active_only)
        return GenderListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error retrieving genders: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/genders/{code}", response_model=GenderResponse)
async def get_gender_by_code(
    code: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> GenderResponse:
    """
    Get gender by code.
    
    Returns detailed information about a specific gender.
    
    **Path Parameters:**
    - `code`: Gender code (e.g., "M" for Masculino, "F" for Femenino)
    
    **Example Response:**
    ```json
    {
      "id": 1,
      "code": "M",
      "name": "MASCULINO",
      "status": 1
    }
    ```
    
    Args:
        code: Gender code
        current_user: Current user information from token
        
    Returns:
        GenderResponse with gender details
        
    Raises:
        404: Gender not found
        500: Internal server error
    """
    try:
        catalog_service = CatalogService(current_user.get("sponsor"))
        result = await catalog_service.get_gender_by_code(code)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Gender with code '{code}' not found"
            )
        
        return GenderResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving gender: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

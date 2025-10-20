"""
Catalog Service

Service for retrieving catalog data (departments, cities, document types, genders, etc.).
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.models.department import Department
from app.models.city import City
from app.models.document_type import DocumentType
from app.models.gender import Gender
from app.database.session import db_manager
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class CatalogService:
    """Service for handling catalog operations."""
    
    def __init__(self, sponsor: str):
        """
        Initialize the catalog service.
        
        Args:
            sponsor: Sponsor identifier
        """
        self.sponsor = sponsor
    
    async def get_departments(
        self,
        active_only: bool = True
    ) -> Dict[str, Any]:
        """
        Get all departments.
        
        Args:
            active_only: If True, only return active departments (status=1)
            
        Returns:
            Dictionary with total count and list of departments
        """
        async with db_manager.get_async_session("dbr", self.sponsor) as session:
            stmt = select(Department)
            
            if active_only:
                stmt = stmt.where(Department.status == 1)
            
            stmt = stmt.order_by(Department.name)
            
            result = await session.execute(stmt)
            departments = result.scalars().all()
            
            logger.info(f"Retrieved {len(departments)} departments (active_only={active_only})")
            
            return {
                "total": len(departments),
                "departments": [
                    {
                        "id": dept.id,
                        "code": dept.code,
                        "name": dept.name,
                        "status": dept.status
                    }
                    for dept in departments
                ]
            }
    
    async def get_department_by_code(
        self,
        code: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get department by code.
        
        Args:
            code: Department code
            
        Returns:
            Department information or None if not found
        """
        async with db_manager.get_async_session("dbr", self.sponsor) as session:
            stmt = select(Department).where(Department.code == code)
            result = await session.execute(stmt)
            department = result.scalars().first()
            
            if not department:
                logger.warning(f"Department not found: {code}")
                return None
            
            return {
                "id": department.id,
                "code": department.code,
                "name": department.name,
                "status": department.status
            }
    
    async def get_cities(
        self,
        department_code: Optional[str] = None,
        active_only: bool = True
    ) -> Dict[str, Any]:
        """
        Get all cities, optionally filtered by department.
        
        Args:
            department_code: Optional department code to filter cities
            active_only: If True, only return active cities (status=1)
            
        Returns:
            Dictionary with total count and list of cities
        """
        async with db_manager.get_async_session("dbr", self.sponsor) as session:
            stmt = (
                select(City)
                .options(selectinload(City.department))
            )
            
            conditions = []
            if active_only:
                conditions.append(City.status == 1)
            if department_code:
                conditions.append(City.code_department == department_code)
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
            
            stmt = stmt.order_by(City.name)
            
            result = await session.execute(stmt)
            cities = result.scalars().all()
            
            logger.info(
                f"Retrieved {len(cities)} cities "
                f"(department_code={department_code}, active_only={active_only})"
            )
            
            return {
                "total": len(cities),
                "cities": [
                    {
                        "id": city.id,
                        "code": city.code,
                        "name": city.name,
                        "code_department": city.code_department,
                        "department_name": city.department.name if city.department else None,
                        "status": city.status
                    }
                    for city in cities
                ]
            }
    
    async def get_city_by_code(
        self,
        code: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get city by code.
        
        Args:
            code: City code
            
        Returns:
            City information or None if not found
        """
        async with db_manager.get_async_session("dbr", self.sponsor) as session:
            stmt = (
                select(City)
                .options(selectinload(City.department))
                .where(City.code == code)
            )
            result = await session.execute(stmt)
            city = result.scalars().first()
            
            if not city:
                logger.warning(f"City not found: {code}")
                return None
            
            return {
                "id": city.id,
                "code": city.code,
                "name": city.name,
                "code_department": city.code_department,
                "department_name": city.department.name if city.department else None,
                "status": city.status
            }
    
    async def get_document_types(
        self,
        active_only: bool = True
    ) -> Dict[str, Any]:
        """
        Get all document types.
        
        Args:
            active_only: If True, only return active document types (status=1)
            
        Returns:
            Dictionary with total count and list of document types
        """
        async with db_manager.get_async_session("dbr", self.sponsor) as session:
            stmt = select(DocumentType)
            
            if active_only:
                stmt = stmt.where(DocumentType.status == 1)
            
            stmt = stmt.order_by(DocumentType.name)
            
            result = await session.execute(stmt)
            document_types = result.scalars().all()
            
            logger.info(
                f"Retrieved {len(document_types)} document types (active_only={active_only})"
            )
            
            return {
                "total": len(document_types),
                "document_types": [
                    {
                        "id": doc_type.id,
                        "code": doc_type.code,
                        "name": doc_type.name,
                        "description": doc_type.description,
                        "soat_id": doc_type.soat_id,
                        "soat_code": doc_type.soat_code,
                        "runt_code": doc_type.runt_code,
                        "status": doc_type.status
                    }
                    for doc_type in document_types
                ]
            }
    
    async def get_document_type_by_code(
        self,
        code: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get document type by code.
        
        Args:
            code: Document type code
            
        Returns:
            Document type information or None if not found
        """
        async with db_manager.get_async_session("dbr", self.sponsor) as session:
            stmt = select(DocumentType).where(DocumentType.code == code)
            result = await session.execute(stmt)
            doc_type = result.scalars().first()
            
            if not doc_type:
                logger.warning(f"Document type not found: {code}")
                return None
            
            return {
                "id": doc_type.id,
                "code": doc_type.code,
                "name": doc_type.name,
                "description": doc_type.description,
                "soat_id": doc_type.soat_id,
                "soat_code": doc_type.soat_code,
                "runt_code": doc_type.runt_code,
                "status": doc_type.status
            }
    
    async def get_genders(
        self,
        active_only: bool = True
    ) -> Dict[str, Any]:
        """
        Get all genders.
        
        Args:
            active_only: If True, only return active genders (status=1)
            
        Returns:
            Dictionary with total count and list of genders
        """
        async with db_manager.get_async_session("dbr", self.sponsor) as session:
            stmt = select(Gender)
            
            if active_only:
                stmt = stmt.where(Gender.status == 1)
            
            stmt = stmt.order_by(Gender.name)
            
            result = await session.execute(stmt)
            genders = result.scalars().all()
            
            logger.info(f"Retrieved {len(genders)} genders (active_only={active_only})")
            
            return {
                "total": len(genders),
                "genders": [
                    {
                        "id": gender.id,
                        "code": gender.code,
                        "name": gender.name,
                        "status": gender.status
                    }
                    for gender in genders
                ]
            }
    
    async def get_gender_by_code(
        self,
        code: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get gender by code.
        
        Args:
            code: Gender code
            
        Returns:
            Gender information or None if not found
        """
        async with db_manager.get_async_session("dbr", self.sponsor) as session:
            stmt = select(Gender).where(Gender.code == code)
            result = await session.execute(stmt)
            gender = result.scalars().first()
            
            if not gender:
                logger.warning(f"Gender not found: {code}")
                return None
            
            return {
                "id": gender.id,
                "code": gender.code,
                "name": gender.name,
                "status": gender.status
            }

import logging
from turtle import mode
from typing import Optional, Any, List, Dict
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import db_manager

logger = logging.getLogger(__name__)


class TenantDB:
    """Simplified interface for tenant database operations."""

    @staticmethod
    @asynccontextmanager
    async def get_read_session(tenant_id: str):
        """Get a read-only async session for a tenant."""
        async with db_manager.get_async_session("dbr", tenant_id) as session:
            yield session

    @staticmethod
    @asynccontextmanager
    async def get_write_session(tenant_id: str):
        """Get a read-write async session for a tenant."""
        async with db_manager.get_async_session("dbw", tenant_id) as session:
            yield session

    @staticmethod
    async def execute_read_query(tenant_id: str, query) -> Any:
        """Execute a read-only query for a tenant."""
        async with TenantDB.get_read_session(tenant_id) as session:
            result = await session.execute(query)
            return result

    @staticmethod
    async def execute_write_query(tenant_id: str, query) -> Any:
        """Execute a write query for a tenant (with commit)."""
        async with TenantDB.get_write_session(tenant_id) as session:
            result = await session.execute(query)
            await session.commit()
            return result

    @staticmethod
    @asynccontextmanager
    async def get_master_session():
        """Optional: master DB connection (for tenant registry)."""
        async with db_manager.get_async_session("dbw", tenant_id=None) as session:
            yield session
    
    @staticmethod
    @asynccontextmanager
    async def get_db_session(tenant_id: str, mode: str = "dbr"):
        async with db_manager.get_async_session(mode=mode, tenant_id=tenant_id) as session:
            yield session

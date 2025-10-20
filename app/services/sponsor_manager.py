from typing import Optional, Dict, Any
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Request

from app.database.session import db_manager
from app.models.sponsor import Sponsor
from app.models.user import User
from app.core.exceptions import TenantConfigurationError
from app.core.config import settings

logger = logging.getLogger(__name__)

class SponsorService:
    """Service for tenant management and resolution."""

    @staticmethod
    async def get_sponsor_config(sponsor_id: str) -> Optional[Dict[str, Any]]:
        """Get sponsor configuration from database."""
        try:
            async with db_manager.get_async_session() as session:
                stmt = select(Sponsor).filter(Sponsor.slug == sponsor_id)
                result = await session.execute(stmt)
                sponsor = result.scalars().first()

                if sponsor:
                    return {
                        "sponsor_id": sponsor.slug,
                        "name": sponsor.name,
                        "status": sponsor.status.value,
                        "is_active": sponsor.is_active,
                        "contact_email": sponsor.contact_email,
                        "contact_phone": sponsor.contact_phone,
                    }
                return None
        except Exception as e:
            logger.error(f"Error retrieving sponsor config for {sponsor_id}: {e}")
            return None

    @staticmethod
    async def validate_sponsor_access(sponsor_id: str, user_sponsor: str, user_role: str) -> bool:
        """Validate if user has access to the sponsor."""
        if user_role in ["admin", "insurer"]:
            return True
        return sponsor_id == user_sponsor

    @staticmethod
    async def get_sponsor_db_session(sponsor_id: str, db_type: str = "dbw") -> AsyncSession:
        """Get database session for sponsor."""
        return await db_manager.get_tenant_session(sponsor_id, db_type)

    @staticmethod
    async def resolve_tenant_from_request(request: "Request") -> Optional[str]:
        """Resolve tenant ID from request headers or other sources."""
        # Check header first
        tenant_header = request.headers.get(settings.TENANT_HEADER_NAME)
        if tenant_header:
            return tenant_header

        # Could add domain-based resolution here
        # host = request.headers.get("host", "")
        # if "rappi" in host:
        #     return "rappi"

        return None

    @staticmethod
    async def validate_user_in_sponsor_db(sponsor_id: str, email: str):
        async with db_manager.get_async_session("dbr", sponsor_id) as session:
            stmt = select(User.id, User.email, User.fullname, User.role, User.status).filter(User.email == email, User.status == 1).order_by(User.created_at.desc())
            result = await session.execute(stmt)
            user = result.first()

            if user:
                return {
                    "user_id": user.id,
                    "email": user.email,
                    "full_name": user.fullname,
                    "role": user.role,
                    "status": user.status,
                }
            return None
        # try:
        # except Exception as e:
        #     logger.error(f"Error retrieving sponsor config for {sponsor_id}: {e}")
        #     return None
    
    @staticmethod
    async def validate_user_in_core_db(email: str):
        async with db_manager.get_async_session() as session:
            stmt = select(User.id, User.email, User.fullname, User.role, User.status).filter(User.email == email, User.status == 1).order_by(User.created_at.desc())
            result = await session.execute(stmt)
            user = result.first()
            print(f"user from core db: {user}")
            if user:
                return {
                    "user_id": user.id,
                    "email": user.email,
                    "full_name": user.fullname,
                    "role": user.role,
                    "status": user.status,
                }
            return None
        # try:
        # except Exception as e:
        #     logger.error(f"Error retrieving user from core DB for email {email}: {e}")
        #     return None
# Global service instance
sponsor_service = SponsorService()
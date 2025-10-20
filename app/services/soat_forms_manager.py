"""
SOAT Forms Manager Service

Manages SOAT form lifecycle including:
- Fetching forms from Mundial Seguros
- Reserving forms for sessions
- Marking forms as used
- Releasing expired reservations
- Blocking/unblocking forms
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.soat_form import SoatForm, FormStatus
from app.database.session import db_manager
from app.core.exceptions import ValidationError
from app.services.external.soat_forms_client import SoatFormsClient

logger = logging.getLogger(__name__)


class SoatFormsManager:
    """Manager for SOAT forms lifecycle."""
    
    # Reservation expiration time (in minutes)
    RESERVATION_TIMEOUT = 15
    
    # Minimum forms to keep in database
    MIN_FORMS_THRESHOLD = 10
    
    def __init__(self, sponsor: str):
        """
        Initialize forms manager.
        
        Args:
            sponsor: Sponsor identifier
        """
        self.sponsor = sponsor
    
    async def fetch_and_store_forms(self) -> Dict[str, Any]:
        """
        Fetch available forms from Mundial Seguros and store in database.
        
        Only stores forms that don't already exist in the database.
        
        Returns:
            Dictionary with fetch results
        """
        # Get forms from external service
        forms_client = SoatFormsClient(self.sponsor)
        response = await forms_client.get_available_forms()
        
        if not response.success:
            logger.error(f"Failed to fetch forms: {response.error_message}")
            raise ValidationError(f"Error al consultar formularios: {response.error_message}")
        
        all_form_numbers = [f["nro_formulario"] for f in response.forms]
        if not all_form_numbers:
            logger.warning("No forms received from Mundial Seguros.")
            return {"success": True, "new_forms": 0, "existing_forms": 0, "total_fetched": 0}
        
        async with db_manager.get_async_session("dbw", self.sponsor) as session:
            new_forms = 0
            existing_forms = 0
            
            stmt = select(SoatForm.form_number).where(SoatForm.form_number.in_(all_form_numbers))
            result = await session.execute(stmt)
            existing_form_numbers = set(result.scalars().all())
            
            new_forms_data = [
                SoatForm(
                    form_number=f["nro_formulario"],
                    cod_suc=f["cod_suc"],
                    cod_agente=f["cod_agente"],
                    cod_pto_vta=f["cod_pto_vta"],
                    status=FormStatus.AVAILABLE,
                )
                for f in response.forms
                if f["nro_formulario"] not in existing_form_numbers
            ]
            
            # Bulk insert only new forms
            if new_forms_data:
                session.add_all(new_forms_data)
                await session.commit()
            
            new_count = len(new_forms_data)
            existing_count = len(existing_form_numbers)
            total_count = len(response.forms)
            
            # for form_data in response.forms:
            #     form_number = form_data['nro_formulario']
                
            #     # Check if form already exists
            #     stmt = select(SoatForm).where(
            #         SoatForm.form_number == form_number
            #     )
            #     result = await session.execute(stmt)
            #     existing_form = result.scalars().first()
                
            #     if existing_form:
            #         existing_forms += 1
            #         logger.debug(f"Form {form_number} already exists with status {existing_form.status}")
            #     else:
            #         # Create new form
            #         new_form = SoatForm(
            #             form_number=form_number,
            #             cod_suc=form_data['cod_suc'],
            #             cod_agente=form_data['cod_agente'],
            #             cod_pto_vta=form_data['cod_pto_vta'],
            #             status=FormStatus.AVAILABLE
            #         )
            #         session.add(new_form)
            #         new_forms += 1
            
            # await session.commit()
            
            logger.info(
                f"Forms fetch completed - New: {new_count}, "
                f"Existing: {existing_count}, Total fetched: {total_count}"
            )
            
            return {
                "success": True,
                "new_forms": new_count,
                "existing_forms": existing_count,
                "total_fetched": total_count
            }
    
    async def reserve_form_for_session(
        self,
        session_id: int,
    ) -> SoatForm:
        """
        Reserve an available form for a session.
        
        Uses database-level locking to prevent race conditions.
        
        Args:
            session_id: Insurance session ID
            
        Returns:
            Reserved SoatForm
            
        Raises:
            ValidationError: If no forms available
        """
        async with db_manager.get_async_session("dbw", self.sponsor) as session:
            # First, release any expired reservations
            await self._release_expired_reservations(session)
            
            # Get an available form with row lock (FOR UPDATE)
            stmt = (
                select(SoatForm)
                .where(
                    SoatForm.status.in_([FormStatus.AVAILABLE, FormStatus.EXPIRED])
                )
                .order_by(SoatForm.created_at.asc())
                .limit(1)
                .with_for_update()  # Lock the row
            )
            
            result = await session.execute(stmt)
            form = result.scalars().first()
            
            if not form:
                logger.warning(f"No available forms for sponsor {self.sponsor}")
                
                # Try to fetch more forms
                try:
                    await self.fetch_and_store_forms()
                    
                    # Try again after fetching
                    result = await session.execute(stmt)
                    form = result.scalars().first()
                    
                    if not form:
                        raise ValidationError("No hay formularios disponibles")
                        
                except Exception as e:
                    logger.error(f"Failed to fetch forms: {str(e)}")
                    raise ValidationError("No hay formularios disponibles")
            
            # Reserve the form
            form.status = FormStatus.RESERVED
            form.session_id = session_id
            form.reserved_at = datetime.utcnow()
            form.expires_at = datetime.utcnow() + timedelta(minutes=self.RESERVATION_TIMEOUT)
            
            await session.commit()
            await session.refresh(form)
            
            logger.info(
                f"Form reserved - Form: {form.form_number}, "
                f"Session: {session_id}, Expires: {form.expires_at}"
            )
            
            return form
    
    async def mark_form_as_used(
        self,
        form_number: str,
        session_id: str
    ) -> SoatForm:
        """
        Mark a form as used after successful expedition.
        
        Args:
            form_number: Form number
            session_id: Session ID to verify ownership
            
        Returns:
            Updated SoatForm
            
        Raises:
            ValidationError: If form not found or not reserved for this session
        """
        async with db_manager.get_async_session("dbw", self.sponsor) as session:
            stmt = select(SoatForm).where(
                SoatForm.form_number == form_number
            )
            result = await session.execute(stmt)
            form = result.scalars().first()
            
            if not form:
                raise ValidationError(f"Formulario {form_number} no encontrado")
            
            # Verify it's reserved for this session
            if form.session_id != session_id:
                raise ValidationError(
                    f"Formulario {form_number} no está reservado para esta sesión"
                )
            
            # Mark as used
            form.status = FormStatus.USED
            form.used_at = datetime.utcnow()
            
            await session.commit()
            await session.refresh(form)
            
            logger.info(
                f"Form marked as used - Form: {form_number}, Session: {session_id}"
            )
            
            return form
    
    async def release_form(
        self,
        form_number: str,
        session_id: str
    ) -> SoatForm:
        """
        Release a reserved form back to available status.
        
        Use this if pre-expedition fails or user cancels.
        
        Args:
            form_number: Form number
            session_id: Session ID to verify ownership
            
        Returns:
            Updated SoatForm
            
        Raises:
            ValidationError: If form not found or not reserved for this session
        """
        async with db_manager.get_async_session("dbw", self.sponsor) as session:
            stmt = select(SoatForm).where(
                SoatForm.form_number == form_number
            )
            result = await session.execute(stmt)
            form = result.scalars().first()
            
            if not form:
                raise ValidationError(f"Formulario {form_number} no encontrado")
            
            # Verify it's reserved for this session
            if form.session_id != session_id:
                raise ValidationError(
                    f"Formulario {form_number} no está reservado para esta sesión"
                )
            
            # Release the form
            form.status = FormStatus.AVAILABLE
            form.session_id = None
            form.reserved_at = None
            form.expires_at = None
            
            await session.commit()
            await session.refresh(form)
            
            logger.info(
                f"Form released - Form: {form_number}, Session: {session_id}"
            )
            
            return form
    
    async def get_form_for_session(
        self,
        session_id: str
    ) -> Optional[SoatForm]:
        """
        Get the form reserved for a session.
        
        Args:
            session_id: Session id
            
        Returns:
            SoatForm if found, None otherwise
        """
        async with db_manager.get_async_session("dbr", self.sponsor) as session:
            stmt = select(SoatForm).where(
                and_(
                    SoatForm.session_id == session_id,
                    SoatForm.status.in_([FormStatus.RESERVED, FormStatus.USED])
                )
            )
            result = await session.execute(stmt)
            return result.scalars().first()
    
    async def block_form(
        self,
        form_number: str,
        reason: str
    ) -> SoatForm:
        """
        Block a form manually.
        
        Args:
            form_number: Form number
            reason: Reason for blocking
            
        Returns:
            Updated SoatForm
            
        Raises:
            ValidationError: If form not found
        """
        async with db_manager.get_async_session("dbw", self.sponsor) as session:
            stmt = select(SoatForm).where(
                and_(
                    SoatForm.form_number == form_number,
                    SoatForm.sponsor == self.sponsor
                )
            )
            result = await session.execute(stmt)
            form = result.scalars().first()
            
            if not form:
                raise ValidationError(f"Formulario {form_number} no encontrado")
            
            form.status = FormStatus.BLOCKED
            form.blocked_at = datetime.utcnow()
            form.blocked_reason = reason
            
            await session.commit()
            await session.refresh(form)
            
            logger.info(f"Form blocked - Form: {form_number}, Reason: {reason}")
            
            return form
    
    async def unblock_form(
        self,
        form_number: str
    ) -> SoatForm:
        """
        Unblock a form.
        
        Args:
            form_number: Form number
            
        Returns:
            Updated SoatForm
            
        Raises:
            ValidationError: If form not found or not blocked
        """
        async with db_manager.get_async_session("dbw", self.sponsor) as session:
            stmt = select(SoatForm).where(
                and_(
                    SoatForm.form_number == form_number,
                    SoatForm.sponsor == self.sponsor
                )
            )
            result = await session.execute(stmt)
            form = result.scalars().first()
            
            if not form:
                raise ValidationError(f"Formulario {form_number} no encontrado")
            
            if form.status != FormStatus.BLOCKED:
                raise ValidationError(f"Formulario {form_number} no está bloqueado")
            
            form.status = FormStatus.AVAILABLE
            form.blocked_at = None
            form.blocked_reason = None
            
            await session.commit()
            await session.refresh(form)
            
            logger.info(f"Form unblocked - Form: {form_number}")
            
            return form
    
    async def _release_expired_reservations(self, session: AsyncSession):
        """
        Release expired reservations.
        
        Called internally before reserving a new form.
        
        Args:
            session: Database session
        """
        now = datetime.utcnow()
        
        stmt = (
            select(SoatForm)
            .where(
                and_(
                    SoatForm.status == FormStatus.RESERVED,
                    SoatForm.expires_at < now
                )
            )
        )
        
        result = await session.execute(stmt)
        expired_forms = result.scalars().all()
        
        for form in expired_forms:
            form.status = FormStatus.EXPIRED
            form.session_id = None
            form.session_slug = None
            
            logger.info(
                f"Form reservation expired - Form: {form.form_number}, "
                f"Session: {form.session_slug}"
            )
        
        if expired_forms:
            await session.commit()
    
    async def get_forms_stats(self) -> Dict[str, Any]:
        """
        Get statistics about forms.
        
        Returns:
            Dictionary with form statistics
        """
        async with db_manager.get_async_session("dbr", self.sponsor) as session:
            # Count by status
            stmt = select(SoatForm)
            result = await session.execute(stmt)
            all_forms = result.scalars().all()
            
            stats = {
                "total": len(all_forms),
                "available": sum(1 for f in all_forms if f.status == FormStatus.AVAILABLE),
                "reserved": sum(1 for f in all_forms if f.status == FormStatus.RESERVED),
                "used": sum(1 for f in all_forms if f.status == FormStatus.USED),
                "blocked": sum(1 for f in all_forms if f.status == FormStatus.BLOCKED),
                "expired": sum(1 for f in all_forms if f.status == FormStatus.EXPIRED),
            }
            
            # Check if we need more forms
            stats["needs_refill"] = stats["available"] < self.MIN_FORMS_THRESHOLD
            
            return stats

"""
Session Information Service

This service provides session information including owner validation data,
with visibility rules based on session status.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.insurance_session import InsuranceSession, SessionStatus
from app.models.client import Client
from app.models.vehicle import Vehicle
from app.models.vehicle_homologation import VehicleHomologation
from app.database.session import db_manager
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class SessionInfoService:
    """Service for retrieving session information with conditional visibility."""
    
    # States where full owner and vehicle info is visible
    PRE_QUOTE_STATES = [
        SessionStatus.CREATED,
        SessionStatus.STARTED,
        SessionStatus.VALIDATING,
        SessionStatus.VALIDATED,
        SessionStatus.VALIDATION_FAILED
    ]
    
    def __init__(self, sponsor: str):
        """
        Initialize the session info service.
        
        Args:
            sponsor: Sponsor identifier
        """
        self.sponsor = sponsor
    
    async def get_session_info(self, session_slug: str) -> Dict[str, Any]:
        """
        Get session information with conditional visibility based on status.
        
        **Visibility Rules:**
        - Pre-quote states (created, validating, validated, validation_failed):
          → Full owner and vehicle information visible
        - Post-quote states (quoting onwards):
          → Only session status and basic metadata
        
        Args:
            session_slug: Insurance session UUID slug
            
        Returns:
            Dictionary with session information:
            {
                "session_slug": str,
                "session_id": int,
                "status": str,
                "status_display": str,
                "is_owner": bool,
                "created_at": str,
                "updated_at": str,
                "can_view_details": bool,
                "owner_info": dict or None (only in pre-quote states),
                "vehicle_info": dict or None (only in pre-quote states),
                "message": str
            }
            
        Raises:
            ValidationError: If session not found
        """
        async with db_manager.get_async_session("dbr", self.sponsor) as session:
            # Get session with relationships
            stmt = (
                select(InsuranceSession)
                .options(
                    selectinload(InsuranceSession.client).options(
                        selectinload(Client.document_type),
                        selectinload(Client.city),
                        selectinload(Client.gender)
                    ),
                    selectinload(InsuranceSession.vehicle)
                )
                .where(InsuranceSession.slug == session_slug)
            )
            result = await session.execute(stmt)
            insurance_session = result.scalars().first()
            
            if not insurance_session:
                logger.warning(f"Session not found: {session_slug}")
                raise ValidationError("Sesión no encontrada")
            
            # Determine if details should be visible
            can_view_details = insurance_session.status in self.PRE_QUOTE_STATES
            
            # Build base response
            response = {
                "session_slug": insurance_session.slug,
                "session_id": insurance_session.id,
                "status": insurance_session.status.value,
                "status_display": self._get_status_display(insurance_session.status),
                "is_owner": insurance_session.is_owner,
                "created_at": insurance_session.created_at.isoformat(),
                "updated_at": insurance_session.updated_at.isoformat(),
                "can_view_details": can_view_details
            }
            
            # Add conditional information based on status
            if can_view_details:
                # Pre-quote states: Show full details
                response["owner_info"] = await self._build_owner_info(insurance_session)
                response["vehicle_info"] = await self._build_vehicle_info(
                    session, insurance_session
                )
                response["message"] = self._get_pre_quote_message(insurance_session.status)
            else:
                # Post-quote states: Hide sensitive details
                response["owner_info"] = None
                response["vehicle_info"] = None
                response["message"] = (
                    "Información de propietario y vehículo no disponible. "
                    "La sesión está en proceso de cotización o posterior."
                )
            
            logger.info(
                f"Session info retrieved - Slug: {session_slug}, "
                f"Status: {insurance_session.status.value}, "
                f"Details visible: {can_view_details}"
            )
            
            return response
    
    async def _build_owner_info(
        self,
        insurance_session: InsuranceSession
    ) -> Optional[Dict[str, Any]]:
        """
        Build owner information dictionary.
        
        Args:
            insurance_session: Insurance session with loaded client relationship
            
        Returns:
            Dictionary with owner information or None if no client
        """
        if not insurance_session.client:
            return None
        
        client = insurance_session.client
        
        return {
            "client_id": client.id,
            "document_type": client.document_type.code if client.document_type else None,
            "document_type_name": client.document_type.name if client.document_type else None,
            "document_number": client.document_number,
            "first_name": client.first_name,
            "last_name": client.last_name,
            "second_last_name": client.second_last_name,
            "full_name": client.full_name,
            "email": client.email,
            "phone": client.phone,
            "address": client.address,
            "city": client.city.name if client.city else None,
            "birth_date": client.birth_date.isoformat() if client.birth_date else None,
            "gender": client.gender.name if client.gender else None
        }
    
    async def _build_vehicle_info(
        self,
        session: Any,
        insurance_session: InsuranceSession
    ) -> Optional[Dict[str, Any]]:
        """
        Build vehicle information dictionary including homologations.
        
        Args:
            session: Database session
            insurance_session: Insurance session with loaded vehicle relationship
            
        Returns:
            Dictionary with vehicle information or None if no vehicle
        """
        if not insurance_session.vehicle:
            return None
        
        vehicle = insurance_session.vehicle
        
        # Get homologations for this session
        stmt = (
            select(VehicleHomologation)
            .where(VehicleHomologation.session_id == insurance_session.id)
        )
        result = await session.execute(stmt)
        homologations = result.scalars().all()
        
        return {
            "vehicle_id": vehicle.id,
            "license_plate": vehicle.license_plate,
            "brand": vehicle.brand,
            "line": vehicle.line,
            "model_year": vehicle.model_year,
            "vehicle_class": vehicle.vehicle_class,
            "vehicle_class_id": vehicle.vehicle_class_id,
            "service_type": vehicle.service_type,
            "service_type_id": vehicle.service_type_id,
            "color": vehicle.color,
            "engine_cc": vehicle.engine_cc,
            "fuel_type": vehicle.fuel_type,
            "chassis_number": vehicle.chassis_number,
            "engine_number": vehicle.engine_number,
            "vin_number": vehicle.vin_number,
            "serial_number": vehicle.serial_number,
            "seats": vehicle.seats,
            "tonnage": vehicle.tonnage,
            "gross_weight": vehicle.gross_weight,
            "body_type": vehicle.body_type,
            "homologations": [
                {
                    "id": h.id,
                    "class_code": h.class_code,
                    "class_description": h.class_description,
                    "transport_type_code": h.transport_type_code,
                    "brand_code": h.brand_code,
                    "line_code": h.line_code,
                    "destination_code": h.destination_code
                }
                for h in homologations
            ]
        }
    
    def _get_status_display(self, status: SessionStatus) -> str:
        """
        Get human-readable status display text.
        
        Args:
            status: Session status enum
            
        Returns:
            Human-readable status text
        """
        status_map = {
            SessionStatus.CREATED: "Sesión creada",
            SessionStatus.STARTED: "Sesión iniciada",
            SessionStatus.VALIDATING: "Validando propietario",
            SessionStatus.VALIDATED: "Propietario validado",
            SessionStatus.VALIDATION_FAILED: "Validación de propietario fallida",
            SessionStatus.QUOTING: "Generando cotización",
            SessionStatus.QUOTED: "Cotización generada",
            SessionStatus.QUOTE_FAILED: "Error en cotización",
            SessionStatus.SELECTING: "Seleccionando planes",
            SessionStatus.SELECTED: "Planes seleccionados",
            SessionStatus.SELECTION_FAILED: "Error en selección",
            SessionStatus.ISSUING: "Emitiendo pólizas",
            SessionStatus.ISSUED: "Pólizas pre-expedidas",
            SessionStatus.ISSUE_FAILED: "Error en emisión",
            SessionStatus.PAYMENT_PENDING: "Pago pendiente",
            SessionStatus.PAYMENT_CONFIRMED: "Pago confirmado",
            SessionStatus.PAYMENT_FAILED: "Pago fallido",
            SessionStatus.COMPLETED: "Completado",
            SessionStatus.CANCELLED: "Cancelado",
            SessionStatus.EXPIRED: "Expirado"
        }
        return status_map.get(status, status.value)
    
    def _get_pre_quote_message(self, status: SessionStatus) -> str:
        """
        Get contextual message for pre-quote states.
        
        Args:
            status: Session status enum
            
        Returns:
            Contextual message based on status
        """
        if status == SessionStatus.CREATED or status == SessionStatus.STARTED:
            return "Sesión creada. Inicie la validación de propietario."
        elif status == SessionStatus.VALIDATING:
            return "Validación de propietario en proceso."
        elif status == SessionStatus.VALIDATED:
            return "Propietario validado exitosamente. Puede proceder a cotizar."
        elif status == SessionStatus.VALIDATION_FAILED:
            return "La validación de propietario falló. Verifique los datos e intente nuevamente."
        else:
            return "Información de sesión disponible."

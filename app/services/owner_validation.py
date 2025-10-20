"""
Owner Validation Service

This service handles the complete flow of vehicle owner validation:
1. Create client and vehicle records with minimal information
2. Query RUNT API for additional data
3. Update records with RUNT information
4. Validate ownership
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from requests import session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client, DocumentType
from app.models.vehicle import Vehicle
from app.models.insurance_session import InsuranceSession, SessionStatus
from app.models.vehicle_homologation import VehicleHomologation
from app.services.external.runt_client import RUNTClient
from app.database.session import db_manager
from app.core.exceptions import ExternalServiceError, ValidationError

logger = logging.getLogger(__name__)


class OwnerValidationService:
    """Service for validating vehicle ownership and managing client/vehicle data."""
    
    def __init__(self, sponsor: str):
        """
        Initialize the owner validation service.
        
        Args:
            sponsor: Sponsor identifier
        """
        self.sponsor = sponsor
        self.runt_client = RUNTClient(sponsor)
    
    async def validate_owner(
        self,
        document_type_code: int,
        document_number: str,
        license_plate: str
    ) -> Dict[str, Any]:
        """
        Validate vehicle ownership with complete flow.
        
        Process:
        1. Create/get client with minimal info (document type/number)
        2. Create/get vehicle with minimal info (license plate)
        3. Query RUNT API for additional data
        4. Update client and vehicle with RUNT data if available
        5. Validate ownership
        
        Args:
            document_type_code: Client document type CODE
            document_number: Client document number
            license_plate: Vehicle license plate
            
        Returns:
            Dictionary with validation results:
            {
                "is_owner": bool,
                "message": str,
                "client_id": int,
                "vehicle_id": int,
                "owner_data": dict or None,
                "vehicle_data": dict or None,
                "runt_available": bool,
                "insured_session_id": int
            }
        """
        # Step 1: Create or get client and vehicle with minimal info
        client_id, document_type, vehicle_id, insured_session_id, insured_session_slug = await self._create_or_get_minimal_records(
            document_type_code, document_number, license_plate
        )
        
        # Update session to VALIDATING status
        await self._update_insured_session_status(insured_session_id, SessionStatus.VALIDATING, None)
        
        # Step 2: Query RUNT API
        try:
            runt_data, runt_available = await self._query_runt_service(license_plate)
        except Exception as e:
            # Mark as validation failed
            await self._update_insured_session_status(insured_session_id, SessionStatus.VALIDATION_FAILED, None)
            raise
        
        if not runt_available:
            await self._update_insured_session_status(insured_session_id, SessionStatus.VALIDATION_FAILED, None)
            return {"message": "Servicio de RUNT no disponible", "runt_available": False}
        
        vehicle_data = runt_data.get("vehicle", {}) if runt_data else {}
        owner_data = runt_data.get("owner", []) if runt_data else []
        
        # Step 3: Update records with RUNT data if available
        if runt_available and (vehicle_data or owner_data):
            vehicle_data = await self._update_records_with_runt_data(
                client_id, document_type, vehicle_id, insured_session_id, owner_data, vehicle_data
            )
        
        if not vehicle_data.get('plate_number'):
            await self._update_insured_session_status(insured_session_id, SessionStatus.VALIDATION_FAILED, None)
            return {"message": "Verifique la placa del vehículo e intente nuevamente.", "runt_available": True}
        
        # Step 4: Validate ownership
        is_owner, validation_message, owner = self._validate_ownership(
            document_type, document_number, owner_data, runt_available
        )
        
        # Update insured_session status to validated and is_owner
        await self._update_insured_session_status(insured_session_id, SessionStatus.VALIDATED, is_owner)
        
        return {
            "is_owner": is_owner,
            "message": validation_message,
            "client_id": client_id,
            "vehicle_id": vehicle_id,
            "owner_data": owner if owner else None,
            "vehicle_data": vehicle_data if vehicle_data else None,
            "runt_available": runt_available,
            "session_slug": insured_session_slug
        }
    
    async def _create_or_get_minimal_records(
        self,
        document_type_code: int,
        document_number: str,
        license_plate: str
    ) -> Tuple[int, int]:
        """
        Create or get client and vehicle with minimal information.
        
        Args:
            document_type_code: Client document type CODE
            document_number: Client document number
            license_plate: Vehicle license plate
            
        Returns:
            Tuple of (client_id, document_type, vehicle_id, insured_session_id, insured_session_slug)
        """
        
        async with db_manager.get_async_session("dbw", self.sponsor) as session:
            # Get or create client
            stmt = select(
                DocumentType.id, DocumentType.code, DocumentType.runt_code
            ).where(
                DocumentType.code == document_type_code,
                DocumentType.status == 1
            )
            result = await session.execute(stmt)
            document_type = result.first()
            if not document_type:
                raise ValidationError(f"Invalid document type CODE: {document_type_code}")

            stmt = select(Client).where(
                Client.document_type_id == document_type.id,
                Client.document_number == document_number
            )
            result = await session.execute(stmt)
            client = result.scalars().first()
            
            if not client:
                # Create with minimal info
                client = Client(
                    document_type_id=document_type.id,
                    document_number=document_number,
                ) # Will be updated from RUNT
                session.add(client)
                await session.flush()
                
                logger.info(
                    f"New client created with minimal info - ID: {client.id}, "
                    f"Document: {document_type.code}/{document_number}"
                )
            else:
                logger.info(f"Existing client found - ID: {client.id}")
            
            client_id = client.id
            
            # Get or create vehicle
            stmt_vehicle = select(Vehicle).where(
                Vehicle.license_plate == license_plate
            )
            result_vehicle = await session.execute(stmt_vehicle)
            vehicle = result_vehicle.scalars().first()
            
            if not vehicle:
                # Create with minimal info
                vehicle = Vehicle(
                    license_plate=license_plate,
                ) # Will be updated from RUNT
                session.add(vehicle)
                await session.flush()
                
                logger.info(
                    f"New vehicle created with minimal info - ID: {vehicle.id}, "
                    f"Plate: {license_plate}"
                )
            else:
                logger.info(f"Existing vehicle found - ID: {vehicle.id}")
            
            vehicle_id = vehicle.id
            
            insured_session = InsuranceSession.create_session(
                client_id=client_id,
                vehicle_id=vehicle_id,
                is_owner=False,
                status=SessionStatus.STARTED
            )
            session.add(insured_session)
            await session.flush()

            logger.info(f"New insurance session created - ID: {insured_session.id}")
            
            insured_session_id = insured_session.id
            insured_session_slug = insured_session.slug
            # Commit minimal records
            await session.commit()

        return client_id, document_type, vehicle_id, insured_session_id, insured_session_slug

    async def _query_runt_service(
        self,
        license_plate: str
    ) -> Tuple[Optional[Dict[str, Any]], bool]:
        """
        Query RUNT API for vehicle and owner information.
        
        Args:
            license_plate: Vehicle license plate
            
        Returns:
            Tuple of (runt_data, runt_available)
        """
        try:
            runt_data = await self.runt_client.get_vehicle_info(
                license_plate=license_plate
            )
            # if not runt_data:
            #     raise ExternalServiceError("RUNT", "Empty response from RUNT service")
            logger.info(f"RUNT query successful for plate: {license_plate}")
            return runt_data, True
        except ExternalServiceError as e:
            logger.warning(
                f"RUNT query failed for plate {license_plate}: {str(e)}. "
                "Continuing with minimal data."
            )
            return None, False
    
    async def _update_records_with_runt_data(
        self,
        client_id: int,
        document_type: Any,
        vehicle_id: int,
        session_id: int,
        owner_data: Dict[str, Any],
        vehicle_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update client and vehicle records with RUNT data.
        
        Args:
            client_id: Client ID to update
            vehicle_id: Vehicle ID to update
            owner_data: Owner data from RUNT
            vehicle_data: Vehicle data from RUNT
            
        Returns:
            Updated vehicle_data with homologation IDs
        """
        async with db_manager.get_async_session("dbw", self.sponsor) as session:
            async with session.begin():
                await self._update_client(session, client_id, document_type, owner_data)
                if vehicle_data.get('plate_number'):
                    await self._update_vehicle(session, vehicle_id, vehicle_data)
                    if vehicle_data.get('homologations'):
                        homologations_with_ids = await self._insert_vehicle_homologations(
                            session, session_id, vehicle_data['homologations']
                        )
                        # Update vehicle_data with homologations that now include IDs
                        vehicle_data['homologations'] = homologations_with_ids

            logger.info(
                f"✅ RUNT data synchronized (client_id={client_id}, vehicle_id={vehicle_id})"
            )
        
        return vehicle_data

    async def _update_client(self, session: AsyncSession, client_id: int, document_type: Any, owner_data: Dict[str, Any]):
        if not owner_data:
            return

        result = await session.execute(select(Client).where(Client.id == client_id))
        client = result.scalars().first()
        if not client:
            logger.warning(f"Client not found: {client_id}")
            return

        updatable_fields = {"full_name", "first_name", "last_name", "second_last_name"}
        for owner in owner_data:
            if owner.get("document_type") == document_type.runt_code and owner.get("document_number") == client.document_number:
                for key, value in owner.items():
                    if key in updatable_fields: # value not in (None, "")
                        setattr(client, key, value)

        logger.info(f"Client updated with RUNT data - ID: {client_id}")
    
    async def _update_vehicle(
        self, session: AsyncSession, vehicle_id: int, vehicle_data: Dict[str, Any]
    ):
        if not vehicle_data:
            return

        result = await session.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
        vehicle = result.scalars().first()
        if not vehicle:
            logger.warning(f"Vehicle not found: {vehicle_id}")
            return

        updatable_fields = {
            "consultation_id",
            "consultation_success",
            "service_observation",
            "service_type_id",
            "service_type",
            "vehicle_class_id",
            "vehicle_class",
            "brand_id",
            "brand",
            "line_id",
            "line",
            "model_year",
            "color_id",
            "color",
            "serial_number",
            "engine_number",
            "chassis_number",
            "vin_number",
            "engine_cc",
            "tonnage",
            "gross_weight",
            "seats",
            "body_type_id",
            "body_type",
            "fuel_type_id",
            "fuel_type",
            "vehicle_state",
            "transit_authority",
        }

        for key, value in vehicle_data.items():
            if key in updatable_fields: # and value not in (None, "")
                setattr(vehicle, key, value)

        logger.info(f"Vehicle updated with RUNT data - ID: {vehicle_id}")
    
    async def _insert_vehicle_homologations(
        self,
        session: AsyncSession,
        session_id: int,
        homologations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Insert vehicle homologations and return the created records with IDs.
        
        Returns:
            List of dictionaries with homologation data including database IDs
        """
        if not homologations:
            return []
        
        records = [
            VehicleHomologation(
                session_id=session_id,
                class_code=h["class_code"],
                class_description=h["class_description"],
                transport_type_code=h["transport_type_code"],
                brand_code=h["brand_code"],
                line_code=h["line_code"],
                destination_code=h["destination_code"]
            )
            for h in homologations
            if h.get("class_code")  # evita insertar vacíos
        ]

        if records:
            session.add_all(records)
            await session.flush()  # Flush to get IDs assigned
            
            # Build return list with IDs
            homologations_with_ids = [
                {
                    "id": record.id,
                    "class_code": record.class_code,
                    "class_description": record.class_description,
                    "transport_type_code": record.transport_type_code,
                    "brand_code": record.brand_code,
                    "line_code": record.line_code,
                    "destination_code": record.destination_code
                }
                for record in records
            ]
            
            logger.info(f"Inserted {len(records)} homologation(s) for session_id={session_id}")
            return homologations_with_ids
        
        return []
    
    def _validate_ownership(
        self,
        request_doc_type: int,
        request_doc_number: str,
        owner_data: List[Dict[str, Any]],
        runt_available: bool
    ) -> Tuple[bool, str]:
        """
        Validate if the provided document matches the vehicle owner.
        
        Args:
            request_doc_type: Requested document type ID
            request_doc_number: Requested document number
            owner_data: Owner data from RUNT
            runt_available: Whether RUNT data is available
        Returns:
            Tuple of (is_owner, validation_message, owner)
        """
        
        if not owner_data:
            # TODO: Consider if this should be a different message
            return False, f"El documento no coincide con el propietario del vehículo.", None

        request_doc_type_str = str(request_doc_type.runt_code).upper()
        request_doc_number_clean = request_doc_number.strip()
        
        _owner = {}
        for owner in owner_data:
            owner_doc_type = owner.get("document_type", "").upper()
            owner_doc_number = owner.get("document_number", "").strip()
            
            is_owner = (
                owner_doc_type == request_doc_type_str and
                owner_doc_number == request_doc_number_clean
            )
            if is_owner:
                _owner = {
                    'document_type': owner.get('document_type', ''),
                    'document_number': owner.get('document_number', ''),
                    'full_name': owner.get('full_name', ''),
                    'first_name': owner.get('first_name', ''),
                    'last_name': owner.get('last_name', ''),
                    'second_last_name': owner.get('second_last_name', ''),
                }
                break
        
        if is_owner:
            logger.info(
                f"Owner validated successfully - "
                f"Document: {request_doc_type.code}/{request_doc_number}"
            )
            return True, "Owner validated successfully", _owner
        else:
            logger.warning(
                f"Ownership validation failed - "
                f"Provided: {request_doc_type.code}/{request_doc_number}, "
            )
            return False, f"El documento no coincide con el propietario del vehículo.", None

    async def _update_insured_session_status(self, session_id: int, new_status: SessionStatus, is_owner: Optional[bool] = None):
        """
        Update the status of an insurance session.
        """
        async with db_manager.get_async_session("dbw", self.sponsor) as session:
            stmt = select(InsuranceSession).where(InsuranceSession.id == session_id)
            result = await session.execute(stmt)
            insured_session = result.scalars().first()
            if insured_session:
                insured_session.status = new_status
                if is_owner is not None:
                    insured_session.is_owner = is_owner
                await session.commit()
                logger.info(f"Insurance session {session_id} status updated to {new_status}")
            else:
                logger.warning(f"Insurance session not found: {session_id}")
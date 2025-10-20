"""
Quote Service

This service handles the quote flow:
1. Validate session exists and meets requirements (is_owner=true, status=validated)
2. Validate that class_code exists in vehicle_homologations for the session
3. Validate products (mandatory products required, inactive products rejected)
4. Create or update vehicle_homologations_selection
5. Call external provider APIs for each product (parallel execution)
6. Store external quote responses
"""

import logging
import asyncio
from datetime import datetime, timedelta
import traceback
from typing import Dict, Any, Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.insurance_session import InsuranceSession, SessionStatus
from app.models.vehicle_homologation import VehicleHomologation
from app.models.vehicle_homologation_selection import VehicleHomologationSelection
from app.models.product import Product
from app.models.quote_product import QuoteProduct
from app.models.quote_product_option import QuoteProductOption, OptionAvailabilityStatus
from app.models.quote_product_selection import QuoteProductSelection
from app.models.soat_form import FormStatus
from app.models.client import Client
from app.models.vehicle import Vehicle
from app.models.plan_ap import PlanAP
from app.models.vehicle_class import VehicleClass
from app.models.plan_vehicle_class import PlanVehicleClass
from app.database.session import db_manager
from app.core.exceptions import ExternalServiceError, ValidationError
from app.core.utils import str_to_date, change_format_date
from app.services.external.soat import SOATClient, SOATQuoteResponse
from app.services.external.ap_client import APClient, APQuoteResponse
from app.services.external.rce_client import RCEClient, RCEQuoteResponse
from app.services.external.expedition_client import ExpeditionClient, ExpeditionRCEClient, ExpeditionResponse
from app.services.soat_forms_manager import SoatFormsManager
from app.aws.secrets import AWSSecretsManager

logger = logging.getLogger(__name__)


class QuoteService:
    """Service for handling insurance quote requests."""
    
    def __init__(self, sponsor: str):
        """
        Initialize the quote service.
        
        Args:
            sponsor: Sponsor identifier
            soat_base_url: Base URL for SOAT API (optional, for testing)
        """
        self.sponsor = sponsor
        self.config = AWSSecretsManager().get_secret("config", sponsor)
    
    async def create_quote(
        self,
        session_slug: str,
        class_code: str,
        products: List[str]
    ) -> Dict[str, Any]:
        """
        Create or update a quote for a session.
        
        Process:
        1. Validate session exists with slug
        2. Validate session has is_owner=true and status=validated
        3. Find homologation with class_code for this session
        4. Validate products (mandatory + no inactive/unknown)
        5. Create or update vehicle_homologations_selection
        6. Update session status to QUOTED
        
        Args:
            session_slug: Insurance session UUID slug
            class_code: Vehicle class code from homologations
            products: List of product codes
            
        Returns:
            Dictionary with quote results:
            {
                "success": bool,
                "message": str,
                "session_id": int,
                "session_slug": str,
                "selected_homologation_id": int,
                "class_code": str,
                "products": list
            }
            
        Raises:
            ValidationError: If validation fails
        """
        async with db_manager.get_async_session("dbw", self.sponsor) as session:
            # Step 1: Validate session exists
            insurance_session = await self._validate_session(session, session_slug)
            
            # Step 2: Validate session requirements
            await self._validate_session_requirements(insurance_session)
            
            # Step 3: Find homologation with class_code
            homologation = await self._find_homologation(
                session, insurance_session.id, class_code
            )
            
            # Step 4: Validate products
            validated_products = await self._validate_products(session, products)
            
            # Step 5: Create or update selection
            selection = await self._create_or_update_selection(
                session, insurance_session.id, homologation.id
            )
            
            # Step 5.1: Create or update product selection
            await self._create_or_update_product_selection(
                session, insurance_session.id, validated_products
            )
            
            # Update session to QUOTING status
            insurance_session.status = SessionStatus.QUOTING
            await session.commit()

            # Step 6: Fetch external quotes for all products (parallel execution)
            try:
                external_quotes = await self._fetch_external_quotes(
                    session, insurance_session, homologation, validated_products
                )
            except Exception as e:
                # Mark as quote failed
                insurance_session.status = SessionStatus.QUOTE_FAILED
                await session.commit()
                raise

            # Step 7: Update session status to QUOTED
            insurance_session.status = SessionStatus.QUOTED
            
            await session.commit()
            
            logger.info(
                f"Quote created successfully - Session: {session_slug}, "
                f"Homologation ID: {homologation.id}, Class: {class_code}, "
                f"Products: {products}"
            )
            
            return {
                "success": True,
                "message": "Quote created successfully",
                "session_slug": insurance_session.slug,
                "products": [
                    {
                        "product_code": eq["product_code"],
                        "product_name": eq["product_name"],
                        "mandatory": eq["mandatory"],
                        "plans": [eq.get("plans")] if isinstance(eq.get("plans"), dict) else eq.get("plans"),
                        "success": eq.get("success")
                    }
                    for eq in external_quotes
                ]
                # "external_quotes": [
                #     {
                #         "product_code": eq["product_code"],
                #         "provider": eq["provider"],
                #         "success": eq["success"],
                #         "total": eq["total"],
                #         "premium": eq["premium"],
                #         "start_date": eq["start_date"],
                #         "end_date": eq["end_date"],
                #         "error_message": eq.get("error_message")
                #     }
                #     for eq in external_quotes
                # ]
            }
    
    async def _validate_session(
        self,
        session: AsyncSession,
        session_slug: str
    ) -> InsuranceSession:
        """
        Validate that session exists.
        
        Args:
            session: Database session
            session_slug: Insurance session UUID slug
            
        Returns:
            InsuranceSession instance
            
        Raises:
            ValidationError: If session not found
        """
        stmt = select(InsuranceSession).where(
            InsuranceSession.slug == session_slug
        )
        result = await session.execute(stmt)
        insurance_session = result.scalars().first()
        
        if not insurance_session:
            logger.warning(f"Session not found: {session_slug}")
            raise ValidationError(f"Insurance session not found: {session_slug}")
        
        logger.info(f"Session found - ID: {insurance_session.id}, Slug: {session_slug}")
        return insurance_session
    
    async def _validate_session_requirements(
        self,
        insurance_session: InsuranceSession
    ):
        """
        Validate that session meets requirements for quoting.
        
        Requirements:
        - is_owner must be True
        - status must be VALIDATED
        
        Args:
            insurance_session: InsuranceSession instance
            
        Raises:
            ValidationError: If requirements not met
        """
        if not insurance_session.is_owner:
            logger.warning(
                f"Session {insurance_session.slug} - Owner validation failed. "
                f"is_owner={insurance_session.is_owner}"
            )
            raise ValidationError(
                "El cliente no es el propietario del vehículo."
            )
        
        if insurance_session.status not in [SessionStatus.VALIDATED, SessionStatus.QUOTED, SessionStatus.SELECTED]:
            logger.warning(
                f"Session {insurance_session.slug} - Invalid status. "
                f"Current: {insurance_session.status.value}, Required: validated|quoted|selected"
            )
            raise ValidationError(
                f"La sesión debe estar en estado 'validated', 'quoted' o 'selected', "
                f"el estado actual es '{insurance_session.status.value}'"
            )
        
        logger.info(f"Session {insurance_session.slug} meets all requirements")
    
    async def _find_homologation(
        self,
        session: AsyncSession,
        session_id: int,
        class_code: str
    ) -> VehicleHomologation:
        """
        Find homologation with class_code for the session.
        
        Args:
            session: Database session
            session_id: Insurance session ID
            class_code: Vehicle class code
            
        Returns:
            VehicleHomologation instance
            
        Raises:
            ValidationError: If homologation not found
        """
        stmt = select(VehicleHomologation).where(
            and_(
                VehicleHomologation.session_id == session_id,
                VehicleHomologation.class_code == class_code
            )
        )
        result = await session.execute(stmt)
        homologation = result.scalars().first()
        
        if not homologation:
            logger.warning(
                f"Homologation not found - Session ID: {session_id}, "
                f"Class Code: {class_code}"
            )
            raise ValidationError(
                f"La clase de vehículo seleccionada no es válida."
            )
        
        logger.info(
            f"Homologation found - ID: {homologation.id}, "
            f"Class: {class_code}, Session ID: {session_id}"
        )
        return homologation
    
    async def _validate_products(
        self,
        session: AsyncSession,
        product_codes: List[str]
    ) -> List[Product]:
        """
        Validate products for the quote.
        
        Validations:
        - All product codes must exist in products table
        - All products must be active (status=1)
        - All mandatory products must be included
        
        Args:
            session: Database session
            product_codes: List of product codes from request
            
        Returns:
            List of validated Product instances
            
        Raises:
            ValidationError: If validation fails
        """
        # Get all active products
        stmt = select(Product).where(Product.status == 1)
        result = await session.execute(stmt)
        all_active_products = result.scalars().all()
        
        # Create dictionaries for easy lookup
        active_products_dict = {p.code: p for p in all_active_products}
        mandatory_products = [p for p in all_active_products if p.mandatory]
        mandatory_codes = {p.code for p in mandatory_products}
        
        # Remove duplicates from input
        unique_product_codes = list(set(product_codes))
        
        # Validation 1: Check for unknown or inactive products
        invalid_products = []
        for code in unique_product_codes:
            if code not in active_products_dict:
                invalid_products.append(code)
        
        if invalid_products:
            logger.warning(
                f"Invalid products found: {invalid_products}"
            )
            raise ValidationError(
                f"Los siguientes productos son inválidos o inactivos: {', '.join(invalid_products)}. "
                "Por favor, elimínalos de tu solicitud."
            )
        
        # Validation 2: Check for missing mandatory products
        provided_codes = set(unique_product_codes)
        missing_mandatory = mandatory_codes - provided_codes
        
        if missing_mandatory:
            missing_names = [
                f"{active_products_dict[code].name} ({code})"
                for code in missing_mandatory
            ]
            logger.warning(
                f"Missing mandatory products: {missing_mandatory}"
            )
            raise ValidationError(
                f"Los siguientes productos son obligatorios: {', '.join(missing_names)}"
            )
        
        # Get validated product instances
        validated_products = [active_products_dict[code] for code in unique_product_codes]
        
        logger.info(
            f"Products validated successfully - "
            f"Total: {len(validated_products)}, "
            f"Mandatory: {len([p for p in validated_products if p.mandatory])}"
        )
        
        return validated_products
    
    async def _fetch_external_quotes(
        self,
        session: AsyncSession,
        insurance_session: InsuranceSession,
        homologation: VehicleHomologation,
        products: List[Product]
    ) -> List[Dict[str, Any]]:
        """
        Fetch external quotes for all products in parallel.
        
        Args:
            session: Database session
            insurance_session: InsuranceSession instance with loaded relationships
            homologation: Selected VehicleHomologation
            products: List of products to quote
            
        Returns:
            List of external quote results
        """
        # Load client and vehicle relationships
        await session.refresh(insurance_session, ["client", "vehicle"])
        
        client = insurance_session.client
        vehicle = insurance_session.vehicle
        
        await session.refresh(client, ["document_type"])
        # Update client and vehicle information as needed
        await session.commit() 
        # Create tasks for each product
        tasks = []
        for product in products:
            if product.code == "SOAT":
                task = self._fetch_soat_quote(
                    insurance_session, client, vehicle, homologation, product
                )
                tasks.append(task)
            elif product.code == "AP":
                task = self._fetch_ap_options(
                    insurance_session, product, homologation.class_code
                )
                tasks.append(task)
            elif product.code == "RCE":
                task = self._fetch_rce_quote(
                    insurance_session, client, vehicle, homologation, product
                )
                tasks.append(task)

        # Execute all tasks in parallel
        if tasks:
            logger.info(f"Fetching {len(tasks)} external quotes in parallel")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and log errors
            valid_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"External quote task {i} failed: {str(result)}")
                    message = str(result) if isinstance(result, ValidationError) or isinstance(result, ExternalServiceError) else "Detalle no disponible"
                    raise ValidationError(f"No se ha podido obtener la cotización de uno o varios productos: {message}")
                valid_results.append(result)
            
            return valid_results
        
        return []
    
    async def _fetch_soat_quote(
        self,
        insurance_session: InsuranceSession,
        client: Client,
        vehicle: Vehicle,
        homologation: VehicleHomologation,
        product: Product
    ) -> Dict[str, Any]:
        """
        Fetch SOAT quote from Mundial Seguros.
        
        Args:
            session: Database session
            insurance_session: InsuranceSession with loaded client and vehicle
            homologation: Selected VehicleHomologation
            product: Product instance (SOAT)
            
        Returns:
            Dictionary with quote result
        """
        async with db_manager.get_async_session("dbw", self.sponsor) as session:
            soat_client = SOATClient(self.sponsor)
            
            logger.info(
                f"Fetching SOAT quote - Session: {insurance_session.slug}, "
                f"Plate: {vehicle.license_plate}"
            )
            
            try:
                # Call SOAT API
                quote_response, log_id = await soat_client.calculate_quote(
                    class_code=homologation.class_code,
                    cylinder_capacity=vehicle.engine_cc,
                    tonnage=float(vehicle.tonnage or 0.0),
                    model_year=vehicle.model_year,
                    seats=vehicle.seats,
                    license_plate=vehicle.license_plate,
                    document_type_code=str(client.document_type.soat_id),
                    document_number=client.document_number
                )
                
                logger.info(
                    f"SOAT quote fetched successfully - Total: "
                )
                # quote_response = SOATQuoteResponse(quote_response)
                quote_product_id = await self._get_quote_product(
                    log_id, insurance_session.id, product
                )
                quote_response = SOATQuoteResponse(quote_response)
                if not quote_response:
                    raise ValidationError("Ocurrió un error al obtener la respuesta de cotización para SOAT.")
                
                start_date = str_to_date(quote_response.start_date, "%d/%m/%Y")
                if not start_date:
                    raise ValidationError("Ocurrió un error al calcular la cotización de SOAT.")
                
                days_until_expiration = (start_date - datetime.now()).days
                if days_until_expiration > int(self.config.get("soat_max_days_until_expiration", 60)):  # More than configured months
                    logger.warning(
                        f"SOAT policy too far from expiration - "
                        f"Days until expiration: {days_until_expiration}"
                    )
                    raise ValidationError("No puedes comprar tu SOAT porque falta mucho para su vencimiento.")
                
                stmt = select(QuoteProductOption).where(
                    QuoteProductOption.quote_product_id == quote_product_id,
                )
                result = await session.execute(stmt)
                existing_option = result.scalars().first()
                
                option_id = None
                # Update existing option or create new ones
                if existing_option:
                    # Update existing option
                    existing_option.price = quote_response.policy_total_value
                    existing_option.coverage = quote_response.to_dict()
                    existing_option.status = True
                    option_id = existing_option.id
                else:
                    # Create new option
                    option = QuoteProductOption(
                        quote_product_id=quote_product_id,
                        plan_name="SOAT",
                        price=quote_response.policy_total_value,
                        coverage=quote_response.to_dict()
                    )
                    session.add(option)
                await session.flush()
                
                quote_response.option_id = option.id if not option_id else option_id
                
                await session.commit()
                
                return {
                    "product_code": product.code,
                    "product_name": product.name,
                    "mandatory": product.mandatory,
                    "success": True,
                    "plans": quote_response.to_dict(),
                }
                
            except Exception as e:
                logger.error(f"Unexpected error fetching SOAT quote: {str(e)}", exc_info=True)
                raise
    
    async def _fetch_ap_options(
        self,
        insurance_session: InsuranceSession,
        product: Product,
        class_code: str
    ) -> Dict[str, Any]:
        """
        Fetch AP (Accidentes Personales) plan options from Mundial Seguros.
        Validates plan availability based on vehicle class from vehicle_homologations_selection.
        
        Args:
            session: Database session
            insurance_session: InsuranceSession instance
            product: Product instance (AP)
            class_code: Selected vehicle class code
            
        Returns:
            Dictionary with plan options result
        """
        async with db_manager.get_async_session("dbw", self.sponsor) as session:
            ap_client = APClient(self.sponsor)
            
            logger.info(
                f"Fetching AP plan options - Session: {insurance_session.slug}"
            )
            
            try:
                logger.info(f"Selected vehicle class code: {class_code}")
                
                # Call AP API to get plan options
                quote_response, log_id = await ap_client.get_plan_options()
                
                # Get or create QuoteProduct
                quote_product_id = await self._get_quote_product(
                    log_id, insurance_session.id, product
                )
                
                stmt = select(QuoteProductOption).where(
                    QuoteProductOption.quote_product_id == quote_product_id,
                )
                result = await session.execute(stmt)
                existing_options = result.scalars().all()
                
                quote_response = APQuoteResponse(quote_response)
                
                # Get VehicleClass for the selected class_code
                stmt_vehicle_class = select(VehicleClass).where(
                    VehicleClass.code == class_code,
                    VehicleClass.status == True
                )
                result_vehicle_class = await session.execute(stmt_vehicle_class)
                vehicle_class = result_vehicle_class.scalars().first()
                
                # Track availability statistics
                available_plans = 0
                unavailable_plans = 0
                
                # Update existing options or create new ones
                existing_plan_names = {opt.plan_name: opt for opt in existing_options}
                
                # Store each plan as a QuoteProductOption with availability validation
                for plan in quote_response.plans:
                    # Determine availability based on vehicle class
                    availability_status = await self._check_ap_plan_availability(
                        session, plan, vehicle_class
                    )
                    
                    status = True if availability_status == OptionAvailabilityStatus.AVAILABLE else False
                    plan.availability = status
                    
                    if availability_status == OptionAvailabilityStatus.AVAILABLE:
                        available_plans += 1
                    else:
                        unavailable_plans += 1
                    
                    option = existing_plan_names.get(plan.desc_type)
                    if option:
                        # Update existing option
                        option.price = plan.prices.get("policy_value")
                        option.coverage = plan.to_dict()
                        option.status = status
                        option.availability_status = availability_status
                    else:
                        # Create new option
                        option = QuoteProductOption(
                            quote_product_id=quote_product_id,
                            plan_name=plan.desc_type,
                            price=plan.prices.get("policy_value"),
                            coverage=plan.to_dict(),
                            status=status,
                            availability_status=availability_status
                        )
                        session.add(option)
                        await session.flush()
                    plan.option_id = option.id
                
                # Deactivate existing options not in the new plans
                existing_plan_names_set = {plan.desc_type for plan in quote_response.plans}
                for existing_option in existing_options:
                    if existing_option.plan_name not in existing_plan_names_set:
                        existing_option.status = False
                        existing_option.availability_status = OptionAvailabilityStatus.INACTIVE

                await session.flush()
                
                logger.info(
                    f"AP plan options stored successfully - "
                    f"Total plans: {len(quote_response.plans)}, "
                    f"Available: {available_plans}, Unavailable: {unavailable_plans}"
                )
                
                # If NO plans are available for this vehicle class, deactivate the AP product
                if available_plans == 0:
                    logger.warning(
                        f"No AP plans available for vehicle class {class_code}. "
                        f"Deactivating AP product for session {insurance_session.slug}"
                    )
                    stmt_quote_product = select(QuoteProduct).where(
                        QuoteProduct.id == quote_product_id
                    )
                    result_qp = await session.execute(stmt_quote_product)
                    quote_product = result_qp.scalars().first()
                    if quote_product:
                        quote_product.status = False
                        logger.info(f"AP product deactivated - quote_product_id: {quote_product_id}")
                
                await session.commit()
                
                if not quote_response.plans:
                    logger.warning("No AP plans found in response")
                    raise ValidationError("No se han encontrado opciones de plan para AP")
                
                return {
                    "product_code": product.code,
                    "product_name": product.name,
                    "mandatory": product.mandatory,
                    "total_plans": len(quote_response.plans),
                    "plans": [plan.to_dict() for plan in quote_response.plans if plan.availability == True],
                    "success": True,
                    "vehicle_class_code": class_code
                }
                
            except Exception as e:
                logger.error(f"Unexpected error fetching AP options: {str(e)}", exc_info=True)
                raise
    
    async def _fetch_rce_quote(
        self,
        insurance_session: InsuranceSession,
        client: Client,
        vehicle: Vehicle,
        homologation: VehicleHomologation,
        product: Product
    ) -> Dict[str, Any]:
        """
        Fetch RC (Responsabilidad Civil) quote from external provider.
        
        Args:
            session: Database session
            insurance_session: InsuranceSession with loaded client and vehicle
            homologation: Selected VehicleHomologation
            product: Product instance (RC)
        Returns:
            Dictionary with quote result
        """
        async with db_manager.get_async_session("dbw", self.sponsor) as session:
            rce_client = RCEClient(self.sponsor)
            
            logger.info(
                f"Fetching RCE plan options - Session: {insurance_session.slug}"
            )
            
            try:
                quote_response, log_id = await rce_client.get_plan_options(vehicle.license_plate)
                
                # Get or create QuoteProduct
                quote_product_id = await self._get_quote_product(
                    log_id, insurance_session.id, product
                )
                
                stmt = select(QuoteProductOption).where(
                    QuoteProductOption.quote_product_id == quote_product_id,
                )
                result = await session.execute(stmt)
                existing_options = result.scalars().all()
                
                # Update existing options or create new ones
                existing_plan_names = {opt.plan_name: opt for opt in existing_options}
                
                quote_response = RCEQuoteResponse(quote_response)
                
                # Store each plan as a QuoteProductOption
                for plan in quote_response.plans:
                    option = existing_plan_names.get(plan.description)
                    if option:
                        # Update existing option
                        option.price = plan.coverages[0].total_premium if len(plan.coverages) > 0 else None
                        option.coverage = plan.to_dict()
                        option.status = True
                    else:
                        # Create new option
                        option = QuoteProductOption(
                            quote_product_id=quote_product_id,
                            plan_name=plan.description,
                            price=plan.coverages[0].total_premium if len(plan.coverages) > 0 else None,
                            coverage=plan.to_dict()
                        )
                        session.add(option)
                        await session.flush()
                    plan.option_id = option.id

                # Deactivate existing options not in the new plans
                existing_plan_names = {plan.description for plan in quote_response.plans}
                for existing_option in existing_options:
                    if existing_option.plan_name not in existing_plan_names:
                        existing_option.status = False

                await session.flush()
                
                logger.info(
                    f"RCE plan options stored successfully - "
                    f"Total plans: {len(quote_response.plans)}"
                )
                await session.commit()
                
                if not quote_response.plans:
                    logger.warning("No RCE plans found in response")
                    raise ValidationError("No se encontraron planes RCE disponibles")
                
                return {
                    "product_code": product.code,
                    "product_name": product.name,
                    "mandatory": product.mandatory,
                    "total_plans": len(quote_response.plans),
                    "plans": [plan.to_dict() for plan in quote_response.plans],
                    "success": True,
                }
                
            except Exception as e:
                logger.error(f"Unexpected error fetching RCE options: {str(e)}", exc_info=True)
                raise

    async def _get_quote_product(
        self,
        log_id: Dict[str, Any],
        insurance_session_id: int,
        product: Product
    ) -> Optional[QuoteProduct]:
        async with db_manager.get_async_session("dbw", self.sponsor) as session:
            stmt = (
                select(QuoteProduct)
                .where(
                    and_(
                        QuoteProduct.session_id == insurance_session_id,
                        QuoteProduct.product_id == product.id,
                    )
                )
            )
            result = await session.execute(stmt)
            quote_product = result.scalars().first()
            
            if not quote_product:
                logger.error(f"QuoteProduct not found for AP - this shouldn't happen")
                raise ValidationError(f"Cotización para {product.name} no encontrada")
            logger.info(f"************************** LOG ID: {log_id} **************************")
            logger.info(f"QuoteProduct found - ID: {quote_product.id}, Product: {product.code}")
            quote_product_id = quote_product.id
            # update quote products with log_id
            if log_id:
                if log_id.get('mysql_id'):
                    quote_product.external_service_log_id = log_id['mysql_id']
                    # TODO set dynamo_id
                    await session.commit()
                    logger.info(
                        f"Updated QuoteProduct with ExternalServiceLog ID: {log_id['mysql_id']}"
                    )
            return quote_product_id
    
    async def _create_or_update_selection(
        self,
        session: AsyncSession,
        session_id: int,
        vehicle_class_id: int
    ) -> VehicleHomologationSelection:
        """
        Create or update vehicle homologation selection.
        
        If a selection already exists for this session, update it.
        Otherwise, create a new one.
        
        Args:
            session: Database session
            session_id: Insurance session ID
            vehicle_class_id: Vehicle homologation ID
            
        Returns:
            VehicleHomologationSelection instance
        """
        # Check if selection already exists
        stmt = select(VehicleHomologationSelection).where(
            VehicleHomologationSelection.session_id == session_id
        )
        result = await session.execute(stmt)
        selection = result.scalars().first()
        
        if selection:
            # Update existing selection
            old_class_id = selection.vehicle_class_id
            selection.vehicle_class_id = vehicle_class_id
            
            logger.info(
                f"Selection updated - Session ID: {session_id}, "
                f"Old Homologation ID: {old_class_id}, "
                f"New Homologation ID: {vehicle_class_id}"
            )
        else:
            # Create new selection
            selection = VehicleHomologationSelection(
                session_id=session_id,
                vehicle_class_id=vehicle_class_id
            )
            session.add(selection)
            
            logger.info(
                f"Selection created - Session ID: {session_id}, "
                f"Homologation ID: {vehicle_class_id}"
            )
        
        await session.flush()
        return selection
    
    async def get_selected_homologation(
        self,
        session_slug: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the selected homologation for a session along with selected product quotes.
        
        Args:
            session_slug: Insurance session UUID slug
            
        Returns:
            Dictionary with selection details and selected products or None if not found
        """
        async with db_manager.get_async_session("dbr", self.sponsor) as session:
            # Get session
            stmt_session = select(InsuranceSession).where(
                InsuranceSession.slug == session_slug
            )
            result_session = await session.execute(stmt_session)
            insurance_session = result_session.scalars().first()
            
            if not insurance_session:
                return None
            
            # Get selection
            stmt = (
                select(VehicleHomologationSelection, VehicleHomologation)
                .join(
                    VehicleHomologation,
                    VehicleHomologationSelection.vehicle_class_id == VehicleHomologation.id
                )
                .where(VehicleHomologationSelection.session_id == insurance_session.id)
            )
            result = await session.execute(stmt)
            row = result.first()
            
            if not row:
                return None
            
            selection, homologation = row
            
            # Get selected products with their options
            selected_products = []
            stmt_products = (
                select(QuoteProduct)
                .options(
                    selectinload(QuoteProduct.product),
                    selectinload(QuoteProduct.selection).selectinload(QuoteProductSelection.option)
                )
                .where(
                    and_(
                        QuoteProduct.session_id == insurance_session.id,
                        QuoteProduct.status == True
                    )
                )
            )
            result_products = await session.execute(stmt_products)
            quote_products = result_products.scalars().all()
            
            # Build selected products list
            for quote_product in quote_products:
                if quote_product.selection and quote_product.selection.option:
                    selected_option = quote_product.selection.option
                    
                    # Build selected plan data similar to get_quote_options structure
                    selected_plan = {
                        "option_id": selected_option.id,
                        "plan_name": selected_option.plan_name,
                        "price": float(selected_option.price) if selected_option.price else None,
                        "coverages": selected_option.coverage  # JSON field
                    }
                    
                    # For RCE, extract additional fields from coverage
                    if quote_product.product.code == "RCE" and selected_option.coverage:
                        rce_data = dict(selected_option.coverage)
                        rce_data.pop('option_id', None)
                        selected_plan.update(rce_data)
                    
                    selected_products.append({
                        "product_code": quote_product.product.code,
                        "product_name": quote_product.product.name,
                        "selected_plan": selected_plan
                    })
            
            logger.info(
                f"Retrieved selected homologation with {len(selected_products)} selected products "
                f"for session {session_slug}"
            )

            return {
                "session_slug": insurance_session.slug,
                "selection_id": selection.id,
                "id": homologation.id,
                "class_code": homologation.class_code,
                "class_description": homologation.class_description,
                "transport_type_code": homologation.transport_type_code,
                "brand_code": homologation.brand_code,
                "line_code": homologation.line_code,
                "destination_code": homologation.destination_code,
                "selected_at": selection.created_at.isoformat(),
                "selected_products": selected_products
            }

    async def _create_or_update_product_selection(
        self,
        session: AsyncSession,
        session_id: int,
        products: List[Product]
    ):
        """
        Create or update product selection for a Quote.
        
        Args:
            session: Database session
            session_id: Insurance session ID
            products: List of products to associate with the selection
        """
        product_codes = [p.code for p in products]
        # Check if selection already exists
        stmt = (
            select(QuoteProduct)
            .options(selectinload(QuoteProduct.product))
            .where(QuoteProduct.session_id == session_id)
        )
        result = await session.execute(stmt)
        existing_products = result.scalars().all()
        if existing_products:
            # Update existing products
            existing_codes = {p.product.code for p in existing_products}
            for product in products:
                if product.code not in existing_codes:
                    # Add new product
                    new_product = QuoteProduct(
                        session_id=session_id,
                        product_id=product.id
                    )
                    session.add(new_product)
                else:
                    # Update existing product status
                    existing_product = next(p for p in existing_products if p.product.code == product.code)
                    existing_product = next((p for p in existing_products if p.product.code == product.code), None)
                    if existing_product:
                        existing_product.status = True
            for existing_product in existing_products:
                if existing_product.product.code not in product_codes:
                    existing_product.status = False
            logger.info(
                f"Product selection updated - Session ID: {session_id}, "
                f"Products: {product_codes}"
            )
        else:
            # Create new product selections
            for product in products:
                new_product = QuoteProduct(
                    session_id=session_id,
                    product_id=product.id
                )
                session.add(new_product)
            logger.info(
                f"Product selection created - Session ID: {session_id}, "
                f"Products: {product_codes}"
            )
        await session.flush()
        
        # stmt = select(QuoteProduct).where(
        #     QuoteProduct.session_id == session_id,
        #     QuoteProduct.status == True
        # )
        # result = await session.execute(stmt)
        # return result.scalars().all()

    async def get_quote_options(self, session_slug: str) -> Dict[str, Any]:
        """
        Get all available quote options for a session.
        
        Retrieves all products and their available plan options from quote_product_options,
        including the coverage details stored in JSON format.
        
        Args:
            session_slug: Insurance session slug
            
        Returns:
            Dictionary with session_slug and list of products with their plans
            
        Raises:
            ValidationError: If session not found
        """
        async with db_manager.get_async_session("dbr", self.sponsor) as session:
            # Get session
            stmt = select(InsuranceSession).where(InsuranceSession.slug == session_slug)
            result = await session.execute(stmt)
            insurance_session = result.scalars().first()
            
            if not insurance_session:
                logger.warning(f"Session not found: {session_slug}")
                raise ValidationError("Sesión no encontrada")
            
            # Get all quote products with their options
            stmt = (
                select(QuoteProduct)
                .options(
                    selectinload(QuoteProduct.product),
                    selectinload(QuoteProduct.options)
                )
                .where(
                    and_(
                        QuoteProduct.session_id == insurance_session.id,
                        QuoteProduct.status == True
                    )
                )
            )
            result = await session.execute(stmt)
            quote_products = result.scalars().all()
            
            # Build response structure
            products_data = []
            for quote_product in quote_products:
                # Get active AND available options for this product
                active_available_options = [
                    opt for opt in quote_product.options 
                    if opt.status and opt.availability_status == OptionAvailabilityStatus.AVAILABLE
                ]
                
                if not active_available_options:
                    logger.warning(
                        f"No active and available options found for product {quote_product.product.code}"
                    )
                    continue
                
                # Build plans array from options
                plans = []
                rce_data = {}
                for option in active_available_options:
                    if quote_product.product.code == "RCE":
                        if option.coverage:
                            rce_data = option.coverage
                    plan_data = {
                        "option_id": option.id,
                        "plan_name": option.plan_name,
                        "price": float(option.price) if option.price else None,
                        "coverages": option.coverage  # JSON field
                    }
                    if rce_data:
                        rce_data.pop('option_id', None)
                        plan_data.update(rce_data)
                        rce_data = {}
                    plans.append(plan_data)
                
                product_data = {
                    "product_code": quote_product.product.code,
                    "product_name": quote_product.product.name,
                    "plans": plans
                }
                products_data.append(product_data)
            
            logger.info(
                f"Retrieved quote options - Session: {session_slug}, "
                f"Products: {len(products_data)}"
            )
            
            return {
                "session_slug": session_slug,
                "products": products_data
            }

    async def select_plan(
        self,
        session_slug: str,
        selections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Select specific plan options for multiple products in a session.
        
        Validates that each option exists and belongs to the correct product,
        then creates or updates the selections in quote_product_selection table.
        
        Args:
            session_slug: Insurance session slug
            selections: List of dicts with product_code and option_id
            
        Returns:
            Dictionary with confirmation and all selected plan details
            
        Raises:
            ValidationError: If session, product, or option not found or invalid
        """
        async with db_manager.get_async_session("dbw", self.sponsor) as session:
            # Get session
            stmt = select(InsuranceSession).where(InsuranceSession.slug == session_slug)
            result = await session.execute(stmt)
            insurance_session = result.scalars().first()
            
            if not insurance_session:
                logger.warning(f"Session not found: {session_slug}")
                raise ValidationError("Sesión no encontrada")
            
            selected_plans = []
            
            # Process each selection
            for selection_data in selections:
                product_code = selection_data['product_code']
                option_id = selection_data['option_id']
                
                # Get product
                stmt = select(Product).where(Product.code == product_code)
                result = await session.execute(stmt)
                product = result.scalars().first()
                
                if not product:
                    logger.warning(f"Product not found: {product_code}")
                    raise ValidationError(f"Producto {product_code} no encontrado")
                
                # Get quote product for this session and product
                stmt = (
                    select(QuoteProduct)
                    .options(selectinload(QuoteProduct.options))
                    .where(
                        and_(
                            QuoteProduct.session_id == insurance_session.id,
                            QuoteProduct.product_id == product.id,
                            QuoteProduct.status == True
                        )
                    )
                )
                result = await session.execute(stmt)
                quote_product = result.scalars().first()
                
                if not quote_product:
                    logger.warning(
                        f"Quote product not found - Session: {session_slug}, "
                        f"Product: {product_code}"
                    )
                    raise ValidationError(
                        f"No se encontró cotización para el producto {product_code}"
                    )
                
                # Validate that option exists and belongs to this quote product
                selected_option = None
                for option in quote_product.options:
                    if option.id == option_id:
                        selected_option = option
                        break
                
                if not selected_option:
                    logger.warning(
                        f"Invalid option_id {option_id} for quote_product {quote_product.id}"
                    )
                    raise ValidationError(
                        f"La opción seleccionada no es válida para el producto {product_code}"
                    )
                
                if not selected_option.status:
                    logger.warning(f"Option {option_id} is not active")
                    raise ValidationError(
                        f"La opción seleccionada no está disponible para el producto {product_code}"
                    )
                
                # Create or update selection (upsert pattern due to unique constraint)
                stmt = (
                    select(QuoteProductSelection)
                    .where(QuoteProductSelection.quote_product_id == quote_product.id)
                )
                result = await session.execute(stmt)
                existing_selection = result.scalars().first()
                
                if existing_selection:
                    # Update existing selection
                    existing_selection.option_id = option_id
                    logger.info(
                        f"Updated plan selection - Session: {session_slug}, "
                        f"Product: {product_code}, Option: {option_id}"
                    )
                else:
                    # Create new selection
                    new_selection = QuoteProductSelection(
                        quote_product_id=quote_product.id,
                        option_id=option_id
                    )
                    session.add(new_selection)
                    logger.info(
                        f"Created plan selection - Session: {session_slug}, "
                        f"Product: {product_code}, Option: {option_id}"
                    )
                
                # Add to response
                selected_plans.append({
                    "product_code": product_code,
                    "product_name": product.name,
                    "selected_option": {
                        "option_id": selected_option.id,
                        "plan_name": selected_option.plan_name,
                        "price": float(selected_option.price) if selected_option.price else None,
                        "coverage": selected_option.coverage
                    }
                })
            
            # Update session status to SELECTING then SELECTED
            insurance_session.status = SessionStatus.SELECTING
            await session.flush()
            
            insurance_session.status = SessionStatus.SELECTED
            
            # Commit all changes
            await session.commit()
            
            logger.info(
                f"Plan selections completed - Session: {session_slug}, "
                f"Status: {SessionStatus.SELECTED.value}, "
                f"Total selections: {len(selected_plans)}"
            )
            
            return {
                "session_slug": session_slug,
                "message": "Planes seleccionados exitosamente",
                "selected_plans": selected_plans,
                "total_selected": len(selected_plans)
            }

    async def pre_expedite_policies(self, session_slug: str) -> Dict[str, Any]:
        """
        Pre-expedite policies for a session (quote mode issuance).
        
        This validates that policies can be issued before sending user to payment gateway.
        Processes SOAT and AP (if selected) in a single request to Mundial Seguros.
        
        Args:
            session_slug: Insurance session slug
            
        Returns:
            Dictionary with pre-expedition results for each product
            
        Raises:
            ValidationError: If session not found, no selections, or validation fails
        """
        async with db_manager.get_async_session("dbw", self.sponsor) as session:  # Changed to dbw for write access
            # Get session with all relationships
            stmt = (
                select(InsuranceSession)
                .options(
                    selectinload(InsuranceSession.client).options(
                        selectinload(Client.document_type),
                        selectinload(Client.city),
                        selectinload(Client.gender)
                    ),
                    selectinload(InsuranceSession.vehicle),
                    selectinload(InsuranceSession.quote_products).selectinload(QuoteProduct.product),
                    selectinload(InsuranceSession.quote_products).selectinload(QuoteProduct.selection).selectinload(QuoteProductSelection.option)
                )
                .where(InsuranceSession.slug == session_slug)
            )
            result = await session.execute(stmt)
            insurance_session = result.scalars().first()
            
            if not insurance_session:
                logger.warning(f"Session not found: {session_slug}")
                raise ValidationError("Sesión no encontrada")
            
            # Validate session has owner validated
            if not insurance_session.is_owner:
                raise ValidationError("Debe validar propiedad del vehículo antes de pre-expedir")
            
            # Get products with selections
            selected_products = []
            for quote_product in insurance_session.quote_products:
                if quote_product.selection and quote_product.status:
                    selected_products.append(quote_product)
            
            if not selected_products:
                raise ValidationError("No hay productos seleccionados para pre-expedición")
            
            vehicle_class_selection = await self.get_selected_homologation(session_slug)
            if not vehicle_class_selection:
                raise ValidationError("No hay una clase de vehículo seleccionada")
            
            # Check if SOAT is selected (required)
            soat_product = None
            ap_product = None
            rce_product = None
            
            for qp in selected_products:
                if qp.product.code == 'SOAT':
                    soat_product = qp
                elif qp.product.code == 'AP':
                    ap_product = qp
                elif qp.product.code == 'RCE':
                    rce_product = qp
            
            if not soat_product:
                raise ValidationError("SOAT es obligatorio para pre-expedición")
            
            # Reserve a SOAT form
            forms_manager = SoatFormsManager(self.sponsor)
            
            # Check if session already has a form reserved
            existing_form = await forms_manager.get_form_for_session(insurance_session.id)
            
            if existing_form and existing_form.status == FormStatus.RESERVED:
                # Use existing reservation
                soat_form = existing_form
                logger.info(f"Using existing form reservation: {soat_form.form_number}")
            else:
                # Reserve a new form
                soat_form = await forms_manager.reserve_form_for_session(
                    session_id=insurance_session.id,
                )
                logger.info(f"Reserved new form: {soat_form.form_number}")
            
            # Build session data for expedition
            session_data = await self._build_expedition_data(
                insurance_session,
                vehicle_class_selection,
                soat_product,
                ap_product,
                rce_product,
                soat_form.form_number
            )
            
            # Update session to ISSUING status
            insurance_session.status = SessionStatus.ISSUING
            await session.commit()
            
            # Call expedition service
            expedition_client = ExpeditionClient(self.sponsor)
            
            try:
                # Execute SOAT/AP and RCE in parallel if RCE is present
                if rce_product:
                    expedition_rce_client = ExpeditionRCEClient(self.sponsor)
                    # Parallel execution: SOAT/AP + RCE
                    logger.info("Executing SOAT/AP and RCE pre-expedition in parallel")
                    
                    soat_task = expedition_client.pre_expedite_policy(session_data)
                    rce_task = expedition_rce_client.pre_expedite_rce_policy(session_data)
                    
                    # Wait for both to complete
                    soat_response, rce_response = await asyncio.gather(
                        soat_task, 
                        rce_task, 
                        return_exceptions=True
                    )
                    
                    results = []
                    all_success = True
                    
                    # Process SOAT response
                    if isinstance(soat_response, Exception):
                        logger.error(f"SOAT pre-expedition failed: {str(soat_response)}")
                        all_success = False
                        results.append({
                            "product_code": "SOAT",
                            "success": False,
                            "message": f"Error en pre-expedición SOAT: {str(soat_response)}",
                            "details": {}
                        })
                    else:
                        all_success = all_success and soat_response.success
                        results.append({
                            "product_code": "SOAT",
                            "success": soat_response.success,
                            "message": soat_response.message,
                            "details": soat_response.details
                        })
                    
                    # If AP was included in SOAT request
                    if ap_product:
                        if isinstance(soat_response, Exception):
                            results.append({
                                "product_code": "AP",
                                "success": False,
                                "message": "AP no procesado debido a error en SOAT",
                                "details": {}
                            })
                        else:
                            results.append({
                                "product_code": "AP",
                                "success": soat_response.success,
                                "message": soat_response.message,
                                "details": soat_response.details
                            })
                    
                    # Process RCE response
                    if isinstance(rce_response, Exception):
                        logger.error(f"RCE pre-expedition failed: {str(rce_response)}")
                        all_success = False
                        results.append({
                            "product_code": "RCE",
                            "success": False,
                            "message": f"Error en pre-expedición RCE: {str(rce_response)}",
                            "details": {}
                        })
                    else:
                        all_success = all_success and rce_response.success
                        results.append({
                            "product_code": "RCE",
                            "success": rce_response.success,
                            "message": rce_response.message,
                            "details": rce_response.details
                        })
                    
                else:
                    # Only SOAT/AP (no RCE) - sequential execution
                    logger.info("Executing SOAT/AP pre-expedition (no RCE)")
                    
                    response = await expedition_client.pre_expedite_policy(session_data)
                    
                    results = []
                    all_success = response.success
                    
                    # SOAT result
                    results.append({
                        "product_code": "SOAT",
                        "success": response.success,
                        "message": response.message,
                        "details": response.details
                    })
                    
                    # If AP was included
                    if ap_product:
                        results.append({
                            "product_code": "AP",
                            "success": response.success,
                            "message": response.message,
                            "details": response.details
                        })
                
                # Update session status to ISSUED if all pre-expeditions succeeded
                if all_success:
                    insurance_session.status = SessionStatus.ISSUED
                    await session.commit()
                    logger.info(f"Session status updated to ISSUED - Session: {session_slug}")
                else:
                    # Mark as issue failed if any failed
                    insurance_session.status = SessionStatus.ISSUE_FAILED
                    await session.commit()
                    logger.warning(f"Session status updated to ISSUE_FAILED - Session: {session_slug}")
                
                logger.info(
                    f"Pre-expedition completed - Session: {session_slug}, "
                    f"Success: {all_success}, Status: {insurance_session.status.value}, "
                    f"Products: {len(results)}"
                )
                
                return {
                    "session_slug": session_slug,
                    "message": "Pre-expedición completada" if all_success else "Pre-expedición con errores",
                    "results": results,
                    "total_processed": len(results),
                    "all_success": all_success
                }
                
            except Exception as e:
                logger.error(f"Error in pre-expedition: {str(e)}", exc_info=True)
                traceback.print_exc()
                raise ValidationError(f"Ocurrió un error en pre-expedición") from e
    
    async def _build_expedition_data(
        self,
        insurance_session: InsuranceSession,
        vehicle_class_selection: Dict[str, Any],
        soat_product: QuoteProduct,
        ap_product: Optional[QuoteProduct] = None,
        rce_product: Optional[QuoteProduct] = None,
        form_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build data structure for expedition request.
        
        Args:
            insurance_session: Insurance session with client and vehicle loaded
            vehicle_class_selection: Selected vehicle homologation
            soat_product: SOAT quote product with selection
            ap_product: Optional AP quote product with selection
            form_number: SOAT form number (if not provided, generates random)
            
        Returns:
            Dictionary with all data needed for expedition
        """
        try:
            client = insurance_session.client
            vehicle = insurance_session.vehicle
            client_city = client.city
            
            # Get selected SOAT option
            soat_option = soat_product.selection.option
            soat_coverage = soat_option.coverage
            
            # Calculate dates
            today = datetime.now()
            fec_emision = soat_coverage.get('issue_date') # or today.strftime('%d/%m/%Y')
            # Vigencia starts from emission date
            fec_vig_desde = soat_coverage.get('start_date')
            fec_vig_hasta = soat_coverage.get('end_date')
            
            # Client data
            client_data = {
                'id': client.id,
                "txt_apellido1": client.last_name or "",
                "txt_apellido2": client.second_last_name or "",
                "txt_nombre": client.first_name or "",
                "cod_tipo_persona": "J" if client.document_type.code == "NIT" else "F",
                "cod_tipo_doc": client.document_type.soat_id,
                "nro_doc": client.document_number,
                "cod_tipo_dir": "1",
                "txt_direccion": client.address,
                "cod_dpto": client_city.code_department if client_city else "",
                "cod_municipio": f"{client_city.code_department}{client_city.code}" if client_city else "",
                "cod_tipo_telef": "8",
                "txt_telefono": client.phone or "",
                "txt_correo": client.email or "",
                "txt_sexo": client.gender.code
            }
            
            # Vehicle data
            vehicle_data = {
                "cod_marca_min_trans": vehicle_class_selection['brand_code'],
                "cod_modelo_min_trans": vehicle_class_selection['line_code'],
                "cod_tipo_veh_min_trans": vehicle_class_selection['transport_type_code'],
                "aaaa_modelo": str(vehicle.model_year),
                "txt_patente": vehicle.license_plate,
                "txt_motor": vehicle.engine_number,
                "txt_chasis": vehicle.chassis_number,
                "cod_destino": vehicle_class_selection['destination_code'],
                "cnt_toneladas": str(vehicle.tonnage or 0.00),
                "cnt_ocupantes": vehicle.seats,
                "cnt_cc": vehicle.engine_cc,
                "cod_pais_matricula": "1",
                "cod_clase_soat": vehicle_class_selection['class_code'],
                "txt_marca": vehicle.brand,
                "txt_modelo": vehicle.line,
                "txt_vin": vehicle.vin_number or "NA"
            }
            
            # SOAT data
            soat_data = {
                "fec_emision": fec_emision,
                "fec_vig_desde": fec_vig_desde,
                "fec_vig_hasta": fec_vig_hasta,
                "rate": int(soat_coverage.get('rate')),
                "imp_prima_total": int(soat_coverage.get('policy_total_value')),
                "imp_gtos_emi": 0,
                "imp_iva": 0,
                "nro_formulario": form_number,
                "cod_motivo": "",
                "imp_pagado": int(soat_coverage.get('policy_total_value') + soat_coverage.get('runt_fee')),
                "fec_mov": fec_emision,
                "cod_tipo_agente": self.config['intermediary_code_id'],
                "imp_tasa_runt": int(soat_coverage.get('runt_fee'))
            }
            
            config = {
                "pos_code": self.config['pos_code'],
                "branch_code": self.config['branch_code'],
                "agent_code": self.config['intermediary_code'],
                "user_code": self.config['user_code'],
            }
            
            result = {
                "client": client_data,
                "vehicle": vehicle_data,
                "soat": soat_data,
                "config": config
            }
            
            # Add AP data if present
            if ap_product:
                ap_option = ap_product.selection.option
                ap_coverage = ap_option.coverage
                
                # Get AP specific data from coverage
                prices = ap_coverage.get('prices', {})
                tipo_poliza = ap_coverage.get('code_type', '3')
                valor_asegurado = int(prices.get('insured_value'))
                valor_poliza = int(prices.get('policy_value'))

                ap_data = {
                    "ap_tipo_poliza": tipo_poliza,
                    "ap_tomador": "0",
                    "ap_txt_apellido1": client_data['txt_apellido1'],
                    "ap_txt_apellido2": client_data['txt_apellido2'],
                    "ap_txt_nombre": client_data['txt_nombre'],
                    "ap_cod_tipo_persona": client_data['cod_tipo_persona'],
                    "ap_cod_tipo_doc": client_data['cod_tipo_doc'],
                    "ap_nro_doc": client_data['nro_doc'],
                    "ap_cod_tipo_dir": client_data['cod_tipo_dir'],
                    "ap_txt_direccion": client_data['txt_direccion'],
                    "ap_cod_dpto": client_data['cod_dpto'],
                    "ap_cod_municipio": client_data['cod_municipio'],
                    "ap_pais": "1",
                    "ap_txt_sexo": client_data['txt_sexo'],
                    "ap_cod_tipo_telef": "8",
                    "ap_txt_telefono": client.phone or "",
                    "fec_naci": "01/01/1990",  # TODO: Get from client
                    "ap_fec_emision": fec_emision,
                    "ap_fec_vig_desde": fec_vig_desde,
                    "ap_fec_vig_hasta": fec_vig_hasta,
                    "ap_valor_asegurado": valor_asegurado,
                    "ap_valor_poliza": valor_poliza,
                    "ap_placa_asistencia": vehicle.license_plate,
                    "ap_vigencia": today.strftime('%Y')
                }
                
                result["ap"] = ap_data
            
            if rce_product:
                rce_option = rce_product.selection.option
                rce_coverage = rce_option.coverage
                
                coverages = rce_coverage.get('coverages') if rce_coverage else {}
                rce_cov_cal = {
                    'premium_sum': 0,
                    'vat_sum': 0,
                    'coverages': []
                }
                for coverage in coverages:
                    print(f'*** RCE Coverage {coverage["coverage_id"]} ***')
                    print(f'*** premium_sum {rce_cov_cal["premium_sum"]} ***')
                    print(f'*** rce_cov_cal {rce_cov_cal["vat_sum"]} ***')
                    print(f'*** coverage[premium] {coverage["premium"]} ***')
                    print(f'*** coverage[vat] {coverage["vat"]} ***')
                    
                    rce_cov_cal['premium_sum'] += coverage['premium'] if coverage['premium'] else 0
                    rce_cov_cal['vat_sum'] += coverage['vat'] if coverage['vat'] else 0
                    rce_cov_cal['coverages'].append({
                        'idCobertura': coverage['coverage_id'],
                        'tipocobertura': coverage['type']
                    })
                
                # Get RCE specific data from coverage
                rce_suma_asegurada = rce_coverage.get('insured_sum', 10000000)
                rce_valor_poliza = int(rce_option.price)
                
                date_issued = change_format_date(fec_emision, '%d/%m/%Y', '%Y-%m-%d')
                
                rce_data = {
                    "nombre_sucursal": self.config['branch_name'],
                    "cod_sucursal": self.config['branch_code'],
                    "fecha_emision": date_issued,
                    "cod_usuario": self.config['user_code'],
                    "cod_agente": self.config['intermediary_code'],
                    "cod_tipo_agente": self.config['intermediary_code_id'],
                    "pto_vta": self.config['pos_code'],
                    "Sn_cotizacion": False,
                    "polizaRc": {
                        "nro_solicitud": 0,
                        "fec_expedicion": date_issued,
                        "fecha_vig_desde": change_format_date(fec_vig_desde, '%d/%m/%Y', '%Y-%m-%d'),
                        "fecha_vig_hasta": change_format_date(fec_vig_hasta, '%d/%m/%Y', '%Y-%m-%d'),
                        "placa": vehicle.license_plate,
                        "cod_clase_vehiculo": vehicle_class_selection['class_code'],
                        "id_regla_rce": '',
                        "imp_prima": rce_cov_cal['premium_sum'],
                        "Pje_iva": '', # VALIDAR
                        "Imp_iva": rce_cov_cal['vat_sum'],
                        "Imp_total": rce_cov_cal["premium_sum"] + rce_cov_cal["vat_sum"],
                        "cod_fasecolda": "", # VALIDAR
                        "cod_tipo_endo": 8, # VALIDAR
                        "cod_grupo_endo": 1, # VALIDAR
                        "cod_modelo": vehicle.model_year,
                        "cod_usuario": self.config['user_code'],
                        "cod_suc": self.config['branch_code'],
                        "cod_pto_vta": self.config['pos_code'],
                        "cod_tipo_agente": self.config['intermediary_code_id'],
                        "cod_agente": self.config['intermediary_code'],
                        "cod_tipo_agente_asociado": None, # VALIDAR
                        "cod_agente_asociado": None, # VALIDAR
                        "cod_grupo": rce_coverage['group_code'],
                        "cod_subgrupo": rce_coverage['sub_group_code'],
                        "cod_servicio_sm": rce_coverage['service_sm_code'],
                        "id_plan": rce_coverage['plan_id'],
                        "plan_seleccionado": {
                            "id": rce_coverage['plan_id'],
                            "coberturas": rce_cov_cal['coverages']
                        },
                        "info_tomador": {
                            "Cod_tipo_doc": client_data["cod_tipo_doc"],
                            "nro_doc": client_data["nro_doc"],
                            "txt_nombre": client_data["txt_nombre"],
                            "txt_Apellido1": client_data["txt_apellido1"],
                            "txt_sexo": client_data["txt_sexo"],
                            "email": client_data["txt_correo"],
                            "celular": client_data["txt_telefono"],
                            "cod_dpto": client_data["cod_dpto"],
                            "cod_municipio": client_data["cod_municipio"],
                            "txt_direccion": client_data["txt_direccion"],
                            "cod_tipo_persona": client_data["cod_tipo_persona"],
                            "cod_tipo_empresa": 1
                        }
                    }
                }
                
                result["rce"] = rce_data

            return result
        except Exception as e:
            logger.error("Error building expedition data: %s", str(e), exc_info=True)
            raise ValidationError("Ocurrió un error al validar los servicios de pre-expedición.") from e
    
    async def _check_ap_plan_availability(
        self,
        session: AsyncSession,
        plan: Any,
        vehicle_class: Optional[VehicleClass]
    ) -> OptionAvailabilityStatus:
        """
        Check if an AP plan is available for the selected vehicle class.
        
        Args:
            session: Database session
            plan: APPlanOption instance from API response
            vehicle_class: VehicleClass instance for the selected vehicle
            
        Returns:
            OptionAvailabilityStatus indicating availability
        """
        # If no vehicle class is found in our database, consider all plans available
        # This maintains backward compatibility
        if not vehicle_class:
            logger.warning("No vehicle class found - allowing all AP plans by default")
            return OptionAvailabilityStatus.AVAILABLE
        
        # Get the plan code from the API response
        plan_code = plan.code_type  # e.g., "3", "5", "14"
        
        # Check if this plan exists in plans_ap table
        stmt_plan = select(PlanAP).where(
            PlanAP.code == plan_code,
            PlanAP.status == True
        )
        result_plan = await session.execute(stmt_plan)
        plan_ap = result_plan.scalars().first()
        
        # If plan not configured in our database, allow it by default
        if not plan_ap:
            logger.info(
                f"AP plan {plan_code} ({plan.desc_type}) not found in plans_ap table - "
                f"allowing by default"
            )
            return OptionAvailabilityStatus.AVAILABLE
        
        # Check if there's an association between this plan and the vehicle class
        stmt_association = select(PlanVehicleClass).where(
            PlanVehicleClass.plan_id == plan_ap.id,
            PlanVehicleClass.vehicle_class_id == vehicle_class.id,
            PlanVehicleClass.status == True
        )
        result_association = await session.execute(stmt_association)
        association = result_association.scalars().first()
        
        if association:
            logger.info(
                f"AP plan {plan_code} ({plan.desc_type}) is AVAILABLE for "
                f"vehicle class {vehicle_class.code}"
            )
            return OptionAvailabilityStatus.AVAILABLE
        else:
            logger.info(
                f"AP plan {plan_code} ({plan.desc_type}) is UNAVAILABLE for "
                f"vehicle class {vehicle_class.code}"
            )
            return OptionAvailabilityStatus.UNAVAILABLE_CLASS
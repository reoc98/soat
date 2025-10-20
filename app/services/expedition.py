"""
Expedition Service

This service handles the complete expedition flow for insurance policies:
- Plan selection validation
- Pre-expedition (quote mode with cotizador=true)
- Final expedition (actual issuance with cotizador=false)

Supports parallel execution of SOAT/AP and RCE products.
"""

import logging
import asyncio
from typing import Dict, Any, List
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.models.insurance_session import InsuranceSession, SessionStatus
from app.models.product import Product
from app.models.quote_product import QuoteProduct
from app.models.quote_product_option import QuoteProductOption
from app.models.quote_product_selection import QuoteProductSelection
from app.models.soat_form import FormStatus
from app.models.client import Client
from app.models.vehicle import Vehicle
from app.models.city import City
from app.models.gender import Gender
from app.database.session import db_manager
from app.core.exceptions import ValidationError
from app.services.external.expedition_client import ExpeditionClient, ExpeditionRCEClient
from app.services.soat_forms_manager import SoatFormsManager

logger = logging.getLogger(__name__)


class ExpeditionService:
    """Service for handling insurance policy expedition."""
    
    def __init__(self, sponsor: str):
        """
        Initialize the expedition service.
        
        Args:
            sponsor: Sponsor identifier
        """
        self.sponsor = sponsor
    
    async def update_client_info(
        self,
        session_slug: str,
        client_data: Dict[str, Any]
    ) -> None:
        """
        Update client information for a session.
        
        Updates the client record with address, phone, email, city_id, gender_id, and birth_date (if provided).
        This method is called before pre-expedition to ensure client data is complete.
        
        Args:
            session_slug: Insurance session slug
            client_data: Dictionary with client information (address, phone, email, city_id, gender_id, birth_date)
            
        Raises:
            ValidationError: If session, client, city, or gender not found
        """
        from datetime import datetime
        
        async with db_manager.get_async_session("dbw", self.sponsor) as session:
            # Get session with client relationship
            stmt = (
                select(InsuranceSession)
                .options(selectinload(InsuranceSession.client))
                .where(InsuranceSession.slug == session_slug)
            )
            result = await session.execute(stmt)
            insurance_session = result.scalars().first()
            
            if not insurance_session:
                logger.warning(f"Session not found: {session_slug}")
                raise ValidationError("Sesión no encontrada")
            
            if not insurance_session.client:
                logger.warning(f"Client not found for session: {session_slug}")
                raise ValidationError("Cliente no encontrado en la sesión")
            
            client = insurance_session.client
            
            # Validate city_id if provided
            if client_data.get('city_id'):
                city_id = client_data['city_id']
                stmt = select(City).where(City.id == city_id)
                result = await session.execute(stmt)
                city = result.scalars().first()
                
                if not city:
                    logger.warning(f"City not found: {city_id}")
                    raise ValidationError(f"Ciudad con ID {city_id} no encontrada")
            
            # Validate gender_id if provided
            if client_data.get('gender_id'):
                gender_id = client_data['gender_id']
                stmt = select(Gender).where(Gender.id == gender_id)
                result = await session.execute(stmt)
                gender = result.scalars().first()
                
                if not gender:
                    logger.warning(f"Gender not found: {gender_id}")
                    raise ValidationError(f"Género con ID {gender_id} no encontrado")
            
            # Update client fields
            if client_data.get('address'):
                client.address = client_data['address']
            
            if client_data.get('phone'):
                client.phone = client_data['phone']
            
            if client_data.get('email'):
                client.email = client_data['email']
            
            if client_data.get('city_id'):
                client.city_id = client_data['city_id']
            
            if client_data.get('gender_id'):
                client.gender_id = client_data['gender_id']
            
            if client_data.get('birth_date'):
                try:
                    # Parse birth_date string to date object
                    birth_date_str = client_data['birth_date']
                    birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
                    client.birth_date = birth_date
                except ValueError as e:
                    logger.warning(f"Invalid birth_date format: {client_data['birth_date']}")
                    raise ValidationError("Formato de fecha de nacimiento inválido. Use YYYY-MM-DD")
            
            await session.commit()
            
            logger.info(
                f"Client info updated - Session: {session_slug}, "
                f"Client ID: {client.id}, "
                f"Updated fields: address={bool(client_data.get('address'))}, "
                f"phone={bool(client_data.get('phone'))}, "
                f"email={bool(client_data.get('email'))}, "
                f"city_id={bool(client_data.get('city_id'))}, "
                f"gender_id={bool(client_data.get('gender_id'))}, "
                f"birth_date={bool(client_data.get('birth_date'))}"
            )
    
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
    
    async def pre_expedite_policies(
        self,
        session_slug: str,
        is_pre_expedition: bool = True
    ) -> Dict[str, Any]:
        """
        Pre-expedite or expedite policies for a session.
        
        When is_pre_expedition=True:
        - Validates that policies can be issued (cotizador=true)
        - Does not charge payment
        - Returns pre-policy numbers
        
        When is_pre_expedition=False:
        - Actually issues the policies (cotizador=false)
        - Should be called after payment confirmation
        - Returns final policy numbers
        
        Processes SOAT and AP (if selected) in a single request to Mundial Seguros.
        RCE is processed separately but in parallel.
        
        Args:
            session_slug: Insurance session slug
            is_pre_expedition: True for quote mode, False for final issuance
            
        Returns:
            Dictionary with expedition results for each product
            
        Raises:
            ValidationError: If session not found, no selections, or validation fails
        """
        async with db_manager.get_async_session("dbw", self.sponsor) as session:
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
            
            # Validate session state based on operation
            if is_pre_expedition:
                # For pre-expedition, must have owner validated and plans selected
                if not insurance_session.is_owner:
                    raise ValidationError("Debe validar propiedad del vehículo antes de pre-expedir")
                
                if insurance_session.status not in [SessionStatus.SELECTED, SessionStatus.ISSUED]:
                    raise ValidationError(
                        f"Estado de sesión inválido para pre-expedición: {insurance_session.status.value}. "
                        "Debe estar en estado 'selected' o 'issued'"
                    )
            else:
                # For final expedition, must have payment confirmed
                if insurance_session.status != SessionStatus.PAYMENT_CONFIRMED:
                    raise ValidationError(
                        f"Estado de sesión inválido para expedición: {insurance_session.status.value}. "
                        "Debe estar en estado 'payment_confirmed'"
                    )
            
            # Get products with selections
            selected_products = []
            for quote_product in insurance_session.quote_products:
                if quote_product.selection and quote_product.status:
                    selected_products.append(quote_product)
            
            if not selected_products:
                raise ValidationError("No hay productos seleccionados para expedición")
            
            # Import here to avoid circular dependency
            from app.services.quote import QuoteService
            quote_service = QuoteService(self.sponsor)
            
            vehicle_class_selection = await quote_service.get_selected_homologation(session_slug)
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
                raise ValidationError("SOAT es obligatorio para expedición")
            
            # Reserve a SOAT form (only if not already reserved)
            forms_manager = SoatFormsManager(self.sponsor)
            existing_form = await forms_manager.get_form_for_session(insurance_session.id)
            
            if existing_form and existing_form.status == FormStatus.RESERVED:
                soat_form = existing_form
                logger.info(f"Using existing form reservation: {soat_form.form_number}")
            else:
                soat_form = await forms_manager.reserve_form_for_session(
                    session_id=insurance_session.id,
                )
                logger.info(f"Reserved new form: {soat_form.form_number}")
            
            # Build session data for expedition
            session_data = await quote_service._build_expedition_data(
                insurance_session,
                vehicle_class_selection,
                soat_product,
                ap_product,
                rce_product,
                soat_form.form_number
            )
            
            # Update session status
            if is_pre_expedition:
                insurance_session.status = SessionStatus.ISSUING
            else:
                insurance_session.status = SessionStatus.ISSUING
            await session.commit()
            
            # Call expedition service
            expedition_client = ExpeditionClient(self.sponsor)
            
            try:
                # Execute SOAT/AP and RCE in parallel if RCE is present
                if rce_product:
                    expedition_rce_client = ExpeditionRCEClient(self.sponsor)
                    mode = "pre-expedition" if is_pre_expedition else "expedition"
                    logger.info(f"Executing SOAT/AP and RCE {mode} in parallel")
                    
                    soat_task = expedition_client.pre_expedite_policy(session_data, is_pre_expedition)
                    rce_task = expedition_rce_client.pre_expedite_rce_policy(session_data, is_pre_expedition)
                    
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
                        logger.error(f"SOAT {mode} failed: {str(soat_response)}")
                        all_success = False
                        results.append({
                            "product_code": "SOAT",
                            "success": False,
                            "message": f"Error en {mode} SOAT: {str(soat_response)}",
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
                                "message": f"AP no procesado debido a error en SOAT",
                                "details": {}
                            })
                        else:
                            results.append({
                                "product_code": "AP",
                                "success": soat_response.success,
                                "message": soat_response.message if ap_product else "AP procesado con SOAT",
                                "details": {}
                            })
                    
                    # Process RCE response
                    if isinstance(rce_response, Exception):
                        logger.error(f"RCE {mode} failed: {str(rce_response)}")
                        all_success = False
                        results.append({
                            "product_code": "RCE",
                            "success": False,
                            "message": f"Error en {mode} RCE: {str(rce_response)}",
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
                    # Only SOAT (and optionally AP)
                    mode = "pre-expedition" if is_pre_expedition else "expedition"
                    logger.info(f"Executing SOAT/AP {mode}")
                    
                    soat_response = await expedition_client.pre_expedite_policy(session_data, is_pre_expedition)
                    
                    results = []
                    all_success = soat_response.success
                    
                    results.append({
                        "product_code": "SOAT",
                        "success": soat_response.success,
                        "message": soat_response.message,
                        "details": soat_response.details
                    })
                    
                    if ap_product:
                        results.append({
                            "product_code": "AP",
                            "success": soat_response.success,
                            "message": "AP procesado con SOAT",
                            "details": {}
                        })
                
                # Update session status based on result
                if all_success:
                    if is_pre_expedition:
                        insurance_session.status = SessionStatus.ISSUED
                        message = "Pre-expedición completada exitosamente"
                    else:
                        insurance_session.status = SessionStatus.PAYMENT_PENDING
                        message = "Expedición completada exitosamente"
                else:
                    insurance_session.status = SessionStatus.ISSUE_FAILED
                    message = "Expedición completada con errores"
                
                await session.commit()
                
                logger.info(
                    f"Expedition completed - Session: {session_slug}, "
                    f"Mode: {'pre-expedition' if is_pre_expedition else 'expedition'}, "
                    f"Status: {insurance_session.status.value}, "
                    f"Success: {all_success}"
                )
                
                return {
                    "session_slug": session_slug,
                    "message": message,
                    "results": results,
                    "total_processed": len(results),
                    "all_success": all_success
                }
                
            except Exception as e:
                # Update session to failed state
                insurance_session.status = SessionStatus.ISSUE_FAILED
                await session.commit()
                
                logger.error(
                    f"Expedition failed - Session: {session_slug}, "
                    f"Error: {str(e)}",
                    exc_info=True
                )
                raise

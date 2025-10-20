"""
Expedition Endpoints

API endpoints for insurance policy expedition (pre-expedition and final issuance).
"""

import logging
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any

from app.schemas.expedition import (
    SelectPlanRequest,
    SelectPlanResponse,
    PreExpeditionRequest,
    PreExpeditionResponse,
    ExpeditionResponse
)
from app.services.expedition import ExpeditionService
from app.middleware.dependencies import get_current_user
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/select-plan/{session_slug}", 
    response_model=SelectPlanResponse,
    deprecated=True,
    description="⚠️ DEPRECATED: Use POST /pre-expedition/{session_slug} instead. "
                "This endpoint will be removed in a future version. "
                "The new pre-expedition endpoint combines plan selection and validation in a single call."
)
async def select_plan(
    session_slug: str,
    request: SelectPlanRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> SelectPlanResponse:
    """
    **⚠️ DEPRECATED - Use POST /pre-expedition/{session_slug} instead**
    
    Select specific plan options for one or multiple products in a session.
    
    **MIGRATION NOTICE:**
    This endpoint is deprecated in favor of the combined `/pre-expedition` endpoint
    which performs both plan selection and validation in a single atomic operation.
    
    **New Flow:**
    Instead of:
    1. POST /select-plan/{session_slug} (select plans)
    2. POST /pre-expedition/{session_slug} (validate)
    
    Use:
    1. POST /pre-expedition/{session_slug} (select + validate)
    
    **Example Migration:**
    
    Old approach:
    ```python
    # Step 1: Select plans
    POST /expedition/select-plan/abc123
    {
      "selections": [
        {"product_code": "SOAT", "option_id": 125}
      ]
    }
    
    # Step 2: Validate
    POST /expedition/pre-expedition/abc123
    ```
    
    New approach:
    ```python
    # Single call - select + validate
    POST /expedition/pre-expedition/abc123
    {
      "selections": [
        {"product_code": "SOAT", "option_id": 125}
      ]
    }
    ```
    
    ---
    
    This endpoint allows users to choose plans for multiple products in a single request.
    Each product can have one plan selection. The selections are validated to ensure:
    - Each option exists and is active
    - Each option belongs to the specified product
    - Each product exists in the session
    - No duplicate product selections in the request
    
    If a selection already exists for a product, it will be updated.
    Otherwise, a new selection will be created.
    
    **Requirements:**
    - Session must exist
    - Each product must exist in session
    - Each option must be valid and active for its product
    - No duplicate products in the selections array
    
    **Examples:**
    
    Single product selection:
    ```json
    {
      "selections": [
        {"product_code": "SOAT", "option_id": 125}
      ]
    }
    ```
    
    Multiple products selection:
    ```json
    {
      "selections": [
        {"product_code": "SOAT", "option_id": 125},
        {"product_code": "AP", "option_id": 124},
        {"product_code": "RCE", "option_id": 130}
      ]
    }
    ```
    
    Args:
        session_slug: Insurance session UUID slug
        request: SelectPlanRequest with list of selections
        current_user: Current user information from token
        
    Returns:
        SelectPlanResponse with confirmation and all selected plan details
        
    Raises:
        400: Validation error (invalid option, inactive option, duplicate products, etc.)
        404: Session or product not found
        500: Internal server error
    """
    try:
        expedition_service = ExpeditionService(current_user.get("sponsor"))
        
        # Convert Pydantic models to dict for service layer
        selections_data = [
            {
                "product_code": sel.product_code,
                "option_id": sel.option_id
            }
            for sel in request.selections
        ]
        
        result = await expedition_service.select_plan(
            session_slug=session_slug,
            selections=selections_data
        )
        
        return SelectPlanResponse(**result)
        
    except ValidationError as e:
        logger.warning(f"Plan selection validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error selecting plan: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/pre-expedition/{session_slug}", response_model=PreExpeditionResponse)
async def pre_expedite_policies(
    session_slug: str,
    request: PreExpeditionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> PreExpeditionResponse:
    """
    Select plans and pre-expedite policies for a session (combined endpoint).
    
    This endpoint combines plan selection, client information update, and pre-expedition 
    validation into a single call. It first selects the plans for the specified products,
    updates the client information, then validates that insurance policies can be issued 
    before sending the user to the payment gateway.
    
    **Process:**
    1. Validates and selects the specified plans for each product
    2. Updates client information (address, phone, email, birth_date if AP selected)
    3. Validates session exists and has owner validated
    4. Calls Mundial Seguros expedition service with `cotizador=true` flag
    5. SOAT and AP (if selected) are sent in a single request
    6. RCE (if selected) is sent in a separate parallel request
    7. Returns validation results for each product
    
    **Requirements:**
    - Session must exist
    - Session must have `is_owner=true` (owner validation completed)
    - Session must be in `selected` or `issued` state
    - At least SOAT must be included in selections
    - Each option must be valid and active for its product
    - No duplicate products in the selections array
    - Address, phone, email, city_id, and gender_id are required
    - City_id must be a valid city in the database
    - Gender_id must be a valid gender in the database
    - Birth date is required if AP is selected
    
    **Use Case:**
    This should be called after the user has:
    1. Created a quote (viewed available plans via `/quote/options`)
    2. User selected their preferred plans (sent in this request)
    3. User provided contact and address information
    4. Before redirecting to payment gateway
    
    **Important:**
    - Uses `cotizador=true` flag (pre-expedition mode)
    - Does NOT create final policy
    - Does NOT charge payment
    - Validates that policy CAN be issued
    - Returns pre-policy validation results
    - Updates client record in database
    
    **Example Request:**
    ```json
    {
      "selections": [
        {"product_code": "SOAT", "option_id": 125},
        {"product_code": "AP", "option_id": 124}
      ],
      "address": "Calle 123 #45-67",
      "phone": "3001234567",
      "email": "cliente@example.com",
      "city_id": 1,
      "gender_id": 1,
      "birth_date": "1990-05-15"
    }
    ```
    
    Args:
        session_slug: Insurance session UUID slug
        request: PreExpeditionRequest with plan selections
        current_user: Current user information from token
        
    Returns:
        PreExpeditionResponse with results for each product
        
    Raises:
        400: Validation error (invalid selections, owner not validated, etc.)
        404: Session not found
        500: Internal server error or external service error
    """
    try:
        expedition_service = ExpeditionService(current_user.get("sponsor"))
        
        # Step 1: Select plans
        selections_data = [
            {
                "product_code": sel.product_code,
                "option_id": sel.option_id
            }
            for sel in request.selections
        ]
        
        await expedition_service.select_plan(
            session_slug=session_slug,
            selections=selections_data
        )
        
        logger.info(f"Plans selected successfully for session {session_slug}")
        
        # Step 2: Update client information
        client_data = {
            "address": request.address,
            "phone": request.phone,
            "email": request.email,
            "city_id": request.city_id,
            "gender_id": request.gender_id,
            "birth_date": request.birth_date
        }
        
        await expedition_service.update_client_info(
            session_slug=session_slug,
            client_data=client_data
        )
        
        logger.info(f"Client information updated successfully for session {session_slug}")
        
        # Step 3: Pre-expedite with the selected plans (cotizador=true)
        result = await expedition_service.pre_expedite_policies(
            session_slug=session_slug,
            is_pre_expedition=True
        )
        
        return PreExpeditionResponse(**result)
        
    except ValidationError as e:
        logger.warning(f"Pre-expedition validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in pre-expedition: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/expedition/{session_slug}", response_model=ExpeditionResponse)
async def expedite_policies(
    session_slug: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ExpeditionResponse:
    """
    Expedite final policies for a session (actual issuance).
    
    This endpoint issues the final insurance policies after payment has been confirmed.
    It calls Mundial Seguros expedition service with `cotizador=false` flag to create
    the actual policies.
    
    **Process:**
    1. Validates session exists and payment is confirmed
    2. Validates plans were previously selected
    3. Calls Mundial Seguros expedition service with `cotizador=false` flag
    4. SOAT and AP (if selected) are sent in a single request
    5. RCE (if selected) is sent in a separate parallel request
    6. Returns expedition results with final policy numbers
    
    **Requirements:**
    - Session must exist
    - Session must be in `payment_confirmed` state
    - Plans must have been previously selected and pre-expedited
    - Payment must have been confirmed by payment gateway
    - SOAT form must be reserved
    
    **Use Case:**
    This should be called after:
    1. Pre-expedition was successful (POST /pre-expedition)
    2. User was redirected to payment gateway
    3. Payment was confirmed by payment gateway webhook/callback
    4. Session status was updated to `payment_confirmed`
    
    **Important:**
    - Uses `cotizador=false` flag (final expedition mode)
    - CREATES final policies
    - Cannot be reversed
    - Returns actual policy numbers
    - Updates SOAT form status to ISSUED
    
    **No Request Body Required** - Uses previously selected plans
    
    Args:
        session_slug: Insurance session UUID slug
        current_user: Current user information from token
        
    Returns:
        ExpeditionResponse with final policy details for each product
        
    Raises:
        400: Validation error (payment not confirmed, invalid state, etc.)
        404: Session not found
        500: Internal server error or external service error
    """
    try:
        expedition_service = ExpeditionService(current_user.get("sponsor"))
        
        # Expedite policies with is_pre_expedition=False (actual issuance)
        result = await expedition_service.pre_expedite_policies(
            session_slug=session_slug,
            is_pre_expedition=False
        )
        
        return ExpeditionResponse(**result)
        
    except ValidationError as e:
        logger.warning(f"Expedition validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in expedition: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

"""
Quote endpoints

Handles insurance quote requests (creating quotes and viewing options).
Plan selection and expedition are handled in the expedition endpoints.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from app.schemas.quote import (
    QuoteRequest,
    QuoteResponse,
    SelectedHomologationResponse,
    AvailableHomologationsResponse,
    HomologationInfo,
    QuoteOptionsResponse
)
from app.services.quote import QuoteService
from app.middleware.dependencies import get_current_user
from app.core.exceptions import ValidationError
from app.models.insurance_session import InsuranceSession
from app.models.vehicle_homologation import VehicleHomologation
from app.database.session import db_manager
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/create", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
async def create_quote(
    request: QuoteRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> QuoteResponse:
    """
    Create or update a quote for an insurance session.
    
    **Requirements:**
    - Session must exist
    - Session must have is_owner=true
    - Session must have status=validated|quoted
    - class_code must exist in vehicle_homologations for this session
    - products must be valid, active product codes
    - All mandatory products must be included
    
    **Process:**
    - If selection already exists, it will be updated
    - If selection doesn't exist, it will be created
    - Session status will be updated to QUOTED
    
    Args:
        request: Quote request with session_id, class_code, and products
        current_user: Current user information from token
        
    Returns:
        QuoteResponse with quote details and validated products
        
    Raises:
        400: Validation error (invalid products, missing mandatory products, etc.)
        404: Session or homologation not found
        500: Internal server error
    """
    try:
        quote_service = QuoteService(current_user.get("sponsor"))
        
        result = await quote_service.create_quote(
            session_slug=request.session_id,
            class_code=request.class_code,
            products=request.products
        )
        
        return QuoteResponse(**result)
        
    except ValidationError as e:
        logger.warning(f"Quote validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating quote: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/selected/{session_slug}", response_model=SelectedHomologationResponse)
async def get_selected_homologation(
    session_slug: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> SelectedHomologationResponse:
    """
    Get the selected homologation for a session.
    
    Args:
        session_slug: Insurance session UUID slug
        sponsor: Sponsor identifier from token
        
    Returns:
        SelectedHomologationResponse with selection details
        
    Raises:
        404: Selection not found
        500: Internal server error
    """
    try:
        quote_service = QuoteService(current_user.get("sponsor"))
        
        result = await quote_service.get_selected_homologation(session_slug)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No selection found for session: {session_slug}"
            )
        
        return SelectedHomologationResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting selected homologation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/available/{session_slug}", response_model=AvailableHomologationsResponse)
async def get_available_homologations(
    session_slug: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> AvailableHomologationsResponse:
    """
    Get all available homologations for a session.
    
    Args:
        session_slug: Insurance session UUID slug
        sponsor: Sponsor identifier from token
        
    Returns:
        AvailableHomologationsResponse with list of available homologations
        
    Raises:
        404: Session not found
        500: Internal server error
    """
    try:
        sponsor = current_user.get("sponsor")
        async with db_manager.get_async_session("dbr", sponsor) as session:
            # Get session
            stmt_session = select(InsuranceSession).where(
                InsuranceSession.slug == session_slug
            )
            result_session = await session.execute(stmt_session)
            insurance_session = result_session.scalars().first()
            
            if not insurance_session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session not found: {session_slug}"
                )
            
            # Get homologations
            stmt = select(VehicleHomologation).where(
                VehicleHomologation.session_id == insurance_session.id
            )
            result = await session.execute(stmt)
            homologations = result.scalars().all()
            
            homologations_list = [
                HomologationInfo(
                    id=h.id,
                    class_code=h.class_code or "",
                    class_description=h.class_description,
                    transport_type_code=h.transport_type_code,
                    brand_code=h.brand_code,
                    line_code=h.line_code,
                    destination_code=h.destination_code
                )
                for h in homologations
            ]
            
            return AvailableHomologationsResponse(
                session_slug=session_slug,
                homologations=homologations_list,
                count=len(homologations_list)
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting available homologations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/options/{session_slug}", response_model=QuoteOptionsResponse)
async def get_quote_options(
    session_slug: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> QuoteOptionsResponse:
    """
    Get all available plan options for products in a session.
    
    Returns all products with their available plan options, including:
    - Product information (code, name)
    - List of plans with option_id, plan_name, price, and coverage details
    
    **Requirements:**
    - Session must exist
    - Session must have quoted products
    
    Args:
        session_slug: Insurance session UUID slug
        current_user: Current user information from token
        
    Returns:
        QuoteOptionsResponse with products and their plan options
        
    Raises:
        404: Session not found
        500: Internal server error
    """
    try:
        quote_service = QuoteService(current_user.get("sponsor"))
        
        result = await quote_service.get_quote_options(session_slug)
        
        return QuoteOptionsResponse(**result)
        
    except ValidationError as e:
        logger.warning(f"Quote options validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting quote options: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


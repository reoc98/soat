"""
Owner Validation Endpoint

API endpoint for validating vehicle ownership.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends

from app.schemas.prequote import PreQuoteRequest, PreQuoteResponse, OwnerInfo, VehicleInfo
from app.services.owner_validation import OwnerValidationService
from app.middleware.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/validate", response_model=PreQuoteResponse, summary="Validate Vehicle Owner")
async def validate_vehicle_owner(
    request: PreQuoteRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Validate vehicle ownership and create/update client information.
    
    Process:
    1. Create client and vehicle records with minimal information (document, plate)
    2. Query RUNT API to get additional vehicle and owner information
    3. Update client and vehicle records with RUNT data if available
    4. Validate if provided document matches vehicle owner
    5. Return validation result with owner and vehicle information
    
    If RUNT service is unavailable, client and vehicle are still created with 
    minimal information for later processing.
    
    Requires authentication token with sponsor information.
    """
    try:
        # Get sponsor from token
        sponsor = current_user.get("sponsor")
        
        # user_email = current_user.get("email")
        
        logger.info(
            f"Owner validation request - "
            f"Sponsor: {sponsor}, "
            f"Document: {request.document_type}/{request.document_number}, "
            f"Plate: {request.license_plate}"
        )
        
        # Use validation service
        validation_service = OwnerValidationService(sponsor)
        
        result = await validation_service.validate_owner(
            document_type_code=request.document_type,
            document_number=request.document_number,
            license_plate=request.license_plate,
            # user_email=user_email
        )
        
        # Build response based on validation result
        owner_data = result.get("owner_data")
        vehicle_data = result.get("vehicle_data")
        
        if result.get("is_owner") and owner_data and vehicle_data:
            # Successful validation with complete RUNT data
            return PreQuoteResponse(
                is_owner=True,
                message=result["message"],
                owner_info=OwnerInfo(
                    client_id=result["client_id"],
                    document_type=owner_data.get("document_type", ""),
                    document_number=owner_data.get("document_number", ""),
                    first_name=owner_data.get("first_name", ""),
                    last_name=owner_data.get("last_name", ""),
                    second_last_name=owner_data.get("second_last_name", ""),
                    full_name=owner_data.get("full_name", "")
                ),
                vehicle_info=VehicleInfo(
                    license_plate=vehicle_data.get("license_plate", request.license_plate),
                    brand=vehicle_data.get("brand", ""),
                    model=vehicle_data.get("line", ""),
                    year=vehicle_data.get("model_year"),
                    vehicle_class=vehicle_data.get("vehicle_class"),
                    # vehicle_type=vehicle_data.get("vehicle_type"),
                    # engine_number=vehicle_data.get("engine_number"),
                    # chassis_number=vehicle_data.get("chassis_number"),
                    cylinder_capacity=vehicle_data.get("engine_cc"),
                    fuel_type=vehicle_data.get("fuel_type"),
                    color=vehicle_data.get("color"),
                    service_type=vehicle_data.get("service_type"),
                    homologations=vehicle_data.get("homologations", [])
                ),
                session_id=result.get("session_slug")
            )
        elif not result.get("is_owner") and result.get("runt_available"):
            # RUNT data available but ownership validation failed
            return PreQuoteResponse(
                is_owner=False,
                message=result["message"],
                owner_info=None,
                vehicle_info=None,
                session_id=None
            )
        else:
            # RUNT service unavailable - return minimal information
            return PreQuoteResponse(
                is_owner=False,
                message=result["message"],
                owner_info=None,
                vehicle_info=None,
                session_id=None
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in owner validation: {str(e)}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during validation"
        )

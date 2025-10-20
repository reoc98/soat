"""
Session Information Endpoint

API endpoint for retrieving session information with conditional visibility.
"""

import logging
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any

from app.schemas.session_info import SessionInfoResponse
from app.services.session_info import SessionInfoService
from app.middleware.dependencies import get_current_user
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/info/{session_slug}", response_model=SessionInfoResponse)
async def get_session_info(
    session_slug: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> SessionInfoResponse:
    """
    Get session information with conditional visibility based on status.
    
    This endpoint retrieves comprehensive session information including owner
    and vehicle data. The visibility of sensitive information depends on the
    session's current status.
    
    **Visibility Rules:**
    
    1. **Pre-Quote States** (details visible):
       - `created` - Session just created
       - `started` - Session started (legacy)
       - `validating` - Owner validation in progress
       - `validated` - Owner successfully validated
       - `validation_failed` - Owner validation failed
       
       → Returns full owner and vehicle information
    
    2. **Post-Quote States** (details hidden):
       - `quoting` - Quote generation in progress
       - `quoted` - Quote generated
       - `selected` - Plans selected
       - `issued` - Policies pre-issued
       - `payment_confirmed` - Payment confirmed
       - `completed` - Process completed
       - (and all other subsequent states)
       
       → Returns only session status and metadata
       → `owner_info` and `vehicle_info` are `null`
    
    **Use Cases:**
    
    1. **Check validation status:**
       ```
       GET /session/info/{session_slug}
       → Returns validation status and owner/vehicle data
       ```
    
    2. **Resume interrupted flow:**
       ```
       GET /session/info/{session_slug}
       → Check status to determine next step
       ```
    
    3. **Monitor session progress:**
       ```
       GET /session/info/{session_slug}
       → Track session through different states
       ```
    
    **Security:**
    - Sensitive owner/vehicle data is hidden after quote creation
    - Only session metadata is visible in advanced states
    - Requires valid authentication token
    
    **Response Examples:**
    
    Pre-quote state (validated):
    ```json
    {
      "session_slug": "abc123",
      "status": "validated",
      "status_display": "Propietario validado",
      "is_owner": true,
      "can_view_details": true,
      "owner_info": {
        "client_id": 123,
        "document_number": "1234567890",
        "full_name": "Juan Pérez"
      },
      "vehicle_info": {
        "vehicle_id": 456,
        "license_plate": "ABC123",
        "brand": "TOYOTA"
      },
      "message": "Propietario validado exitosamente. Puede proceder a cotizar."
    }
    ```
    
    Post-quote state (quoted):
    ```json
    {
      "session_slug": "abc123",
      "status": "quoted",
      "status_display": "Cotización generada",
      "is_owner": true,
      "can_view_details": false,
      "owner_info": null,
      "vehicle_info": null,
      "message": "Información de propietario y vehículo no disponible..."
    }
    ```
    
    Args:
        session_slug: Insurance session UUID slug
        current_user: Current user information from token
        
    Returns:
        SessionInfoResponse with session information and conditional details
        
    Raises:
        404: Session not found
        500: Internal server error
    """
    try:
        session_info_service = SessionInfoService(current_user.get("sponsor"))
        
        result = await session_info_service.get_session_info(session_slug)
        
        return SessionInfoResponse(**result)
        
    except ValidationError as e:
        logger.warning(f"Session info validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting session info: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

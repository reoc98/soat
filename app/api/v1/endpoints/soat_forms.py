"""
SOAT Forms endpoints

Administrative endpoints for managing SOAT form lifecycle.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, Optional

from app.schemas.soat_forms import (
    FetchFormsResponse,
    FormsStatsResponse,
    BlockFormRequest,
    UnblockFormRequest,
    FormActionResponse,
    ListFormsResponse,
    FormInfo
)
from app.services.soat_forms_manager import SoatFormsManager
from app.middleware.dependencies import get_current_user, require_admin, require_any_role
from app.core.exceptions import ValidationError
from app.models.soat_form import SoatForm, FormStatus
from app.database.session import db_manager
from sqlalchemy import select, and_, or_

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/fetch", response_model=FetchFormsResponse, status_code=status.HTTP_200_OK)
async def fetch_forms_from_external(
    current_user: Dict[str, Any] = Depends(require_admin())
) -> FetchFormsResponse:
    """
    Fetch available forms from Mundial Seguros external service.
    
    **🔒 Admin Only** - This endpoint requires admin role.
    
    This endpoint manually triggers synchronization with the external SOAP service
    to retrieve available form numbers and store them in the database.
    
    **Process:**
    - Calls consultarFormulariosDisponibles SOAP service
    - Parses the diffgr:diffgram XML response
    - Stores new forms (skips duplicates)
    - Returns summary of the operation
    
    **Use cases:**
    - Manual inventory replenishment
    - Initial system setup
    - Recovery after system issues
    
    Args:
        current_user: Current user information from token (admin required)
        
    Returns:
        FetchFormsResponse with fetch results
        
    Raises:
        400: Validation error (external service error)
        500: Internal server error
    """
    try:
        forms_manager = SoatFormsManager(current_user.get("sponsor"))
        
        result = await forms_manager.fetch_and_store_forms()
        
        return FetchFormsResponse(
            success=result["success"],
            new_forms=result["new_forms"],
            existing_forms=result["existing_forms"],
            total_fetched=result["total_fetched"],
            message=f"Successfully fetched {result['total_fetched']} forms. "
                   f"New: {result['new_forms']}, Existing: {result['existing_forms']}"
        )
        
    except ValidationError as e:
        logger.warning(f"Forms fetch validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error fetching forms: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/stats", response_model=FormsStatsResponse, status_code=status.HTTP_200_OK)
async def get_forms_statistics(
    current_user: Dict[str, Any] = Depends(require_any_role("admin", "supervisor"))
) -> FormsStatsResponse:
    """
    Get current forms statistics.
    
    **🔒 Admin or Supervisor** - This endpoint requires admin or supervisor role.
    
    Returns count of forms grouped by status and alerts if inventory is low.
    
    **Statistics include:**
    - Total forms in database
    - Count by status (available, reserved, used, blocked, expired)
    - Low inventory alert (available < MIN_FORMS_THRESHOLD)
    
    **Use cases:**
    - Dashboard monitoring
    - Capacity planning
    - Inventory management
    
    Args:
        current_user: Current user information from token
        
    Returns:
        FormsStatsResponse with statistics
        
    Raises:
        500: Internal server error
    """
    try:
        forms_manager = SoatFormsManager(current_user.get("sponsor"))
        
        stats = await forms_manager.get_forms_stats()
        
        return FormsStatsResponse(
            total=stats["total"],
            available=stats["available"],
            reserved=stats["reserved"],
            used=stats["used"],
            blocked=stats["blocked"],
            expired=stats["expired"],
            needs_refill=stats["needs_refill"]
        )
        
    except Exception as e:
        logger.error(f"Error getting forms stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("", response_model=ListFormsResponse, status_code=status.HTTP_200_OK)
async def list_forms(
    status_filter: Optional[str] = Query(None, description="Filter by status: available, reserved, used, blocked, expired"),
    session_id: Optional[int] = Query(None, description="Filter by session ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(require_any_role("admin", "supervisor"))
) -> ListFormsResponse:
    """
    List forms with pagination and filtering.
    
    **🔒 Admin or Supervisor** - This endpoint requires admin or supervisor role.
    
    **Filters:**
    - status: Filter by form status
    - session_id: Filter by session association
    
    **Pagination:**
    - page: Page number (starts at 1)
    - page_size: Items per page (max 100)
    
    **Use cases:**
    - Forms inventory review
    - Debugging session issues
    - Auditing form usage
    
    Args:
        status_filter: Optional status filter
        session_id: Optional session ID filter
        page: Page number
        page_size: Items per page
        current_user: Current user information from token
        
    Returns:
        ListFormsResponse with paginated forms list
        
    Raises:
        400: Invalid status filter
        500: Internal server error
    """
    try:
        # Validate status filter
        if status_filter:
            try:
                FormStatus(status_filter)
            except ValueError:
                raise ValidationError(
                    f"Invalid status: {status_filter}. "
                    f"Valid values: {', '.join([s.value for s in FormStatus])}"
                )
        
        sponsor = current_user.get("sponsor")
        
        async with db_manager.get_async_session("dbr", sponsor) as session:
            # Build query
            conditions = []
            
            if status_filter:
                conditions.append(SoatForm.status == status_filter)
            
            if session_id:
                conditions.append(SoatForm.session_id == session_id)
            
            # Count total
            count_stmt = select(SoatForm)
            if conditions:
                count_stmt = count_stmt.where(and_(*conditions))
            
            count_result = await session.execute(count_stmt)
            all_forms = count_result.scalars().all()
            total = len(all_forms)
            
            # Paginate
            offset = (page - 1) * page_size
            stmt = select(SoatForm)
            if conditions:
                stmt = stmt.where(and_(*conditions))
            
            stmt = stmt.order_by(SoatForm.created_at.desc()).offset(offset).limit(page_size)
            
            result = await session.execute(stmt)
            forms = result.scalars().all()
            
            # Convert to FormInfo
            forms_info = [
                FormInfo(
                    id=form.id,
                    form_number=form.form_number,
                    cod_suc=form.cod_suc,
                    cod_agente=form.cod_agente,
                    cod_pto_vta=form.cod_pto_vta,
                    status=form.status,
                    session_id=form.session_id,
                    reserved_at=form.reserved_at,
                    used_at=form.used_at,
                    blocked_at=form.blocked_at,
                    expires_at=form.expires_at,
                    created_at=form.created_at,
                    updated_at=form.updated_at,
                    blocked_reason=form.blocked_reason,
                    notes=form.notes,
                    sponsor=sponsor
                )
                for form in forms
            ]
            
            total_pages = (total + page_size - 1) // page_size
            
            return ListFormsResponse(
                forms=forms_info,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages
            )
        
    except ValidationError as e:
        logger.warning(f"Forms list validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error listing forms: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/block", response_model=FormActionResponse, status_code=status.HTTP_200_OK)
async def block_form(
    request: BlockFormRequest,
    current_user: Dict[str, Any] = Depends(require_admin())
) -> FormActionResponse:
    """
    Block a form manually.
    
    **🔒 Admin Only** - This endpoint requires admin role.
    
    Blocking prevents a form from being used in reservations or expeditions.
    
    **Use cases:**
    - Form reported as invalid by Mundial Seguros
    - Form causing errors in expeditions
    - Manual intervention required
    
    **Effect:**
    - Status changes to BLOCKED
    - blocked_at timestamp set
    - blocked_reason stored
    - Cannot be reserved until unblocked
    
    Args:
        request: Block request with form_number and reason
        current_user: Current user information from token (admin required)
        
    Returns:
        FormActionResponse with success status
        
    Raises:
        400: Form not found
        500: Internal server error
    """
    try:
        forms_manager = SoatFormsManager(current_user.get("sponsor"))
        
        form = await forms_manager.block_form(
            form_number=request.form_number,
            reason=request.reason
        )
        
        return FormActionResponse(
            success=True,
            message=f"Form {request.form_number} blocked successfully",
            form_number=form.form_number,
            status=form.status
        )
        
    except ValidationError as e:
        logger.warning(f"Form block validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error blocking form: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/unblock", response_model=FormActionResponse, status_code=status.HTTP_200_OK)
async def unblock_form(
    request: UnblockFormRequest,
    current_user: Dict[str, Any] = Depends(require_admin())
) -> FormActionResponse:
    """
    Unblock a previously blocked form.
    
    **🔒 Admin Only** - This endpoint requires admin role.
    
    Unblocking makes a form available again for reservations.
    
    **Effect:**
    - Status changes to AVAILABLE
    - blocked_at timestamp cleared
    - blocked_reason cleared
    - Form can be reserved again
    
    **Requirements:**
    - Form must currently be BLOCKED
    
    Args:
        request: Unblock request with form_number
        current_user: Current user information from token (admin required)
        
    Returns:
        FormActionResponse with success status
        
    Raises:
        400: Form not found or not blocked
        500: Internal server error
    """
    try:
        forms_manager = SoatFormsManager(current_user.get("sponsor"))
        
        form = await forms_manager.unblock_form(
            form_number=request.form_number
        )
        
        return FormActionResponse(
            success=True,
            message=f"Form {request.form_number} unblocked successfully",
            form_number=form.form_number,
            status=form.status
        )
        
    except ValidationError as e:
        logger.warning(f"Form unblock validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error unblocking form: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

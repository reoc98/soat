"""
Ejemplos de uso de InsuranceSession y VehicleHomologation
"""

from app.models.insurance_session import InsuranceSession, SessionStatus
from app.models.vehicle_homologation import VehicleHomologation
from app.database.session import db_manager
from sqlalchemy import select
from sqlalchemy.orm import selectinload


# ============================================================================
# EJEMPLO 1: Crear una nueva sesión de seguro
# ============================================================================

async def create_new_session(client_id: int, vehicle_id: int) -> str:
    """Crea una nueva sesión de seguro y retorna el UUID slug."""
    
    # Opción 1: Usar el factory method (recomendado)
    session = InsuranceSession.create_session(
        client_id=client_id,
        vehicle_id=vehicle_id,
        is_owner=False,
        status=SessionStatus.STARTED
    )
    
    # Opción 2: Crear manualmente
    # session = InsuranceSession(
    #     slug=str(uuid.uuid4()),
    #     client_id=client_id,
    #     vehicle_id=vehicle_id,
    #     is_owner=False,
    #     status=SessionStatus.STARTED
    # )
    
    async with db_manager.get_session() as db:
        db.add(session)
        await db.commit()
        await db.refresh(session)
    
    print(f"✅ Sesión creada con UUID: {session.slug}")
    return session.slug


# ============================================================================
# EJEMPLO 2: Actualizar sesión después de validación RUNT
# ============================================================================

async def update_session_after_runt_validation(
    session_slug: str,
    is_owner: bool,
    homologations: list[dict]
) -> None:
    """Actualiza la sesión con resultados de RUNT."""
    
    async with db_manager.get_session() as db:
        # Buscar sesión por slug (UUID)
        result = await db.execute(
            select(InsuranceSession).where(InsuranceSession.slug == session_slug)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise ValueError(f"❌ Sesión no encontrada: {session_slug}")
        
        # Actualizar estado de propiedad
        session.is_owner = is_owner
        session.status = SessionStatus.VALIDATED
        
        # Guardar homologaciones
        for homolog_data in homologations:
            homologation = VehicleHomologation(
                session_id=session.id,
                vehicle_info_id=homolog_data.get("vehicle_info_id"),
                class_code=homolog_data.get("class_code"),
                class_description=homolog_data.get("class_description"),
                transport_type_code=homolog_data.get("transport_type_code"),
                brand_code=homolog_data.get("brand_code"),
                line_code=homolog_data.get("line_code"),
                destination_code=homolog_data.get("destination_code")
            )
            db.add(homologation)
        
        await db.commit()
        print(f"✅ Sesión {session_slug} actualizada con {len(homologations)} homologaciones")


# ============================================================================
# EJEMPLO 3: Obtener sesión con todas las relaciones
# ============================================================================

async def get_session_details(session_slug: str) -> dict:
    """Obtiene sesión completa con cliente, vehículo y homologaciones."""
    
    async with db_manager.get_session() as db:
        result = await db.execute(
            select(InsuranceSession)
            .options(
                selectinload(InsuranceSession.client),
                selectinload(InsuranceSession.vehicle),
                selectinload(InsuranceSession.homologations)
            )
            .where(InsuranceSession.slug == session_slug)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            return None
        
        return {
            "session_id": session.id,
            "slug": session.slug,
            "status": session.status.value,
            "is_owner": session.is_owner,
            "created_at": session.created_at.isoformat(),
            "client": {
                "id": session.client.id,
                "document_number": session.client.document_number,
                "full_name": session.client.full_name or f"{session.client.first_name} {session.client.last_name}",
                "email": session.client.email
            },
            "vehicle": {
                "id": session.vehicle.id,
                "license_plate": session.vehicle.license_plate,
                "brand": session.vehicle.brand,
                "model": session.vehicle.model,
                "year": session.vehicle.year
            },
            "homologations": [
                {
                    "vehicle_info_id": h.vehicle_info_id,
                    "class_code": h.class_code,
                    "class_description": h.class_description,
                    "transport_type_code": h.transport_type_code,
                    "brand_code": h.brand_code,
                    "line_code": h.line_code,
                    "destination_code": h.destination_code
                }
                for h in session.homologations
            ]
        }


# ============================================================================
# EJEMPLO 4: Actualizar estado de sesión
# ============================================================================

async def progress_session_status(session_slug: str, new_status: SessionStatus) -> bool:
    """Avanza el estado de una sesión en el flujo de compra."""
    
    async with db_manager.get_session() as db:
        result = await db.execute(
            select(InsuranceSession).where(InsuranceSession.slug == session_slug)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            print(f"❌ Sesión no encontrada: {session_slug}")
            return False
        
        old_status = session.status.value
        session.status = new_status
        await db.commit()
        
        print(f"✅ Sesión {session_slug}: {old_status} → {new_status.value}")
        return True


# ============================================================================
# EJEMPLO 5: Flujo completo - Owner Validation con Sesión
# ============================================================================

async def complete_owner_validation_flow(
    client_id: int,
    vehicle_id: int,
    runt_response: dict
) -> dict:
    """Flujo completo: crear sesión, validar propietario, guardar homologaciones."""
    
    # 1. Crear sesión
    session_slug = await create_new_session(client_id, vehicle_id)
    
    # 2. Procesar respuesta de RUNT
    is_owner = runt_response.get("is_owner", False)
    homologations_data = runt_response.get("homologations", [])
    
    # 3. Actualizar sesión con datos de RUNT
    await update_session_after_runt_validation(
        session_slug=session_slug,
        is_owner=is_owner,
        homologations=homologations_data
    )
    
    # 4. Obtener detalles completos
    session_details = await get_session_details(session_slug)
    
    return session_details


# ============================================================================
# EJEMPLO 6: Listar sesiones recientes de un cliente
# ============================================================================

async def get_client_recent_sessions(client_id: int, limit: int = 10) -> list[dict]:
    """Obtiene las sesiones más recientes de un cliente."""
    
    async with db_manager.get_session() as db:
        result = await db.execute(
            select(InsuranceSession)
            .options(selectinload(InsuranceSession.vehicle))
            .where(InsuranceSession.client_id == client_id)
            .order_by(InsuranceSession.created_at.desc())
            .limit(limit)
        )
        sessions = result.scalars().all()
        
        return [
            {
                "slug": s.slug,
                "status": s.status.value,
                "is_owner": s.is_owner,
                "vehicle_plate": s.vehicle.license_plate,
                "created_at": s.created_at.isoformat()
            }
            for s in sessions
        ]


# ============================================================================
# EJEMPLO 7: Cancelar sesión
# ============================================================================

async def cancel_session(session_slug: str, reason: str = None) -> bool:
    """Cancela una sesión de seguro."""
    
    async with db_manager.get_session() as db:
        result = await db.execute(
            select(InsuranceSession).where(InsuranceSession.slug == session_slug)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            return False
        
        session.status = SessionStatus.CANCELLED
        await db.commit()
        
        print(f"✅ Sesión {session_slug} cancelada. Razón: {reason or 'No especificada'}")
        return True


# ============================================================================
# EJEMPLO 8: Estadísticas de sesiones
# ============================================================================

async def get_session_statistics() -> dict:
    """Obtiene estadísticas generales de sesiones."""
    from sqlalchemy import func
    
    async with db_manager.get_session() as db:
        # Contar por estado
        result = await db.execute(
            select(
                InsuranceSession.status,
                func.count(InsuranceSession.id).label("count")
            )
            .group_by(InsuranceSession.status)
        )
        
        stats = {row.status.value: row.count for row in result}
        
        # Total de sesiones
        total_result = await db.execute(
            select(func.count(InsuranceSession.id))
        )
        total = total_result.scalar()
        
        # Sesiones con propietario validado
        owner_result = await db.execute(
            select(func.count(InsuranceSession.id))
            .where(InsuranceSession.is_owner == True)
        )
        owner_count = owner_result.scalar()
        
        return {
            "total_sessions": total,
            "owner_validated": owner_count,
            "by_status": stats,
            "owner_percentage": round((owner_count / total * 100), 2) if total > 0 else 0
        }


# ============================================================================
# EJEMPLO DE USO EN ENDPOINT
# ============================================================================

"""
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.prequote import PreQuoteRequest, SessionResponse

router = APIRouter()

@router.post("/validate", response_model=SessionResponse)
async def validate_and_create_session(
    request: PreQuoteRequest,
    current_user: dict = Depends(get_current_user)
):
    # 1. Validar propietario (crea/obtiene client y vehicle)
    validation_result = await owner_validation_service.validate_owner(
        document_type_id=request.document_type_id,
        document_number=request.document_number,
        license_plate=request.license_plate
    )
    
    # 2. Crear sesión
    session_slug = await create_new_session(
        client_id=validation_result["client_id"],
        vehicle_id=validation_result["vehicle_id"]
    )
    
    # 3. Si hay datos de RUNT, actualizar sesión
    if validation_result.get("runt_available"):
        homologations = validation_result.get("vehicle_data", {}).get("homologations", [])
        
        await update_session_after_runt_validation(
            session_slug=session_slug,
            is_owner=validation_result["is_owner"],
            homologations=homologations
        )
    
    # 4. Retornar respuesta
    return SessionResponse(
        success=True,
        session_slug=session_slug,
        is_owner=validation_result["is_owner"],
        message=validation_result["message"]
    )


@router.get("/session/{slug}", response_model=SessionDetailResponse)
async def get_session(slug: str):
    session = await get_session_details(slug)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session


@router.patch("/session/{slug}/status")
async def update_status(slug: str, status: SessionStatus):
    success = await progress_session_status(slug, status)
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"success": True, "slug": slug, "new_status": status.value}
"""

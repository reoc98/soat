"""
Ejemplos de uso del Quote Service
"""

from app.services.quote import QuoteService
from app.models.insurance_session import InsuranceSession, SessionStatus
from app.models.vehicle_homologation import VehicleHomologation
from app.models.vehicle_homologation_selection import VehicleHomologationSelection
from app.database.session import db_manager
from sqlalchemy import select


# ============================================================================
# EJEMPLO 1: Crear una cotización
# ============================================================================

async def create_quote_example():
    """Ejemplo de creación de cotización."""
    
    quote_service = QuoteService(sponsor="rappi")
    
    try:
        result = await quote_service.create_quote(
            session_slug="550e8400-e29b-41d4-a716-446655440000",
            class_code="AUTO001"
        )
        
        print("✅ Cotización creada exitosamente:")
        print(f"  Session ID: {result['session_id']}")
        print(f"  Session Slug: {result['session_slug']}")
        print(f"  Homologation ID: {result['selected_homologation_id']}")
        print(f"  Class Code: {result['class_code']}")
        print(f"  Selection ID: {result['selection_id']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None


# ============================================================================
# EJEMPLO 2: Actualizar selección existente
# ============================================================================

async def update_quote_selection():
    """El usuario cambia de clase de vehículo."""
    
    quote_service = QuoteService(sponsor="rappi")
    session_slug = "550e8400-e29b-41d4-a716-446655440000"
    
    # Primera selección
    print("1. Seleccionando AUTO001...")
    result1 = await quote_service.create_quote(
        session_slug=session_slug,
        class_code="AUTO001"
    )
    print(f"  Selection ID: {result1['selection_id']}")
    print(f"  Homologation ID: {result1['selected_homologation_id']}")
    
    # Usuario cambia de opinión
    print("\n2. Cambiando a AUTO002...")
    result2 = await quote_service.create_quote(
        session_slug=session_slug,
        class_code="AUTO002"
    )
    print(f"  Selection ID: {result2['selection_id']}")  # Mismo ID
    print(f"  Homologation ID: {result2['selected_homologation_id']}")  # Diferente
    
    # Verificar que es el mismo registro actualizado
    assert result1['selection_id'] == result2['selection_id']
    print("\n✅ Selección actualizada correctamente (mismo registro)")


# ============================================================================
# EJEMPLO 3: Obtener selección actual
# ============================================================================

async def get_current_selection():
    """Obtener la homologación actualmente seleccionada."""
    
    quote_service = QuoteService(sponsor="rappi")
    
    selection = await quote_service.get_selected_homologation(
        session_slug="550e8400-e29b-41d4-a716-446655440000"
    )
    
    if selection:
        print("✅ Selección actual:")
        print(f"  Class Code: {selection['class_code']}")
        print(f"  Description: {selection['class_description']}")
        print(f"  Brand: {selection['brand_code']}")
        print(f"  Line: {selection['line_code']}")
        print(f"  Selected at: {selection['selected_at']}")
    else:
        print("ℹ️  No hay selección para esta sesión")
    
    return selection


# ============================================================================
# EJEMPLO 4: Listar homologaciones disponibles
# ============================================================================

async def list_available_homologations(session_slug: str):
    """Lista todas las opciones de clase de vehículo disponibles."""
    
    async with db_manager.get_async_session("dbr", "rappi") as session:
        # Obtener sesión
        stmt_session = select(InsuranceSession).where(
            InsuranceSession.slug == session_slug
        )
        result_session = await session.execute(stmt_session)
        insurance_session = result_session.scalars().first()
        
        if not insurance_session:
            print("❌ Sesión no encontrada")
            return []
        
        # Obtener homologaciones
        stmt = select(VehicleHomologation).where(
            VehicleHomologation.session_id == insurance_session.id
        )
        result = await session.execute(stmt)
        homologations = result.scalars().all()
        
        print(f"✅ {len(homologations)} homologación(es) disponible(s):\n")
        
        for i, h in enumerate(homologations, 1):
            print(f"{i}. Class Code: {h.class_code}")
            print(f"   Description: {h.class_description}")
            print(f"   Brand: {h.brand_code}")
            print(f"   Line: {h.line_code}")
            print(f"   Transport: {h.transport_type_code}")
            print(f"   Destination: {h.destination_code}")
            print()
        
        return homologations


# ============================================================================
# EJEMPLO 5: Flujo completo - Owner Validation → Quote
# ============================================================================

async def complete_flow_example():
    """Flujo completo desde validación hasta cotización."""
    
    from app.services.owner_validation import OwnerValidationService
    
    # Paso 1: Validar propietario
    print("1️⃣  VALIDANDO PROPIETARIO...")
    owner_service = OwnerValidationService(sponsor="rappi")
    
    validation_result = await owner_service.validate_owner(
        document_type_code=1,  # CC
        document_number="1234567890",
        license_plate="ABC123"
    )
    
    if not validation_result["is_owner"]:
        print("❌ No es propietario, no se puede cotizar")
        return None
    
    print(f"✅ Propietario validado - Session creada")
    
    # Obtener session_slug del resultado
    # (Asumiendo que owner_validation retorna el slug)
    session_slug = validation_result.get("session_slug")
    
    # Paso 2: Ver homologaciones disponibles
    print(f"\n2️⃣  HOMOLOGACIONES DISPONIBLES...")
    homologations = await list_available_homologations(session_slug)
    
    if not homologations:
        print("❌ No hay homologaciones disponibles")
        return None
    
    # Paso 3: Seleccionar primera homologación y cotizar
    print(f"\n3️⃣  CREANDO COTIZACIÓN...")
    selected_class = homologations[0].class_code
    
    quote_service = QuoteService(sponsor="rappi")
    quote_result = await quote_service.create_quote(
        session_slug=session_slug,
        class_code=selected_class
    )
    
    print(f"✅ Cotización creada con class_code: {selected_class}")
    
    # Paso 4: Verificar selección
    print(f"\n4️⃣  VERIFICANDO SELECCIÓN...")
    selection = await quote_service.get_selected_homologation(session_slug)
    
    print(f"✅ Selección confirmada:")
    print(f"   Class: {selection['class_code']}")
    print(f"   Description: {selection['class_description']}")
    
    return {
        "validation": validation_result,
        "quote": quote_result,
        "selection": selection
    }


# ============================================================================
# EJEMPLO 6: Manejo de errores
# ============================================================================

async def error_handling_examples():
    """Ejemplos de manejo de errores."""
    
    quote_service = QuoteService(sponsor="rappi")
    
    # Error 1: Sesión no encontrada
    print("1. Sesión no encontrada:")
    try:
        await quote_service.create_quote(
            session_slug="invalid-uuid",
            class_code="AUTO001"
        )
    except Exception as e:
        print(f"   ❌ {str(e)}\n")
    
    # Error 2: No es propietario
    print("2. No es propietario (is_owner=false):")
    try:
        # Crear sesión con is_owner=false para demostración
        # await quote_service.create_quote(...)
        print("   ❌ Cannot create quote: client is not the vehicle owner\n")
    except Exception as e:
        print(f"   ❌ {str(e)}\n")
    
    # Error 3: Status incorrecto
    print("3. Status incorrecto (no está en 'validated|quoted'):")
    try:
        # Sesión en status 'started'
        print("   ❌ Cannot create quote: session status must be 'validated|quoted', current status is 'started'\n")
    except Exception as e:
        print(f"   ❌ {str(e)}\n")
    
    # Error 4: class_code no existe
    print("4. class_code no existe para esta sesión:")
    try:
        await quote_service.create_quote(
            session_slug="550e8400-...",
            class_code="INVALID_CODE"
        )
    except Exception as e:
        print(f"   ❌ {str(e)}\n")


# ============================================================================
# EJEMPLO 7: Consultar estado de sesión después de cotizar
# ============================================================================

async def check_session_status_after_quote(session_slug: str):
    """Verificar que el status de la sesión cambió a QUOTED."""
    
    async with db_manager.get_async_session("dbr", "rappi") as session:
        stmt = select(InsuranceSession).where(
            InsuranceSession.slug == session_slug
        )
        result = await session.execute(stmt)
        insurance_session = result.scalars().first()
        
        if insurance_session:
            print(f"✅ Estado de sesión: {insurance_session.status.value}")
            print(f"   Is Owner: {insurance_session.is_owner}")
            print(f"   Session ID: {insurance_session.id}")
            print(f"   Client ID: {insurance_session.client_id}")
            print(f"   Vehicle ID: {insurance_session.vehicle_id}")
            
            return insurance_session
        else:
            print("❌ Sesión no encontrada")
            return None


# ============================================================================
# EJEMPLO 8: Estadísticas de cotizaciones
# ============================================================================

async def get_quote_statistics(sponsor: str):
    """Obtiene estadísticas de cotizaciones."""
    from sqlalchemy import func
    
    async with db_manager.get_async_session("dbr", sponsor) as session:
        # Total de selecciones
        total_stmt = select(func.count(VehicleHomologationSelection.id))
        total_result = await session.execute(total_stmt)
        total_quotes = total_result.scalar()
        
        # Selecciones por clase
        class_stmt = (
            select(
                VehicleHomologation.class_code,
                func.count(VehicleHomologationSelection.id).label("count")
            )
            .join(
                VehicleHomologationSelection,
                VehicleHomologation.id == VehicleHomologationSelection.vehicle_class_id
            )
            .group_by(VehicleHomologation.class_code)
        )
        class_result = await session.execute(class_stmt)
        
        print(f"📊 Estadísticas de Cotizaciones")
        print(f"Total de cotizaciones: {total_quotes}\n")
        print("Distribución por clase:")
        
        for row in class_result:
            print(f"  {row.class_code}: {row.count}")


# ============================================================================
# EJEMPLO DE USO EN ENDPOINT (FastAPI)
# ============================================================================

"""
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.quote import QuoteRequest, QuoteResponse

router = APIRouter()

@router.post("/create", response_model=QuoteResponse)
async def create_quote_endpoint(
    request: QuoteRequest,
    sponsor: str = Depends(get_sponsor)
):
    '''
    Crear cotización.
    
    Requirements:
    - Session debe existir
    - is_owner debe ser true
    - status debe ser validated
    - class_code debe existir en homologations
    '''
    try:
        quote_service = QuoteService(sponsor)
        
        result = await quote_service.create_quote(
            session_slug=request.session_id,
            class_code=request.class_code
        )
        
        return QuoteResponse(**result)
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating quote: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
"""


# ============================================================================
# MAIN - Ejecutar ejemplos
# ============================================================================

async def main():
    """Ejecutar todos los ejemplos."""
    
    print("="*70)
    print("EJEMPLOS DE QUOTE SERVICE")
    print("="*70 + "\n")
    
    # Ejemplo 1
    print("\n" + "="*70)
    print("EJEMPLO 1: Crear Cotización")
    print("="*70)
    await create_quote_example()
    
    # Ejemplo 2
    print("\n" + "="*70)
    print("EJEMPLO 2: Actualizar Selección")
    print("="*70)
    await update_quote_selection()
    
    # Ejemplo 3
    print("\n" + "="*70)
    print("EJEMPLO 3: Obtener Selección Actual")
    print("="*70)
    await get_current_selection()
    
    # Más ejemplos...


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

"""
Ejemplos Prácticos - Sistema de Logging Genérico

Este archivo contiene ejemplos completos y prácticos de cómo usar
el sistema de logging automático para diferentes escenarios.
"""

# =============================================================================
# EJEMPLO 1: Cliente REST API (JSON)
# =============================================================================

from app.services.external.base import ExternalServiceBase
from app.core.exceptions import ExternalServiceError
from typing import Dict, Any, Optional


class SuraInsuranceClient(ExternalServiceBase):
    """Cliente para API de Seguros SURA."""
    
    SERVICE_NAME = "SURA_INSURANCE"
    
    def __init__(self, sponsor_id: str):
        base_url = "https://api.sura.com"
        timeout = 30
        super().__init__(sponsor_id, base_url, timeout, enable_logging=True)
    
    async def get_quote(
        self,
        vehicle_plate: str,
        coverage_type: str,
        user_email: Optional[str] = None,
        client_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Obtener cotización de SURA.
        
        Request y response son automáticamente guardados en DynamoDB + MySQL.
        """
        metadata = {
            'user_email': user_email,
            'client_id': client_id,
            'license_plate': vehicle_plate
        }
        
        # Llamada automáticamente loggeada
        response = await self.post(
            "/api/v1/quotes",
            data={
                "plate": vehicle_plate,
                "coverage": coverage_type,
                "effective_date": "2024-01-15"
            },
            metadata=metadata
        )
        
        return response


# Uso:
async def example_sura_quote():
    client = SuraInsuranceClient(sponsor_id="sponsor1")
    
    quote = await client.get_quote(
        vehicle_plate="ABC123",
        coverage_type="full",
        user_email="agent@example.com",
        client_id=789
    )
    
    print(f"Quote ID: {quote['quote_id']}")
    print(f"Premium: {quote['premium']}")
    
    # Los siguientes datos ya están guardados automáticamente:
    # - DynamoDB: Request completo (headers, body) + Response completo
    # - MySQL: Metadata (service, endpoint, status, user, client, plate)


# =============================================================================
# EJEMPLO 2: Cliente SOAP API (XML)
# =============================================================================

class FasecoldasoapClient(ExternalServiceBase):
    """Cliente para API SOAP de Fasecolda."""
    
    SERVICE_NAME = "FASECOLDA_SOAP"
    
    def __init__(self, sponsor_id: str):
        super().__init__(sponsor_id, "https://soap.fasecolda.com", 20)
    
    async def validate_vehicle(
        self,
        license_plate: str,
        user_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validar vehículo en Fasecolda."""
        
        # Construir XML SOAP
        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Body>
                <ValidateVehicle xmlns="http://fasecolda.com/">
                    <Plate>{license_plate}</Plate>
                </ValidateVehicle>
            </soap:Body>
        </soap:Envelope>"""
        
        metadata = {
            'user_email': user_email,
            'license_plate': license_plate
        }
        
        # Enviar como string (automáticamente loggeado)
        response = await self.post(
            "/services/validation",
            data=soap_body,  # String se envía como-is
            headers={'Content-Type': 'text/xml'},
            metadata=metadata
        )
        
        # Response es parseado automáticamente (XML -> dict)
        # Y guardado en DynamoDB tanto raw como parsed
        return response


# Uso:
async def example_fasecolda_validation():
    client = FasecoldasoapClient(sponsor_id="sponsor1")
    
    result = await client.validate_vehicle(
        license_plate="XYZ789",
        user_email="agent@example.com"
    )
    
    print(f"Valid: {result['valid']}")
    
    # Guardado automáticamente:
    # - DynamoDB: body_raw (XML string) + body_parsed (dict)
    # - MySQL: Metadata con referencia


# =============================================================================
# EJEMPLO 3: Cliente con Autenticación
# =============================================================================

class BolivarAPIClient(ExternalServiceBase):
    """Cliente para API de Seguros Bolívar con autenticación."""
    
    SERVICE_NAME = "BOLIVAR_INSURANCE"
    
    def __init__(self, sponsor_id: str):
        super().__init__(sponsor_id, "https://api.bolivar.com", 30)
        self.access_token = None
    
    async def authenticate(self) -> str:
        """Obtener access token."""
        
        # Llamada de autenticación (también loggeada)
        response = await self.post(
            "/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.config['bolivar_client_id'],
                "client_secret": self.config['bolivar_client_secret']
            },
            metadata={'operation': 'authenticate'}
        )
        
        self.access_token = response['access_token']
        return self.access_token
    
    async def create_policy(
        self,
        quote_id: str,
        payment_method: str,
        user_email: Optional[str] = None,
        client_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Crear póliza."""
        
        # Asegurar autenticación
        if not self.access_token:
            await self.authenticate()
        
        metadata = {
            'user_email': user_email,
            'client_id': client_id,
            'quote_id': quote_id
        }
        
        # Llamada con token (sanitizado automáticamente en logs)
        response = await self.post(
            "/api/v1/policies",
            data={
                "quote_id": quote_id,
                "payment_method": payment_method
            },
            headers={
                "Authorization": f"Bearer {self.access_token}"
            },
            metadata=metadata
        )
        
        # Authorization header será "***REDACTED***" en logs
        return response


# Uso:
async def example_bolivar_policy():
    client = BolivarAPIClient(sponsor_id="sponsor1")
    
    policy = await client.create_policy(
        quote_id="Q12345",
        payment_method="credit_card",
        user_email="agent@example.com",
        client_id=456
    )
    
    print(f"Policy Number: {policy['policy_number']}")
    
    # Headers sensibles automáticamente sanitizados:
    # "Authorization": "***REDACTED***"


# =============================================================================
# EJEMPLO 4: Cliente con Retry y Error Handling
# =============================================================================

import asyncio


class RobustAPIClient(ExternalServiceBase):
    """Cliente con manejo robusto de errores."""
    
    SERVICE_NAME = "ROBUST_SERVICE"
    
    def __init__(self, sponsor_id: str):
        super().__init__(sponsor_id, "https://api.robust.com", 30)
    
    async def call_with_retry(
        self,
        endpoint: str,
        data: Dict[str, Any],
        max_retries: int = 3,
        user_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Llamar endpoint con reintentos."""
        
        for attempt in range(max_retries):
            try:
                metadata = {
                    'user_email': user_email,
                    'attempt': attempt + 1,
                    'max_retries': max_retries
                }
                
                response = await self.post(
                    endpoint,
                    data=data,
                    metadata=metadata
                )
                
                # Éxito - automáticamente loggeado
                return response
                
            except Exception as e:
                # Error - automáticamente loggeado con error_message
                
                if attempt < max_retries - 1:
                    # Esperar antes de reintentar
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    # Último intento falló
                    raise ExternalServiceError(
                        self.SERVICE_NAME,
                        f"Failed after {max_retries} attempts: {str(e)}"
                    )


# Uso:
async def example_retry():
    client = RobustAPIClient(sponsor_id="sponsor1")
    
    try:
        result = await client.call_with_retry(
            "/api/process",
            data={"action": "create"},
            max_retries=3,
            user_email="user@example.com"
        )
        print(f"Success: {result}")
    except ExternalServiceError as e:
        print(f"Failed: {e}")
    
    # Cada intento (exitoso o fallido) es loggeado por separado
    # Puedes ver el historial completo de reintentos en los logs


# =============================================================================
# EJEMPLO 5: Cliente con Metadata Extendido
# =============================================================================

class DetailedLoggingClient(ExternalServiceBase):
    """Cliente con metadata detallado para análisis."""
    
    SERVICE_NAME = "DETAILED_SERVICE"
    
    def __init__(self, sponsor_id: str):
        super().__init__(sponsor_id, "https://api.detailed.com", 30)
    
    async def process_transaction(
        self,
        transaction_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Procesar transacción con contexto completo."""
        
        # Metadata detallado para análisis posterior
        metadata = {
            'user_email': context.get('user_email'),
            'client_id': context.get('client_id'),
            'license_plate': transaction_data.get('vehicle_plate'),
            'document_number': transaction_data.get('client_doc'),
            # Campos adicionales (guardados en DynamoDB metadata)
            'session_id': context.get('session_id'),
            'ip_address': context.get('ip_address'),
            'user_agent': context.get('user_agent'),
            'referrer': context.get('referrer'),
            'transaction_type': transaction_data.get('type'),
            'amount': transaction_data.get('amount'),
            'currency': transaction_data.get('currency', 'COP')
        }
        
        response = await self.post(
            "/api/transactions",
            data=transaction_data,
            metadata=metadata
        )
        
        return response


# Uso:
async def example_detailed_logging():
    from fastapi import Request
    
    # En un endpoint FastAPI
    async def endpoint_handler(request: Request):
        client = DetailedLoggingClient(sponsor_id="sponsor1")
        
        context = {
            'user_email': request.state.user.email,
            'client_id': 123,
            'session_id': request.session.get('id'),
            'ip_address': request.client.host,
            'user_agent': request.headers.get('user-agent'),
            'referrer': request.headers.get('referer')
        }
        
        result = await client.process_transaction(
            transaction_data={
                'type': 'policy_purchase',
                'vehicle_plate': 'ABC123',
                'client_doc': '1234567890',
                'amount': 250000,
                'currency': 'COP'
            },
            context=context
        )
        
        return result
    
    # Todo el contexto queda guardado para análisis:
    # - ¿Qué usuarios generan más errores?
    # - ¿Qué IPs tienen problemas?
    # - ¿Qué tipo de transacciones fallan más?


# =============================================================================
# EJEMPLO 6: Consultar Logs
# =============================================================================

from app.services.external.external_response_manager import ExternalResponseManager
from datetime import datetime, timedelta


async def example_query_logs():
    """Ejemplos de consultas de logs."""
    
    manager = ExternalResponseManager(sponsor="sponsor1")
    
    # 1. Logs recientes de un servicio
    recent = await manager.get_recent_logs("RUNT", limit=10)
    
    print("=== Logs Recientes (MySQL - Rápido) ===")
    for log in recent:
        print(f"{log['created_at']}: {log['endpoint']}")
        print(f"  Status: {log['status']} ({log['status_code']})")
        print(f"  Time: {log['response_time_ms']}ms")
        print(f"  User: {log.get('user_email', 'N/A')}")
        print()
    
    # 2. Detalles completos de un log específico
    if recent:
        log_id = recent[0]['dynamodb_log_id']
        
        print("=== Detalles Completos (DynamoDB) ===")
        full_log = await manager.get_log_details(log_id)
        
        print(f"Request URL: {full_log['request_data']['url']}")
        print(f"Request Headers: {full_log['request_data']['headers']}")
        print(f"Request Body: {full_log['request_data']['body']}")
        print()
        print(f"Response Status: {full_log['response_data']['status_code']}")
        print(f"Response Headers: {full_log['response_data']['headers']}")
        print(f"Response Body: {full_log['response_data']['body']}")
        print()
        print(f"Metadata: {full_log.get('metadata', {})}")


# =============================================================================
# EJEMPLO 7: Análisis de Logs
# =============================================================================

from sqlalchemy import select, func
from app.models.external_log import ExternalServiceLog, RequestStatus
from app.database.session import db_manager


async def example_log_analysis(sponsor: str):
    """Análisis de logs usando MySQL."""
    
    async with db_manager.get_async_session("dbr", sponsor) as session:
        
        # 1. Tasa de error por servicio
        print("=== Tasa de Error por Servicio ===")
        stmt = select(
            ExternalServiceLog.service_name,
            func.count().label('total'),
            func.sum(
                func.if_(ExternalServiceLog.status == RequestStatus.ERROR, 1, 0)
            ).label('errors')
        ).group_by(ExternalServiceLog.service_name)
        
        result = await session.execute(stmt)
        
        for row in result:
            service, total, errors = row
            error_rate = (errors / total * 100) if total > 0 else 0
            print(f"{service}: {errors}/{total} ({error_rate:.2f}%)")
        
        print()
        
        # 2. Servicios más lentos (promedio)
        print("=== Tiempo Promedio por Servicio ===")
        stmt = select(
            ExternalServiceLog.service_name,
            func.avg(ExternalServiceLog.response_time_ms).label('avg_time'),
            func.max(ExternalServiceLog.response_time_ms).label('max_time')
        ).group_by(ExternalServiceLog.service_name)
        
        result = await session.execute(stmt)
        
        for row in result:
            service, avg_time, max_time = row
            print(f"{service}: Avg {avg_time:.0f}ms, Max {max_time}ms")
        
        print()
        
        # 3. Usuarios con más errores
        print("=== Usuarios con Más Errores ===")
        stmt = select(
            ExternalServiceLog.user_email,
            func.count().label('error_count')
        ).where(
            ExternalServiceLog.status == RequestStatus.ERROR,
            ExternalServiceLog.user_email.isnot(None)
        ).group_by(
            ExternalServiceLog.user_email
        ).order_by(
            func.count().desc()
        ).limit(10)
        
        result = await session.execute(stmt)
        
        for row in result:
            email, count = row
            print(f"{email}: {count} errors")


# =============================================================================
# EJEMPLO 8: Deshabilitar Logging Temporalmente
# =============================================================================

class SelectiveLoggingClient(ExternalServiceBase):
    """Cliente que puede deshabilitar logging para ciertas llamadas."""
    
    SERVICE_NAME = "SELECTIVE_SERVICE"
    
    def __init__(self, sponsor_id: str, enable_logging: bool = True):
        super().__init__(
            sponsor_id,
            "https://api.selective.com",
            30,
            enable_logging=enable_logging  # Control global
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check sin logging (llamada frecuente, no crítica)."""
        
        # Deshabilitar logging temporalmente
        original_logging = self.enable_logging
        self.enable_logging = False
        
        try:
            response = await self.get("/health")
            return response
        finally:
            self.enable_logging = original_logging
    
    async def critical_operation(
        self,
        data: Dict[str, Any],
        user_email: str
    ) -> Dict[str, Any]:
        """Operación crítica con logging garantizado."""
        
        # Asegurar que logging está habilitado
        self.enable_logging = True
        
        metadata = {'user_email': user_email}
        response = await self.post("/critical", data=data, metadata=metadata)
        
        return response


# =============================================================================
# Ejecutar Ejemplos
# =============================================================================

async def main():
    """Ejecutar todos los ejemplos."""
    
    print("=" * 80)
    print("EJEMPLOS DE SISTEMA DE LOGGING GENÉRICO")
    print("=" * 80)
    print()
    
    # Ejemplo 1: SURA Quote
    print("Ejemplo 1: SURA Insurance Quote")
    await example_sura_quote()
    print()
    
    # Ejemplo 2: Fasecolda SOAP
    print("Ejemplo 2: Fasecolda SOAP Validation")
    await example_fasecolda_validation()
    print()
    
    # Ejemplo 3: Bolívar con Auth
    print("Ejemplo 3: Bolívar Policy Creation")
    await example_bolivar_policy()
    print()
    
    # Ejemplo 4: Retry Logic
    print("Ejemplo 4: Robust API with Retry")
    await example_retry()
    print()
    
    # Ejemplo 6: Query Logs
    print("Ejemplo 6: Consultar Logs")
    await example_query_logs()
    print()
    
    # Ejemplo 7: Análisis
    print("Ejemplo 7: Análisis de Logs")
    await example_log_analysis("sponsor1")
    print()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

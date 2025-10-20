import time
import hmac
import hashlib
from base64 import b64decode, b64encode
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.aws.secrets import AWSSecretsManager
from app.core.exceptions import ExternalServiceError
from .base import ExternalServiceBase

logger = logging.getLogger(__name__)

class RCECoverage:
    """Cobertura dentro de un plan RCE."""
    def __init__(self, data: Dict[str, Any]):
        self.coverage_id = data.get("idCobertura")
        self.description = data.get("descripcionCobertura")
        self.limit = data.get("descripcionLimite")
        self.premium = float(data.get("impPrima", 0))
        self.total_premium = float(data.get("impPrimaTotal", 0))
        self.vat = float(data.get("impIva", 0))
        
        self.type = data.get("tipocobertura")
        self.active = data.get("snCheck") in ("true", "True", True)
    
    def to_dict(self):
        return {
            "coverage_id": self.coverage_id,
            "description": self.description,
            "limit": self.limit,
            "premium": self.premium,
            "total_premium": self.total_premium,
            "vat": self.vat,
            "type": self.type,
            "active": self.active
        }

class RCEPlan:
    """Plan dentro de la respuesta RCE."""
    def __init__(self, data: Dict[str, Any]):
        self.option_id = data.get("idOpcion")
        self.plan_id = data.get("id")
        self.description = data.get("descripcion")
        self.cod_ramo = data.get("codRamo")
        self.cod_tipo_poliza = data.get("codTipoPoliza")
        self.cod_clase_runt = data.get("codClaseRunt")
        self.group_code = data.get("codGrupo")
        self.sub_group_code = data.get("codSubGrupo")
        self.service_sm_code = data.get("codServicioSm")
        
        coberturas = data.get("coberturas", {}).get("CoberturasDetalleDto", [])
        if isinstance(coberturas, dict):
            coberturas = [coberturas]
        
        self.coverages = [RCECoverage(c) for c in coberturas]
        self.coverages = [c for c in self.coverages if c.active]

    def to_dict(self):
        return {
            "option_id": self.option_id,
            "plan_id": self.plan_id,
            "plan_name": self.description,
            "cod_ramo": self.cod_ramo,
            "cod_tipo_poliza": self.cod_tipo_poliza,
            "cod_clase_runt": self.cod_clase_runt,
            "group_code": self.group_code,
            "sub_group_code": self.sub_group_code,
            "service_sm_code": self.service_sm_code,
            "coverages": [c.to_dict() for c in self.coverages],
        }

class RCEQuoteResponse:
    """RCE quote response data class."""
    
    def __init__(self, xml_response: dict):
        """
        Parse SOAP XML response for RCE plans.
        
        Args:
            xml_response: SOAP XML response string
        """
        self.raw_xml = xml_response
        self.plans: List[RCEPlan] = []
        self._parse_response()
    
    def _parse_response(self):
        """Extract plan options."""
        try:
            if self.raw_xml is None:
                raise ExternalServiceError("RCE", "Respuesta RCE inválida o vacía")

            if not isinstance(self.raw_xml, dict):
                raise ExternalServiceError("RCE", "Respuesta RCE inválida o vacía")
            
            result = self.raw_xml.get('soap:Envelope', {}) \
                    .get('soap:Body', {}) \
                    .get('ConsultaVehiculoRCEHomologadoResponse', {}) \
                    .get('ConsultaVehiculoRCEHomologadoResult', {}) \
                    .get('tarifasRce', {})
            # Further parsing logic would go here
            if not result:
                logger.warning("No data found in RCE response")
                return {}
            
            self.success = result.get("procesadoExitoso") in ("true", "True", True)

            if not self.success:
                raise ExternalServiceError("RCE", "El servicio de RCE no procesó la solicitud exitosamente")
            
            if result.get("validaParaEmitir") == "false":
                raise ExternalServiceError("RCE", "Actualmente no se pueden emitir pólizas RCE para este vehículo") # No se recuperaron tarifas rc, no se puede emitir poliza
            
            # Extract relevant data from the result
            plans = result.get('planes', [])
            if not plans:
                logger.warning("No RCE plans found in response")
                return ExternalServiceError("RCE", "No se encontraron planes RCE disponibles")
            
            plans = plans.get('PlanDto', [])
            if isinstance(plans, dict):
                plans = [plans]  # Ensure it's a list
            
            for plan in plans:
                plan.update({
                    "codClaseRunt": result.get('codClaseRunt'),
                    "codGrupo": result.get('codGrupo'),
                    "codSubGrupo": result.get('codSubGrupo'),
                    "codServicioSm": result.get('codServicioSm'),
                })
                self.plans.append(RCEPlan(plan))

            logger.info(f"RCE plans parsed successfully - Total plans: {len(self.plans)}")
        except Exception as e:
            logger.error(f"Error parsing RCE response: {str(e)}", exc_info=True)
            raise
    
    def to_dict(self):
        return {
            "success": self.success,
            "total_plans": len(self.plans),
            "plans": [p.to_dict() for p in self.plans],
        }


class RCEClient(ExternalServiceBase):
    """Client for Mundial Seguros RCE (Responsabilidad Civil Extracontractual) API."""

    SERVICE_NAME = "RCE"  # Service name for logging

    def __init__(self, sponsor_id: str):
        """
        Initialize RCE client.

        Args:
            sponsor_id: Sponsor identifier
        """
        
        self.external_services = AWSSecretsManager().get_secret("external_services")
        self.sponsor_config = AWSSecretsManager().get_secret("config", sponsor_id)
        
        base_url = self.external_services.get("soat_base_url", "")
        timeout = int(self.external_services.get("soat_timeout", 15))
        
        super().__init__(sponsor_id, base_url, timeout, enable_logging=True)
    
    def _build_soap_request(
        self,
        license_plate: str,
        pos_code: str,
        rc_obligatory: bool = True,
    ) -> str:
        """
        Build SOAP XML request for AP plans.
        
        Args:
            license_plate: Vehicle license plate
            pos_code: Sales point code (punto de venta)
            rc_obligatory: Whether RC is obligatory
        Returns:
            SOAP XML request string
        """
        soap_request = f'''<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                <soap:Body>
                    <ConsultaVehiculoRCEHomologado xmlns="http://www.mundialseguros.com.co/">
                        <placa>{license_plate}</placa>
                        <puntoVta>{pos_code}</puntoVta>
                        <rcObligatorio>{rc_obligatory}</rcObligatorio>
                    </ConsultaVehiculoRCEHomologado>
                </soap:Body>
            </soap:Envelope>
        '''
        
        return soap_request
    
    async def get_plan_options(
        self,
        license_plate: Optional[str] = None,
        pos_code: Optional[str] = None,
        rc_obligatory: Optional[bool] = True
    ) -> tuple[RCEQuoteResponse, Dict[str, Any]]:
        """
        Get RCE insurance plan options from Mundial Seguros.

        Args:
            license_plate: Vehicle license plate
            pos_code: Sales point code (punto de venta)
            rc_obligatory: Whether RC is obligatory
            
        Returns:
            RCEQuoteResponse with parsed plan options,
            and log dictionary with request/response details
            
        Raises:
            ExternalServiceError: If the API call fails
        """
        # Use defaults from config if not provided
        pos_code = pos_code or self.sponsor_config.get('pos_code')
        rc_obligatory = 'true' if bool(self.sponsor_config.get('rc_obligatory', rc_obligatory)) else 'false'

        # Build SOAP request
        soap_body = self._build_soap_request(
            license_plate=license_plate,
            pos_code=pos_code,
            rc_obligatory=rc_obligatory
        )
        
        logger.info(
            f"Requesting RCE plan options - "
            f"License Plate: {license_plate}, Sales Point: {pos_code}, RC Obligatory: {rc_obligatory}"
        )
        result_log = None
        try:
            timestamp = int(time.time()) - (5 * 3600)  # UTC -5

            # Build headers with authentication
            auth = b64encode(f"{self.external_services['soat_username']}:{self.external_services['soat_password']}".encode('utf-8')).decode('utf-8')
            headers = {
                # 'Content-Type': 'application/xml',
                'Content-Type': 'text/xml; charset=utf-8',
                'X-MUN-CLIENT': self.sponsor_config['client_id'],
                'X-MUN-TIMESTAMP': str(timestamp),
                'X-MUN-SIGN': self._get_signature(license_plate, str(timestamp)),
                'Authorization': f"Basic {auth}"
            }
            
            # Prepare metadata for logging
            metadata = {
                'license_plate': license_plate,
                'pos_code': pos_code,
                'rc_obligatory': rc_obligatory
            }

            # Call RCE API (logging happens automatically in base class)
            result = await self.post(
                self.base_url,
                content=soap_body,
                headers=headers,
                params={'op': 'ConsultaVehiculoRCEHomologado'},
                metadata=metadata
            )
            
            response = result['response']
            result_log = result.get('log')
            # Parse response
            # quote_response = RCEQuoteResponse(response)
            
            logger.info("RCE plan options retrieved successfully - ")
            
            return response, result_log
        except Exception as e:
            logger.error(f"Error calling AP API: {str(e)}", exc_info=True)
            return None, result_log

    def _get_signature(self, license_plate: str, timestamp: str) -> str:
        """
        Generate HMAC signature for RUNT API authentication.
        
        Args:
            license_plate: Vehicle license plate
            timestamp: Current timestamp string
        Returns:
            Base64-encoded HMAC signature
        """
        message = f"{timestamp}.{self.sponsor_config['client_id']}.{license_plate}".encode('utf-8')
        key = b64decode(self.sponsor_config['client_secret'].encode('utf-8'))
        signature = hmac.new(key, message, hashlib.sha256).digest()
        return b64encode(signature).decode('utf-8')
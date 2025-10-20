"""
AP (Accidentes Personales) Insurance Client

Client for Mundial Seguros SOAP API for AP insurance plan options.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.aws.secrets import AWSSecretsManager
from app.core.exceptions import ValidationError, ExternalServiceError
from .base import ExternalServiceBase

logger = logging.getLogger(__name__)

def _safe_float(value: Any) -> float:
    """Convert safely to float, handling None, empty strings, etc."""
    try:
        if value in (None, '', ' ', 'None'):
            return 0.0
        return float(value)
    except (ValueError, TypeError):
        return 0.0

class APPlanOption:
    """AP plan option data class."""
    
    def __init__(self, plan_data: Dict[str, Any]):
        """
        Initialize AP plan option from parsed XML data.
        
        Args:
            plan_data: Dictionary with plan data from XML
        """
        self.option_id: Optional[int] = None
        self.code_type = str(plan_data.get('cod_tipo', '')).strip()
        self.desc_type = str(plan_data.get('desc_tipo', '')).strip()
        self.year_validity = str(plan_data.get('vigencia', '')).strip()

        self.prices = {
            "insured_value": _safe_float(plan_data.get('valor_aseg')),
            "policy_value": _safe_float(plan_data.get('valor_poliza')),
            "assistance_value": _safe_float(plan_data.get('valor_poliza_asistencia')),
        }
        self.availability = True
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert plan option to dictionary."""
        return {
            "option_id": self.option_id,
            "code_type": self.code_type,
            "desc_type": self.desc_type,
            "year_validity": self.year_validity,
            "prices": self.prices
        }


class APQuoteResponse:
    """AP quote response data class."""
    
    def __init__(self, xml_response: dict):
        """
        Parse SOAP XML response for AP plans.
        
        Args:
            xml_response: SOAP XML response string
        """
        self.raw_xml = xml_response
        self.plans: List[APPlanOption] = []
        self._parse_response()
    
    def _parse_response(self):
        """Extract plan options."""
        try:
            if self.raw_xml is None:
                raise ExternalServiceError("AP", "Respuesta AP inválida o vacía")
            
            if not isinstance(self.raw_xml, dict):
                raise ExternalServiceError("AP", "Respuesta AP inválida o vacía")

            result = self.raw_xml.get('soap:Envelope', {}) \
                    .get('soap:Body', {}) \
                    .get('ConsultarTiposPolizaAPResponse', {}) \
                    .get('ConsultarTiposPolizaAPResult', {}) \
                    .get('diffgr:diffgram', {}) \
                    .get('NewDataSet', {})
            # Further parsing logic would go here
            if not result:
                logger.warning("No data found in AP response")
                return {}
            
            # Extract relevant data from the result
            plans = result.get('Table', [])
            if isinstance(plans, dict):
                plans = [plans]  # Ensure it's a list
            
            for plan in plans:
                self.plans.append(APPlanOption(plan))
            
            logger.info(f"AP plans parsed successfully - Total plans: {len(self.plans)}")
            
        except Exception as e:
            logger.error(f"Error parsing AP response: {str(e)}", exc_info=True)
            raise

    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "plans": [plan.to_dict() for plan in self.plans],
            "total_plans": len(self.plans)
        }


class APClient(ExternalServiceBase):
    """Client for Mundial Seguros AP (Accidentes Personales) API."""
    
    SERVICE_NAME = "AP"  # Service name for logging
    
    def __init__(self, sponsor_id: str):
        """
        Initialize AP client.
        
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
        vigencia: int,
        cod_suc: str,
        cod_agente: str,
        cod_pto_vta: str
    ) -> str:
        """
        Build SOAP XML request for AP plans.
        
        Args:
            vigencia: Validity year (e.g., 2025)
            cod_suc: Branch code (sucursal)
            cod_agente: Agent code
            cod_pto_vta: Sales point code (punto de venta)
            
        Returns:
            SOAP XML request string
        """
        soap_request = f'''<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:mun="http://www.mundialseguros.com.co/">
                <soap:Header/>
                <soap:Body>
                    <mun:ConsultarTiposPolizaAP>
                        <mun:vigencia>{vigencia}</mun:vigencia>
                        <mun:codSuc>{cod_suc}</mun:codSuc>
                        <mun:codAgente>{cod_agente}</mun:codAgente>
                        <mun:codPtoVta>{cod_pto_vta}</mun:codPtoVta>
                    </mun:ConsultarTiposPolizaAP>
                </soap:Body>
            </soap:Envelope>
        '''
        
        return soap_request
    
    async def get_plan_options(
        self,
        vigencia: Optional[int] = None,
        cod_suc: Optional[str] = None,
        cod_agente: Optional[str] = None,
        cod_pto_vta: Optional[str] = None
    ) -> tuple[APQuoteResponse, Dict[str, Any]]:
        """
        Get AP insurance plan options from Mundial Seguros.
        
        Args:
            vigencia: Validity year (default: current year)
            cod_suc: Branch code (default: from config)
            cod_agente: Agent code (default: from config)
            cod_pto_vta: Sales point code (default: from config)
            
        Returns:
            APQuoteResponse with parsed plan options,
            and log dictionary with request/response details
            
        Raises:
            ExternalServiceError: If the API call fails
        """
        # Use defaults from config if not provided
        vigencia = vigencia or datetime.now().year
        cod_suc = cod_suc or int(self.sponsor_config.get('branch_code'))
        cod_agente = cod_agente or self.sponsor_config.get('intermediary_code')
        cod_pto_vta = cod_pto_vta or self.sponsor_config.get('pos_code')
        
        # Build SOAP request
        soap_body = self._build_soap_request(
            vigencia=vigencia,
            cod_suc=cod_suc,
            cod_agente=cod_agente,
            cod_pto_vta=cod_pto_vta
        )
        
        logger.info(
            f"Requesting AP plan options - "
            f"Vigencia: {vigencia}, Sucursal: {cod_suc}"
        )
        log_result = None
        try:
            # Prepare metadata for logging
            metadata = {
                'vigencia': vigencia,
                'cod_suc': cod_suc,
                'cod_agente': cod_agente,
                'cod_pto_vta': cod_pto_vta
            }
            
            # Call AP API (logging happens automatically in base class)
            result = await self.post(
                self.base_url,
                data=soap_body,
                headers={
                    "Content-Type": "application/soap+xml; charset=utf-8",
                    "SOAPAction": "http://www.mundialseguros.com.co/ConsultarTiposPolizaAP"
                },
                params={'op': 'ConsultarTiposPolizaAP'},
                metadata=metadata
            )
            
            response = result['response']
            log_result = result.get('log')
            # Parse response
            # quote_response = APQuoteResponse(response)
            
            logger.info("AP plan options retrieved successfully ")
            
            return response, log_result
            
        except Exception as e:
            logger.error(f"Error calling AP API: {str(e)}", exc_info=True)
            return None, log_result

    def _parse_ap_response(self, xml_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse the XML response from the AP API.

        Args:
            xml_data: The XML data as a dictionary

        Returns:
            Parsed response as a dictionary
        """
        result = xml_data.get('soap:Envelope', {}) \
                .get('soap:Body', {}) \
                .get('ConsultarTiposPolizaAPResponse', {}) \
                .get('ConsultarTiposPolizaAPResult', {}) \
                .get('diffgr:diffgram', {}) \
                .get('NewDataSet', {})
        # Further parsing logic would go here
        if not result:
            logger.warning("No data found in AP response")
            return {}
        
        # Extract relevant data from the result
        plans = result.get('Table', [])
        if isinstance(plans, dict):
            plans = [plans]  # Ensure it's a list
        parsed_plans = []
        for plan in plans:
            parsed_item = {
                "code_type": plan.get("cod_tipo"),
                "desc_type": plan.get("desc_tipo"),
                "year_validity": plan.get("vigencia"),
                "prices": {
                    "insured_value": float(plan.get("valor_aseg", 0)) if plan.get("valor_aseg") else 0.0,
                    "policy_value": float(plan.get("valor_poliza", 0)) if plan.get("valor_poliza") else 0.0,
                    "assistance_value": float(plan.get("valor_poliza_asistencia", 0)) if plan.get("valor_poliza_asistencia") else 0.0
                }
            }
            parsed_plans.append(parsed_item)

        return {"plans": parsed_plans}
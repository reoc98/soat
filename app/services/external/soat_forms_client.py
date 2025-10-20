"""
SOAT Forms Client

Handles communication with Mundial Seguros to retrieve available SOAT form numbers.
"""

import logging
from typing import Dict, Any, List
import xml.etree.ElementTree as ET

from app.services.external.base import ExternalServiceBase
from app.aws.secrets import AWSSecretsManager

logger = logging.getLogger(__name__)


class FormsResponse:
    """Response parser for available forms service."""
    
    def __init__(self, xml_response: str):
        """
        Parse forms response XML.
        
        Args:
            xml_response: XML response string from SOAP service
        """
        self.raw_xml = xml_response
        self.forms = []
        self.success = False
        self.error_message = None
        
        self._parse_response()
    
    def _parse_response(self):
        """Parse the XML response."""
        try:
            # Remove SOAP envelope
            result = self.raw_xml.get('soap:Envelope', {}) \
                    .get('soap:Body', {}) \
                    .get('consultarFormulariosDisponiblesResponse', {}) \
                    .get('consultarFormulariosDisponiblesResult', {}) \
                    .get('diffgr:diffgram', {}) \
                    .get('NewDataSet', {})

            # Further parsing logic would go here
            if not result:
                logger.warning("No data found in AP response")
                # self.success = False
                # self.error_message = "No se encontraron datos en la respuesta"
                return
            
            tables = result.get('Table') if result.get('Table') else []
            if not tables:
                logger.warning("No forms found in response")
                # self.success = False
                # self.error_message = "No se encontraron formularios disponibles"
                return
            
            tables = tables if isinstance(tables, list) else [tables]
            for table in tables:
                form_data = {
                    'cod_suc': table.get('cod_suc'),
                    'cod_agente': table.get('cod_agente'),
                    'cod_pto_vta': table.get('cod_pto_vta'),
                    'nro_formulario': table.get('nro_formulario')
                }
                
                # Only add if we have a form number
                if form_data['nro_formulario']:
                    self.forms.append(form_data)
            
            self.success = len(self.forms) > 0
            
            if not self.success:
                self.error_message = "No se encontraron formularios disponibles"
            
        except Exception as e:
            logger.error(f"Error parsing forms response: {str(e)}", exc_info=True)
            self.success = False
            self.error_message = f"Error al procesar respuesta: {str(e)}"
    
    def _parse_result_xml(self, result_xml: str):
        """Parse the inner result XML (diffgr:diffgram format)."""
        try:
            root = ET.fromstring(result_xml)
            
            # Check for errors
            error = root.find('.//error') or root.find('.//Error')
            if error is not None:
                self.success = False
                self.error_message = error.findtext('mensaje') or error.findtext('message')
                return
            
            # Find all Table elements (diffgr:diffgram format)
            # Namespace handling
            namespaces = {
                'diffgr': 'urn:schemas-microsoft-com:xml-diffgram-v1',
                'msdata': 'urn:schemas-microsoft-com:xml-msdata'
            }
            
            # Try with namespace
            tables = root.findall('.//diffgr:diffgram/DocumentElement/Table', namespaces)
            if not tables:
                # Try without namespace
                tables = root.findall('.//Table')
            
            if not tables:
                # Try NewDataSet format
                tables = root.findall('.//NewDataSet/Table')
            
            for table in tables:
                form_data = {
                    'cod_suc': table.findtext('.//cod_suc') or table.findtext('cod_suc'),
                    'cod_agente': table.findtext('.//cod_agente') or table.findtext('cod_agente'),
                    'cod_pto_vta': table.findtext('.//cod_pto_vta') or table.findtext('cod_pto_vta'),
                    'nro_formulario': table.findtext('.//nro_formulario') or table.findtext('nro_formulario')
                }
                
                # Only add if we have a form number
                if form_data['nro_formulario']:
                    self.forms.append(form_data)
            
            self.success = len(self.forms) > 0
            
            if not self.success:
                self.error_message = "No se encontraron formularios disponibles"
            
        except Exception as e:
            logger.error(f"Error parsing result XML: {str(e)}", exc_info=True)
            self.success = False
            self.error_message = f"Error al procesar XML de resultado: {str(e)}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "forms": self.forms,
            "total_forms": len(self.forms),
            "error_message": self.error_message
        }


class SoatFormsClient(ExternalServiceBase):
    """Client for SOAT forms services."""
    
    SERVICE_NAME = "SOAT_FORMS"
    
    def __init__(self, sponsor: str):
        """
        Initialize SOAT forms client.
        
        Args:
            sponsor: Sponsor identifier
        """
        self.external_services: Dict[str, Any] = AWSSecretsManager().get_secret("external_services")
        self.sponsor_config = AWSSecretsManager().get_secret("config", sponsor)
        base_url = self.external_services.get("soat_base_url", "")
        timeout = int(self.external_services.get("soat_timeout", 15))
        super().__init__(sponsor, base_url, timeout, enable_logging=True)
    
    def _build_soap_request(
        self,
        cod_suc: str,
        cod_agente: str,
        cod_pto_vta: str
    ) -> str:
        """
        Build SOAP request for available forms.
        
        Args:
            cod_suc: Sucursal code
            cod_agente: Agent code
            cod_pto_vta: Point of sale code
            
        Returns:
            Complete SOAP request
        """
        soap_request = f'''<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                <soap:Body>
                    <consultarFormulariosDisponibles xmlns="http://www.mundialseguros.com.co/">
                        <codSuc>{cod_suc}</codSuc>
                        <codAgente>{cod_agente}</codAgente>
                        <codPtoVta>{cod_pto_vta}</codPtoVta>
                    </consultarFormulariosDisponibles>
                </soap:Body>
            </soap:Envelope>
        '''
        
        return soap_request
    
    async def get_available_forms(self) -> FormsResponse:
        """
        Get available SOAT forms from Mundial Seguros.
        
        Returns:
            FormsResponse with list of available forms
        """
        
        # Build SOAP request
        soap_request = self._build_soap_request(
            cod_suc=self.sponsor_config['branch_code'],
            cod_agente=self.sponsor_config['intermediary_code'],
            cod_pto_vta=self.sponsor_config['pos_code']
        )
        
        # Make SOAP call
        result = await self.post(
            endpoint=self.base_url,
            content=soap_request,
            headers={
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': "http://www.mundialseguros.com.co/consultarFormulariosDisponibles"
            },
            params={'op': 'consultarFormulariosDisponibles'}
        )
        response = result['response']
        
        # Parse response
        return FormsResponse(response)

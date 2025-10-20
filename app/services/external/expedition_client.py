"""
Expedition Client for SOAT and AP

Handles pre-expedition (quote mode) and expedition (final issuance) for insurance policies.
Both SOAT and AP can be sent in a single SOAP request.
"""

from base64 import b64encode
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import xml.etree.ElementTree as ET

from app.core.exceptions import ExternalServiceError
from app.services.external.base import ExternalServiceBase
from app.aws.secrets import AWSSecretsManager

logger = logging.getLogger(__name__)


class ExpeditionResponse:
    """Response parser for expedition service."""
    
    def __init__(self, xml_response: str):
        """
        Parse expedition response XML.
        
        Args:
            xml_response: XML response string from SOAP service
        """
        self.raw_response = xml_response
        self.success = False
        self.message = ""
        self.error_code = None
        self.details = {}
        
        self._parse_response()
    
    def _parse_response(self):
        """Parse the XML response."""
        try:
            if self.raw_response is None:
                self.success = False
                self.message = "Respuesta vacía del servicio"
                raise ExternalServiceError("SOAT_EXPEDITION", self.message)
            
            if not isinstance(self.raw_response, dict):
                self.success = False
                self.message = "Respuesta inválida del servicio"
                raise ExternalServiceError("SOAT_EXPEDITION", self.message)
            
            result = self.raw_response.get('soap:Envelope', {}) \
                    .get('soap:Body', {}) \
                    .get('expedirPolizaXMLResponse', {}) \
                    .get('expedirPolizaXMLResult', {}) \
                    .get('diffgr:diffgram', {})
            
            if not result:
                logger.error("No data found in expedition response")
                self.success = False
                self.message = "No se encontraron datos en la respuesta"
                return
            
            dataset = result.get('NewDataSet', {})
            if not dataset:
                logger.error("No dataset found in expedition response")
                self.success = False
                self.message = "No se encontró el conjunto de datos en la respuesta"
                return
            
            response = dataset.get('respuesta', {})
            if not response:
                logger.error("No data found in expedition dataset")
                self.success = False
                self.message = "No se encontraron datos en el conjunto de datos"
                return
            
            if response.get('sn_procesado') == '0':
                self.success = False
                # self.message = response.get('txt_error', 'Error desconocido del servicio')
                # self.error_code = response.get('sn_procesado')
                self.message = 'Error desconocido del servicio SOAT'
                return

            self.success = True
            self.message = 'Póliza expedida exitosamente'
            # self.details = dataset
            
        except Exception as e:
            
            logger.error(f"Error parsing expedition response: {str(e)}", exc_info=True)
            self.success = False
            self.message = f"Error al procesar respuesta: {str(e)}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class RCEExpeditionResponse:
    """Response parser for RCE expedition service."""
    
    def __init__(self, xml_response: str):
        """
        Parse RCE expedition response XML.
        
        Args:
            xml_response: XML response string from SOAP service
        """
        self.raw_response = xml_response
        self.success = False
        self.message = ""
        self.error_code = None
        self.policy_number = None
        self.details = {}
        
        self._parse_response()
    
    def _parse_response(self):
        """Parse the RCE XML response."""
        try:
            if self.raw_response is None:
                self.success = False
                self.message = "Respuesta vacía del servicio RCE"
                raise ExternalServiceError("RCE_EXPEDITION", self.message)
            
            if not isinstance(self.raw_response, dict):
                self.success = False
                self.message = "Respuesta inválida del servicio RCE"
                raise ExternalServiceError("RCE_EXPEDITION", self.message)
            
            # Parse SOAP response for ExpedirPolizaRcYAp
            result = self.raw_response.get('soap:Envelope', {}) \
                    .get('soap:Body', {}) \
                    .get('ExpedirPolizaRcYApResponse', {}) \
                    .get('ExpedirPolizaRcYApResult', {})
            
            if not result:
                logger.error("No data found in RCE expedition response")
                self.success = False
                self.message = "No se encontraron datos en la respuesta RCE"
                return
            
            if result.get('procesadoExitoso') == 'false':
                self.success = False
                self.message = 'Error desconocido del servicio RCE'
                return
            
            if result.get('NewDataSet'):
                result = result.get('NewDataSet')
            
            response = result.get('respuesta', {})
            if isinstance(response, dict):
                # Check for error indicators
                if response.get('sn_procesado') == '0':
                    self.success = False
                    # self.message = result.get('error') or result.get('Error', 'Error desconocido del servicio RCE')
                    # self.error_code = result.get('codigo_error')
                    self.message = 'Error desconocido del servicio RCE'
                    return
                
                # Success case
                self.success = True
                self.message = 'Póliza RCE expedida exitosamente'
                # self.details = result
            else:
                self.success = False
                self.message = "Formato de respuesta RCE no reconocido"
            
        except Exception as e:
            logger.error(f"Error parsing RCE expedition response: {str(e)}", exc_info=True)
            self.success = False
            self.message = f"Error al procesar respuesta RCE: {str(e)}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "policy_number": self.policy_number,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class ExpeditionClient(ExternalServiceBase):
    """Client for expedition services (SOAT and AP)."""

    SERVICE_NAME = "SOAT_EXPEDITION"  # Define service name for logging

    def __init__(self, sponsor: str):
        """
        Initialize expedition client.
        
        Args:
            sponsor: Sponsor identifier
        """
        self.external_services: Dict[str, Any] = AWSSecretsManager().get_secret("external_services")
        self.sponsor_config = AWSSecretsManager().get_secret("config", sponsor)
        base_url = self.external_services.get("soat_base_url", "")
        timeout = int(self.external_services.get("soat_timeout", 15))
        super().__init__(sponsor, base_url, timeout, enable_logging=True)
    
    def _build_expedition_xml(
        self,
        session_data: Dict[str, Any],
        is_pre_expedition: bool = True
    ) -> str:
        """
        Build XML for expedition request.
        
        Args:
            session_data: Dictionary with all session information
            is_pre_expedition: True for pre-expedition (quote mode), False for final expedition
            
        Returns:
            XML string for SOAP request
        """
        
        # Base SOAT data
        soat_data = session_data.get('soat', {})
        client_data = session_data.get('client', {})
        vehicle_data = session_data.get('vehicle', {})
        config = session_data.get('config', {})
        
        xml_parts = [
            '<NewDataSet>',
            '    <Table>',
            f'        <cod_suc>{config.get("branch_code")}</cod_suc>',
            f'        <fec_emision>{soat_data.get("fec_emision")}</fec_emision>',
            '        <cod_grupo_endo>1</cod_grupo_endo>',
            f'        <fec_vig_desde>{soat_data.get("fec_vig_desde")}</fec_vig_desde>',
            f'        <fec_vig_hasta>{soat_data.get("fec_vig_hasta")}</fec_vig_hasta>',
            f'        <txt_apellido1>{client_data.get("txt_apellido1", "")}</txt_apellido1>',
            f'        <txt_apellido2>{client_data.get("txt_apellido2", "")}</txt_apellido2>',
            f'        <txt_nombre>{client_data.get("txt_nombre", "")}</txt_nombre>',
            f'        <cod_tipo_persona>{client_data.get("cod_tipo_persona")}</cod_tipo_persona>',
            f'        <cod_tipo_doc>{client_data.get("cod_tipo_doc")}</cod_tipo_doc>',
            f'        <nro_doc>{client_data.get("nro_doc")}</nro_doc>',
            f'        <cod_tipo_dir>{client_data.get("cod_tipo_dir", "1")}</cod_tipo_dir>', # Fixed to 1
            f'        <txt_direccion>{client_data.get("txt_direccion")}</txt_direccion>',
            f'        <cod_dpto>{client_data.get("cod_dpto")}</cod_dpto>',
            f'        <cod_municipio>{client_data.get("cod_municipio")}</cod_municipio>',
            f'        <cod_tipo_telef>{client_data.get("cod_tipo_telef", "8")}</cod_tipo_telef>', # 8 = Celular
            f'        <txt_telefono>{client_data.get("txt_telefono")}</txt_telefono>',
            f'        <imp_prima_total>{soat_data.get("imp_prima_total")}</imp_prima_total>',
            f'        <imp_gtos_emi>{soat_data.get("imp_gtos_emi")}</imp_gtos_emi>',
            f'        <imp_iva>{soat_data.get("imp_iva")}</imp_iva>',
            f'        <cod_usuario_solicitud>{config.get("user_code")}</cod_usuario_solicitud>',
            f'        <cod_marca_min_trans>{vehicle_data.get("cod_marca_min_trans")}</cod_marca_min_trans>',
            f'        <cod_modelo_min_trans>{vehicle_data.get("cod_modelo_min_trans")}</cod_modelo_min_trans>',
            f'        <cod_tipo_veh_min_trans>{vehicle_data.get("cod_tipo_veh_min_trans")}</cod_tipo_veh_min_trans>',
            f'        <aaaa_modelo>{vehicle_data.get("aaaa_modelo")}</aaaa_modelo>',
            f'        <txt_patente>{vehicle_data.get("txt_patente")}</txt_patente>',
            f'        <txt_motor>{vehicle_data.get("txt_motor")}</txt_motor>',
            f'        <txt_chasis>{vehicle_data.get("txt_chasis")}</txt_chasis>',
            f'        <cod_destino>{vehicle_data.get("cod_destino")}</cod_destino>',
            f'        <cnt_toneladas>{vehicle_data.get("cnt_toneladas", "0.00")}</cnt_toneladas>',
            f'        <cnt_ocupantes>{vehicle_data.get("cnt_ocupantes")}</cnt_ocupantes>',
            f'        <cnt_cc>{vehicle_data.get("cnt_cc")}</cnt_cc>',
            f'        <cod_pais_matricula>{vehicle_data.get("cod_pais_matricula", "1")}</cod_pais_matricula>',
            f'        <cod_clase_soat>{vehicle_data.get("cod_clase_soat")}</cod_clase_soat>',
            f'        <nro_asociado>{soat_data.get("rate")}</nro_asociado>',
            f'        <nro_formulario>{soat_data.get("nro_formulario")}</nro_formulario>',
            '        <cod_motivo></cod_motivo>',
            f'        <txt_marca>{vehicle_data.get("txt_marca")}</txt_marca>',
            f'        <txt_modelo>{vehicle_data.get("txt_modelo")}</txt_modelo>',
            f'        <imp_pagado>{soat_data.get("imp_pagado")}</imp_pagado>',
            f'        <fec_mov>{soat_data.get("fec_mov")}</fec_mov>',
            f'        <cod_tipo_agente>{soat_data.get("cod_tipo_agente", "4")}</cod_tipo_agente>',
            f'        <cod_agente>{config.get("agent_code")}</cod_agente>',
            f'        <cod_pto_vta>{config.get("pos_code")}</cod_pto_vta>',
            f'        <imp_tasa_runt>{soat_data.get("imp_tasa_runt")}</imp_tasa_runt>',
            f'        <txt_correo>{client_data.get("txt_correo")}</txt_correo>',
            f'        <txt_vin>{vehicle_data.get("txt_vin", "NA")}</txt_vin>',
        ]
        
        # Add AP data if present
        ap_data = session_data.get('ap')
        if ap_data:
            xml_parts.extend([
                '',
                f'        <ap_tipo_poliza>{ap_data.get("ap_tipo_poliza")}</ap_tipo_poliza>',
                f'        <ap_tomador>{ap_data.get("ap_tomador", "0")}</ap_tomador>',
                f'        <ap_txt_apellido1>{ap_data.get("ap_txt_apellido1")}</ap_txt_apellido1>',
                f'        <ap_txt_apellido2>{ap_data.get("ap_txt_apellido2")}</ap_txt_apellido2>',
                f'        <ap_txt_nombre>{ap_data.get("ap_txt_nombre")}</ap_txt_nombre>',
                f'        <ap_cod_tipo_persona>{ap_data.get("ap_cod_tipo_persona")}</ap_cod_tipo_persona>',
                f'        <ap_cod_tipo_doc>{ap_data.get("ap_cod_tipo_doc")}</ap_cod_tipo_doc>',
                f'        <ap_nro_doc>{ap_data.get("ap_nro_doc")}</ap_nro_doc>',
                f'        <ap_cod_tipo_dir>{ap_data.get("ap_cod_tipo_dir")}</ap_cod_tipo_dir>',
                f'        <ap_txt_direccion>{ap_data.get("ap_txt_direccion")}</ap_txt_direccion>',
                f'        <ap_cod_dpto>{ap_data.get("ap_cod_dpto")}</ap_cod_dpto>',
                f'        <ap_cod_municipio>{ap_data.get("ap_cod_municipio")}</ap_cod_municipio>',
                f'        <ap_pais>{ap_data.get("ap_pais", "1")}</ap_pais>',
                f'        <ap_txt_sexo>{ap_data.get("ap_txt_sexo")}</ap_txt_sexo>',
                f'        <ap_cod_tipo_telef>{ap_data.get("ap_cod_tipo_telef")}</ap_cod_tipo_telef>',
                f'        <ap_txt_telefono>{ap_data.get("ap_txt_telefono")}</ap_txt_telefono>',
                f'        <fec_naci>{ap_data.get("fec_naci")}</fec_naci>',
                f'        <ap_fec_emision>{ap_data.get("ap_fec_emision")}</ap_fec_emision>',
                f'        <ap_fec_vig_desde>{ap_data.get("ap_fec_vig_desde")}</ap_fec_vig_desde>',
                f'        <ap_fec_vig_hasta>{ap_data.get("ap_fec_vig_hasta")}</ap_fec_vig_hasta>',
                f'        <ap_valor_asegurado>{ap_data.get("ap_valor_asegurado")}</ap_valor_asegurado>',
                f'        <ap_valor_poliza>{ap_data.get("ap_valor_poliza")}</ap_valor_poliza>',
                f'        <ap_placa_asistencia>{ap_data.get("ap_placa_asistencia")}</ap_placa_asistencia>',
                f'        <ap_vigencia>{ap_data.get("ap_vigencia")}</ap_vigencia>',
            ])
        
        # Add cotizador flag
        xml_parts.extend([
            f'        <cotizador></cotizador>',
        ]) if is_pre_expedition else None
        
        xml_parts.extend([
            f'    </Table>',
            '</NewDataSet>'
        ])
        
        return '\n'.join(xml_parts)
    
    def _build_rce_json(
        self,
        session_data: Dict[str, Any],
        is_pre_expedition: bool = True
    ) -> Dict[str, Any]:
        """
        Build JSON data for RCE expedition request.
        
        Args:
            session_data: Dictionary with all session information
            is_pre_expedition: True for pre-expedition (quote mode), False for final expedition
            
        Returns:
            Dictionary with RCE data
        """
        
        rce_data = session_data.get('rce', {})
        client_data = session_data.get('client', {})
        vehicle_data = session_data.get('vehicle', {})
        config = session_data.get('config', {})
        
        json_data = {
            "nombre_sucursal": config.get("branch_name", "BOGOTÁ"),
            "cod_sucursal": config.get("branch_code"),
            "fecha_emision": rce_data.get("fecha_emision"),
            "cod_usuario": config.get("user_code", ""),
            "cod_agente": config.get("agent_code"),
            "cod_tipo_agente": rce_data.get("cod_tipo_agente", 4),
            "pto_vta": config.get("pos_code"),
            "Sn_cotizacion": is_pre_expedition,
            "polizaRc": {
                "nro_solicitud": rce_data.get("nro_solicitud", 0),
                "fec_expedicion": rce_data.get("fec_expedicion"),
                "fecha_vig_desde": rce_data.get("fecha_vig_desde"),
                "fecha_vig_hasta": rce_data.get("fecha_vig_hasta"),
                "placa": vehicle_data.get("txt_patente"),
                "cod_clase_vehiculo": vehicle_data.get("cod_clase_vehiculo", 1),
                "id_regla_rce": rce_data.get("id_regla_rce"),
                "imp_prima": rce_data.get("imp_prima"),
                "Pje_iva": None,
                "Imp_iva": rce_data.get("imp_iva"),
                "Imp_total": str(rce_data.get("imp_total")),
                "cod_fasecolda": vehicle_data.get("cod_fasecolda", ""),
                "cod_tipo_endo": rce_data.get("cod_tipo_endo", 8),
                "cod_grupo_endo": rce_data.get("cod_grupo_endo", 1),
                "cod_modelo": vehicle_data.get("aaaa_modelo"),
                "cod_usuario": config.get("user_code", ""),
                "cod_suc": config.get("branch_code"),
                "cod_pto_vta": config.get("pos_code"),
                "cod_tipo_agente": rce_data.get("cod_tipo_agente", 4),
                "cod_agente": config.get("agent_code"),
                "cod_tipo_agente_asociado": rce_data.get("cod_tipo_agente_asociado"),
                "cod_agente_asociado": rce_data.get("cod_agente_asociado"),
                "cod_grupo": rce_data.get("cod_grupo", 1),
                "cod_subgrupo": rce_data.get("cod_subgrupo", 1),
                "cod_servicio_sm": vehicle_data.get("cod_servicio_sm", 1),
                "id_plan": rce_data.get("id_plan"),
                "plan_seleccionado": rce_data.get("plan_seleccionado", {}),
                "info_tomador": {
                    "Cod_tipo_doc": client_data.get("cod_tipo_doc"),
                    "nro_doc": client_data.get("nro_doc"),
                    "txt_nombre": client_data.get("txt_nombre", ""),
                    "txt_Apellido1": client_data.get("txt_apellido1", ""),
                    "txt_sexo": client_data.get("txt_sexo", "M"),
                    "email": client_data.get("txt_correo"),
                    "celular": client_data.get("txt_telefono"),
                    "cod_dpto": client_data.get("cod_dpto"),
                    "cod_municipio": client_data.get("cod_municipio"),
                    "txt_direccion": client_data.get("txt_direccion"),
                    "cod_tipo_persona": client_data.get("cod_tipo_persona"),
                    "cod_tipo_empresa": client_data.get("cod_tipo_empresa", 1)
                }
            }
        }
        
        return json_data
    
    def _build_soap_request(self, xml_data: str) -> str:
        """
        Build SOAP envelope for expedition request.
        
        Args:
            xml_data: Inner XML data
            
        Returns:
            Complete SOAP request
        """
        # Escape XML for SOAP
        escaped_xml = xml_data.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        soap_request = f'''<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                <soap:Body>
                    <expedirPolizaXML xmlns="http://www.mundialseguros.com.co/">
                        <xmlFile>
            
            {escaped_xml}
            
            </xmlFile>
                    </expedirPolizaXML>
                </soap:Body>
            </soap:Envelope>
        '''
        
        return soap_request
    
    async def pre_expedite_policy(
        self,
        session_data: Dict[str, Any],
        is_pre_expedition: bool = True
    ) -> ExpeditionResponse:
        """
        Pre-expedite policy (quote mode issuance).
        
        This validates that a policy can be issued before going to payment gateway.
        
        Args:
            session_data: Complete session data including client, vehicle, SOAT, and optionally AP
            
        Returns:
            ExpeditionResponse with policy details
        """
        auth = b64encode(f"{self.external_services['soat_username']}:{self.external_services['soat_password']}".encode('utf-8')).decode('utf-8')
        headers = {
            # 'Content-Type': 'application/xml',
            'Content-Type': 'text/xml; charset=utf-8',
            # X-MUN-CLIENT': self.sponsor_config['client_id'],
            'Authorization': f"Basic {auth}"
        }
        # Build XML
        xml_data = self._build_expedition_xml(session_data, is_pre_expedition)
        soap_request = self._build_soap_request(xml_data)
        
        # Make SOAP call
        result = await self.post(
            endpoint=self.base_url,
            content=soap_request,
            headers=headers,
            params={'op': 'expedirPolizaXML'},
            metadata={'client_id': session_data['client']['id']}
        )
        response = result['response']
        log = result['log']
        # Parse response
        return ExpeditionResponse(response)
    
    async def expedite_policy(
        self,
        session_data: Dict[str, Any]
    ) -> ExpeditionResponse:
        """
        Expedite policy (final issuance after payment).
        
        Args:
            session_data: Complete session data including client, vehicle, SOAT, and optionally AP
            
        Returns:
            ExpeditionResponse with policy details
        """
        auth = b64encode(f"{self.external_services['soat_username']}:{self.external_services['soat_password']}".encode('utf-8')).decode('utf-8')
        headers = {
            # 'Content-Type': 'application/xml',
            'Content-Type': 'text/xml; charset=utf-8',
            # X-MUN-CLIENT': self.sponsor_config['client_id'],
            'Authorization': f"Basic {auth}"
        }
        # Build XML
        xml_data = self._build_expedition_xml(session_data, is_pre_expedition=False)
        soap_request = self._build_soap_request(xml_data)
        
        # Make SOAP call
        response = await self.post(
            endpoint_url=self.base_url,
            content=soap_request,
            headers=headers,
            params={'op': 'expedirPolizaXML'},
            metadata={'client_id': session_data['client']['id']}
        )
        
        # Parse response
        return ExpeditionResponse(response)
    

class ExpeditionRCEClient(ExternalServiceBase):
    
    SERVICE_NAME = "RCE_EXPEDITION"  # Define service name for logging

    def __init__(self, sponsor: str):
        """
        Initialize expedition client.
        
        Args:
            sponsor: Sponsor identifier
        """
        self.external_services: Dict[str, Any] = AWSSecretsManager().get_secret("external_services")
        self.sponsor_config = AWSSecretsManager().get_secret("config", sponsor)
        base_url = self.external_services.get("soat_base_url", "")
        timeout = int(self.external_services.get("soat_timeout", 15))
        super().__init__(sponsor, base_url, timeout, enable_logging=True)
    
    
    def _build_rce_soap_request(self, json_data: Dict[str, Any]) -> str:
        """
        Build SOAP envelope for RCE expedition request.
        
        Args:
            json_data: RCE JSON data
            
        Returns:
            Complete SOAP request for RCE
        """
        import json
        
        # Convert dict to JSON string
        json_string = json.dumps(json_data, ensure_ascii=False, indent=2)
        
        soap_request = f'''<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Body>
                <ExpedirPolizaRcYAp xmlns="http://www.mundialseguros.com.co/">
                <jsonData>{json_string}</jsonData>
                </ExpedirPolizaRcYAp>
            </soap:Body>
            </soap:Envelope>
        '''
        
        return soap_request
    
    
    async def pre_expedite_rce_policy(
        self,
        session_data: Dict[str, Any],
        is_pre_expedition: bool = True
    ) -> RCEExpeditionResponse:
        """
        Pre-expedite RCE policy (quote mode issuance).
        
        This validates that an RCE policy can be issued before going to payment gateway.
        Uses ExpedirPolizaRcYAp SOAP action with JSON data.
        
        Args:
            session_data: Complete session data including client, vehicle, and RCE
            
        Returns:
            RCEExpeditionResponse with policy details
        """
        auth = b64encode(f"{self.external_services['soat_username']}:{self.external_services['soat_password']}".encode('utf-8')).decode('utf-8')
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'Authorization': f"Basic {auth}"
        }
        
        session_data['rce']['Sn_cotizacion'] = is_pre_expedition
        json_data = session_data["rce"]
        soap_request = self._build_rce_soap_request(json_data)
        
        # Make SOAP call
        result = await self.post(
            endpoint=self.base_url,
            content=soap_request,
            headers=headers,
            params={'op': 'ExpedirPolizaRcYAp'},
            metadata={'client_id': session_data['client']['id']}
        )
        response = result['response']
        log = result['log']
        
        # Parse response
        return RCEExpeditionResponse(response)
import hmac
import hashlib
import time
from base64 import b64decode, b64encode
import logging
import traceback
from typing import Any, Dict, Optional
from .base import ExternalServiceBase
from app.aws.secrets import AWSSecretsManager
from app.core.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)


class RUNTClient(ExternalServiceBase):
    """Client for RUNT (Registro Único Nacional de Tránsito) API."""
    
    SERVICE_NAME = "RUNT"  # Define service name for logging

    def __init__(self, sponsor_id: str):
        self.external_services: Dict[str, Any] = AWSSecretsManager().get_secret("external_services")
        self.sponsor_config = AWSSecretsManager().get_secret("config", sponsor_id)
        base_url = self.external_services.get("soat_base_url", "")
        timeout = int(self.external_services.get("soat_timeout", 15))
        super().__init__(sponsor_id, base_url, timeout, enable_logging=True)

    async def get_vehicle_info(
        self, 
        license_plate: str
    ) -> Dict[str, Any]:
        """
        Query RUNT API to get vehicle and owner information.
        
        Args:
            license_plate: Vehicle license plate
            
        Returns:
            Dictionary with vehicle and owner information parsed from XML
            
        Raises:
            ExternalServiceError: If the API call fails
        """
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
            
            # Build SOAP body
            xml_body = f"""
                <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                    <soap:Body>
                        <ConsultarInfoVehiculoRuntDoc xmlns="http://www.mundialseguros.com.co/">
                            <placa>{license_plate}</placa>
                            <puntoVta>{self.sponsor_config['pos_code']}</puntoVta>
                        </ConsultarInfoVehiculoRuntDoc>
                    </soap:Body>
                </soap:Envelope>
            """.strip()
            
            # Prepare metadata for logging
            metadata = {
                'license_plate': license_plate,
                'pos_code': self.sponsor_config['pos_code']
            }
            
            # Call RUNT API (logging happens automatically in base class)
            logger.info(f"Querying RUNT for license plate: {license_plate}")
            result = await self.post(
                self.base_url, 
                content=xml_body,
                headers=headers, 
                params={'op': 'ConsultarInfoVehiculoRuntDoc'},
                metadata=metadata
            )
            response = result['response']
            
            # Parse XML response
            vehicle_data = self._parse_runt_response(response)
            
            logger.info(f"RUNT query successful for plate: {license_plate}")
            return vehicle_data
            
        except Exception as e:
            logger.error(f"RUNT API error for plate {license_plate}: {str(e)}")
            raise ExternalServiceError(
                "RUNT",
                f"Failed to query vehicle information: {str(e)}"
            )

    def _parse_runt_response(self, xml_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse RUNT XML response and extract relevant information.
        
        Args:
            xml_data: Parsed XML data as dictionary
            
        Returns:
            Dictionary with structured vehicle and owner information
        """
        try:
            # RUNT XML structure varies, adjust based on actual response
            # This is a generic parser, adapt to actual RUNT XML structure
            result = xml_data.get('soap:Envelope', {}) \
                .get('soap:Body', {}) \
                .get('ConsultarInfoVehiculoRuntDocResponse', {}) \
                .get('ConsultarInfoVehiculoRuntDocResult', {})
            
            if result.get('snConsultaRuntExitosa') != 'True':
                logger.warning(f"Consulta fallida RUNT: {result.get('observacionesServicio')}")
                return {}
            
            # Extract vehicle information
            vehicle_info = {
                "consultation_id": result.get("idConsulta"),
                "consultation_success": result.get("snConsultaRuntExitosa") == "True",
                "service_observation": result.get("observacionesServicio"),
                "service_type_id": result.get("idTipoServicio"),
                "service_type": result.get("tipoServicio"),
                "vehicle_class_id": result.get("idClaseVehiculo"),
                "vehicle_class": result.get("claseVehiculo"),
                "brand_id": result.get("idMarca"),
                "brand": result.get("marca"),
                "line_id": result.get("idLinea"),
                "line": result.get("linea"),
                "model_year": result.get("aaaa_modelo"),
                "color_id": result.get("idColor"),
                "color": result.get("color"),
                "serial_number": result.get("noSerie"),
                "engine_number": result.get("noMotor"),
                "chassis_number": result.get("noChasis"),
                "vin_number": result.get("noVin"),
                "engine_cc": result.get("cnt_cc"),
                "tonnage": result.get("cnt_toneladas"),
                "gross_weight": result.get("pesoBrutoVehicular"),
                "seats": result.get("cnt_ocupantes"),
                "body_type_id": result.get("idTipoCarroceria"),
                "body_type": result.get("tipoCarroceria"),
                "fuel_type_id": result.get("idTipoCombustible"),
                "fuel_type": result.get("tipoCombustible"),
                "vehicle_state": result.get("estadoDelVehiculo"),
                "transit_authority": result.get("organismoTransito"),
                "plate_number": result.get("noPlaca"),
            }
            
            # Homologations
            homologations_data = result.get("homologaciones", {})
            if homologations_data:
                homologations_data = homologations_data.get("HomologacionClaseMarcaLineaServicio")
            if not homologations_data:
                logger.warning("No homologations data found in RUNT response")
                return {}
            homologations = []
            if isinstance(homologations_data, dict):
                homologations_data = [homologations_data]
            for h in homologations_data:
                homologations.append({
                    "class_code": h["clase"]["codClase"],
                    "class_description": h["clase"]["txtDesc"],
                    "transport_type_code": h["clase"]["codTipoVehMinTrans"],
                    "brand_code": h["codMarcaSise"],
                    "line_code": h["codLineaSise"],
                    "destination_code": h["codDestinoSise"],
                })
            
            vehicle_info["homologations"] = homologations
            
            # Extract owner information
            owners_data = result.get("Propietarios", {})
            
            owners = []
            if owners_data:
                owners_data = owners_data.get("Propietario")
                if isinstance(owners_data, dict):
                    owners_data = [owners_data]
                
                for p in owners_data:
                    owners.append({
                        "document_type": p.get("tipoDocumento"),
                        "document_number": p.get("noDocumento"),
                        "full_name": p.get("nombreCompleto"),
                        "first_name": p.get("nombre"),
                        # "middle_name": p.get("nombre2"),
                        "last_name": p.get("apellido1"),
                        "second_last_name": p.get("apellido2"),
                    })
            
            return {
                "vehicle": vehicle_info,
                "owner": owners
            }
            
        except Exception as e:
            traceback.print_exc()
            logger.error(f"Error parsing RUNT response: {str(e)}")
            raise ExternalServiceError(
                "RUNT",
                f"Failed to parse RUNT response: {str(e)}"
            )

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
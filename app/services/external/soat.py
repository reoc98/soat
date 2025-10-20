from datetime import datetime, timedelta
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

class SOATQuoteResponse:
    """SOAT quote response data class."""

    def __init__(self, response_data: Dict[str, Any]):
        """
        Initialize SOAT quote response from parsed XML data.

        Args:
            response_data: Dictionary parsed from SOAP XML.
        """
        self.raw_xml = response_data
        self._parse_response()
    
    def _parse_response(self):
        """Extract plan options."""
        try:
            if self.raw_xml is None:
                raise ExternalServiceError("SOAT", "Respuesta SOAT inválida o vacía")
            
            if not isinstance(self.raw_xml, dict):
                raise ExternalServiceError("SOAT", "Respuesta SOAT inválida o vacía")
            
            result = self.raw_xml.get('soap:Envelope', {}) \
                    .get('soap:Body', {}) \
                    .get('CalcularPolizaResponse', {}) \
                    .get('CalcularPolizaResult', {})
            # Further parsing logic would go here
            if not result:
                logger.warning("No data found in AP response")
                return {}
            
            self.option_id = None
            self.discount_percentage: float = float(result.get("PjeDescuentoLey", 0))
            self.discount_amount: float = float(result.get("ImpDescuentoLey", 0))
            self.rate: float = float(result.get("Tarifa", 0))
            self.issue_date: str = result.get("FechaExpedicion", "")
            self.start_date: str = result.get("FechaInicioVigencia", "")
            self.end_date: str = result.get("FechaFinVigencia", "")
            self.premium_value: float = float(result.get("ValorPrima", 0))
            self.contribution_value: float = float(result.get("ValorContribucion", 0))
            self.runt_fee: float = float(result.get("ValorTasaRUNT", 0))
            self.discount_value: float = float(result.get("ValorDescuento", 0))
            self.policy_total_value: float = float(result.get("ValorTotalPoliza", 0))
            self.total_to_pay: float = float(result.get("ValorTotalPagar", 0))
            self.success: bool = str(result.get("ResultadoExito", "")).lower() == "true"
            self.days_validity: int = int(result.get("DiasVigencia", 0))
            self.fasecolda_status: Optional[int] = (
                int(result["codEstadoFecFasecolda"])
                if "codEstadoFecFasecolda" in result and result["codEstadoFecFasecolda"] not in (None, "")
                else None
            )
        except Exception as e:
            logger.error(f"Error parsing SOAT quote response: {str(e)}")
            traceback.print_exc()
            raise

    def to_dict(self) -> Dict[str, Any]:
        """Convert SOAT quote response to dictionary."""
        return {
            "option_id": self.option_id,
            "discount_percentage": self.discount_percentage,
            "discount_amount": self.discount_amount,
            "rate": self.rate,
            "issue_date": self.issue_date,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "premium_value": self.premium_value,
            "contribution_value": self.contribution_value,
            "runt_fee": self.runt_fee,
            "discount_value": self.discount_value,
            "policy_total_value": self.policy_total_value,
            "total_to_pay": self.total_to_pay,
            "success": self.success,
            "days_validity": self.days_validity,
            "fasecolda_status": self.fasecolda_status,
        }

class SOATClient(ExternalServiceBase):
    """Client for SOAT (Seguro Obligatorio de Accidentes de Tránsito) API."""

    SERVICE_NAME = "SOAT"  # Define service name for logging

    def __init__(self, sponsor_id: str):
        self.external_services: Dict[str, Any] = AWSSecretsManager().get_secret("external_services")
        self.sponsor_config = AWSSecretsManager().get_secret("config", sponsor_id)
        base_url = self.external_services.get("soat_base_url", "")
        timeout = int(self.external_services.get("soat_timeout", 15))
        super().__init__(sponsor_id, base_url, timeout, enable_logging=True)

    def _build_soap_request(
        self,
        class_code: str,
        cylinder_capacity: int,
        tonnage: float,
        model_year: int,
        seats: int,
        start_date: datetime,
        end_date: datetime,
        branch_code: str,
        agent_code: str,
        sales_point_code: str,
        license_plate: str,
        document_type_code: str,
        document_number: str
    ) -> str:
        """
        Build SOAP XML request.
        
        Args:
            class_code: Vehicle class code from homologation
            cylinder_capacity: Engine displacement in CC
            tonnage: Vehicle tonnage
            model_year: Vehicle model year
            seats: Number of passengers
            start_date: Policy start date
            end_date: Policy end date
            branch_code: Branch code (sucursal)
            agent_code: Agent code
            sales_point_code: Sales point code (punto de venta)
            license_plate: Vehicle license plate
            document_type_code: Client document type code
            document_number: Client document number
            
        Returns:
            SOAP XML request string
        """
        soap_request = f'''<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:mun="http://www.mundialseguros.com.co/">
                <soap:Header/>
                <soap:Body>
                    <mun:CalcularPoliza>
                        <mun:datosVehiculo>
                            <mun:Clase>{class_code}</mun:Clase>
                            <mun:Cilindraje>{cylinder_capacity}</mun:Cilindraje>
                            <mun:Capacidad>{tonnage:.2f}</mun:Capacidad>
                            <mun:Modelo>{model_year}</mun:Modelo>
                            <mun:Pasajeros>{seats}</mun:Pasajeros>
                            <mun:FechaInicioVigencia>{start_date}</mun:FechaInicioVigencia>
                            <mun:FechaFinVigencia>{end_date}</mun:FechaFinVigencia>
                            <mun:CodigoSucursal>{branch_code}</mun:CodigoSucursal>
                            <mun:CodigoAgente>{agent_code}</mun:CodigoAgente>
                            <mun:CodigoPuntoVenta>{sales_point_code}</mun:CodigoPuntoVenta>
                            <mun:Placa>{license_plate}</mun:Placa>
                            <mun:CodTipoDoc>{document_type_code}</mun:CodTipoDoc>
                            <mun:NroDoc>{document_number}</mun:NroDoc>
                        </mun:datosVehiculo>
                    </mun:CalcularPoliza>
                </soap:Body>
            </soap:Envelope>
        '''
        
        return soap_request
    
    async def calculate_quote(
        self,
        class_code: str,
        cylinder_capacity: int,
        tonnage: float,
        model_year: int,
        seats: int,
        license_plate: str,
        document_type_code: str,
        document_number: str,
    ) -> tuple[SOATQuoteResponse, Dict[str, Any]]:
        """
        Calculate SOAT insurance quote.
        
        Args:
            class_code: Vehicle class code
            cylinder_capacity: Engine displacement in CC
            tonnage: Vehicle tonnage
            model_year: Vehicle model year
            seats: Number of passengers
            license_plate: Vehicle license plate
            document_type_code: Client document type code
            document_number: Client document number
            
        Returns:
            SOATQuoteResponse with parsed quote data
            
        Raises:
            ValidationError: If quote calculation fails
        """
        # Calculate validity dates (tomorrow to 1 year from tomorrow)
        # start_date = datetime.now() + timedelta(days=1)
        # end_date = start_date + timedelta(days=364)  # 364 days = 1 year
        
        try:
            headers = {
                # "Content-Type": "application/soap+xml; charset=utf-8",
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://www.mundialseguros.com.co/CalcularPoliza"
            }

            xml_body = self._build_soap_request(
                class_code=class_code,
                cylinder_capacity=cylinder_capacity,
                tonnage=tonnage,
                model_year=model_year,
                seats=seats,
                start_date="?",
                end_date="?",
                branch_code=self.sponsor_config['branch_code'],
                agent_code=self.sponsor_config['intermediary_code'],
                sales_point_code=self.sponsor_config['pos_code'],
                license_plate=license_plate,
                document_type_code=document_type_code,
                document_number=document_number
            )
            
            metadata = {
                'license_plate': license_plate,
                'class_code': class_code,
            }
            
            logger.info(f"Sending SOAT quote request for license plate: {license_plate}")
            result = await self.post(
                self.base_url,
                content=xml_body,
                headers=headers,
                params={'op': 'CalcularPoliza'},
                metadata=metadata
            )
            print(f"result: {result}")
            response = result['response']
            
            return response, result.get('log')
            
        except Exception as e:
            logger.error(f"SOAT API error for plate {license_plate}: {str(e)}")
            raise ExternalServiceError(
                "SOAT",
                f"Ocurrió un error en el servicio de SOAT"
            )

    # TODO: 
    def _parse_soat_response(self, xml_data: Dict[str, Any]) -> Dict[str, Any]: pass

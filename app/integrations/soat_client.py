"""
SOAT Insurance Client

Client for Mundial Seguros SOAP API for SOAT insurance quotes.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import httpx

from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class SOATQuoteResponse:
    """SOAT quote response data class."""
    
    def __init__(self, xml_response: str):
        """
        Parse SOAP XML response.
        
        Args:
            xml_response: SOAP XML response string
        """
        self.raw_xml = xml_response
        self._parse_response()
    
    def _parse_response(self):
        """Parse XML response and extract data."""
        try:
            # Remove namespace prefixes for easier parsing
            xml_clean = self.raw_xml.replace('soap:', '').replace('xmlns:', 'ns_')
            
            root = ET.fromstring(xml_clean)
            
            # Find CalcularPolizaResult element
            result = root.find('.//{http://www.mundialseguros.com.co/}CalcularPolizaResult')
            
            if result is None:
                raise ValueError("CalcularPolizaResult not found in response")
            
            # Extract all fields
            self.success = self._get_bool(result, 'ResultadoExito')
            self.discount_percentage = self._get_float(result, 'PjeDescuentoLey')
            self.discount_amount = self._get_float(result, 'ImpDescuentoLey')
            self.rate = self._get_float(result, 'Tarifa')
            self.issue_date = self._get_date(result, 'FechaExpedicion')
            self.start_date = self._get_date(result, 'FechaInicioVigencia')
            self.end_date = self._get_date(result, 'FechaFinVigencia')
            self.premium = self._get_float(result, 'ValorPrima')
            self.contribution = self._get_float(result, 'ValorContribucion')
            self.runt_fee = self._get_float(result, 'ValorTasaRUNT')
            self.discount = self._get_float(result, 'ValorDescuento')
            self.total_policy = self._get_float(result, 'ValorTotalPoliza')
            self.total_to_pay = self._get_float(result, 'ValorTotalPagar')
            self.validity_days = self._get_int(result, 'DiasVigencia')
            self.fasecolda_status = self._get_int(result, 'codEstadoFecFasecolda')
            
            logger.info(f"SOAT quote parsed - Success: {self.success}, Total: {self.total_to_pay}")
            
        except ET.ParseError as e:
            logger.error(f"XML parsing error: {str(e)}")
            raise ValueError(f"Invalid XML response: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing SOAT response: {str(e)}")
            raise
    
    def _get_text(self, element: ET.Element, tag: str) -> Optional[str]:
        """Get text value from XML element."""
        child = element.find(f'.//{{{element.tag.split("}")[0].strip("{")}}}}{tag}')
        if child is None:
            child = element.find(f'.//{tag}')
        return child.text if child is not None else None
    
    def _get_float(self, element: ET.Element, tag: str) -> float:
        """Get float value from XML element."""
        text = self._get_text(element, tag)
        return float(text) if text else 0.0
    
    def _get_int(self, element: ET.Element, tag: str) -> int:
        """Get int value from XML element."""
        text = self._get_text(element, tag)
        return int(text) if text else 0
    
    def _get_bool(self, element: ET.Element, tag: str) -> bool:
        """Get bool value from XML element."""
        text = self._get_text(element, tag)
        return text.lower() == 'true' if text else False
    
    def _get_date(self, element: ET.Element, tag: str) -> Optional[datetime]:
        """Get date value from XML element (DD/MM/YYYY format)."""
        text = self._get_text(element, tag)
        if not text:
            return None
        try:
            return datetime.strptime(text, '%d/%m/%Y')
        except ValueError:
            logger.warning(f"Invalid date format for {tag}: {text}")
            return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "success": self.success,
            "discount_percentage": self.discount_percentage,
            "discount_amount": self.discount_amount,
            "rate": self.rate,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "premium": self.premium,
            "contribution": self.contribution,
            "runt_fee": self.runt_fee,
            "discount": self.discount,
            "total_policy": self.total_policy,
            "total_to_pay": self.total_to_pay,
            "validity_days": self.validity_days,
            "fasecolda_status": self.fasecolda_status
        }


class SOATClient:
    """Client for Mundial Seguros SOAT API."""
    
    def __init__(self, base_url: str, timeout: int = 30):
        """
        Initialize SOAT client.
        
        Args:
            base_url: Base URL for the SOAP API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.endpoint = f"{self.base_url}/?op=CalcularPoliza"
    
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
                <mun:FechaInicioVigencia>{start_date.strftime('%d/%m/%Y')}</mun:FechaInicioVigencia>
                <mun:FechaFinVigencia>{end_date.strftime('%d/%m/%Y')}</mun:FechaFinVigencia>
                <mun:CodigoSucursal>{branch_code}</mun:CodigoSucursal>
                <mun:CodigoAgente>{agent_code}</mun:CodigoAgente>
                <mun:CodigoPuntoVenta>{sales_point_code}</mun:CodigoPuntoVenta>
                <mun:Placa>{license_plate}</mun:Placa>
                <mun:CodTipoDoc>{document_type_code}</mun:CodTipoDoc>
                <mun:NroDoc>{document_number}</mun:NroDoc>
            </mun:datosVehiculo>
        </mun:CalcularPoliza>
    </soap:Body>
</soap:Envelope>'''
        
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
        branch_code: str = "14",
        agent_code: str = "1",
        sales_point_code: str = "41647"
    ) -> SOATQuoteResponse:
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
            branch_code: Branch code (default: "14")
            agent_code: Agent code (default: "1")
            sales_point_code: Sales point code (default: "41647")
            
        Returns:
            SOATQuoteResponse with parsed quote data
            
        Raises:
            ValidationError: If quote calculation fails
        """
        # Calculate validity dates (tomorrow to 1 year from tomorrow)
        start_date = datetime.now() + timedelta(days=1)
        end_date = start_date + timedelta(days=364)  # 364 days = 1 year
        
        # Build SOAP request
        soap_body = self._build_soap_request(
            class_code=class_code,
            cylinder_capacity=cylinder_capacity,
            tonnage=tonnage,
            model_year=model_year,
            seats=seats,
            start_date=start_date,
            end_date=end_date,
            branch_code=branch_code,
            agent_code=agent_code,
            sales_point_code=sales_point_code,
            license_plate=license_plate,
            document_type_code=document_type_code,
            document_number=document_number
        )
        
        logger.info(
            f"Requesting SOAT quote - Plate: {license_plate}, "
            f"Class: {class_code}, Model: {model_year}"
        )
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.endpoint,
                    content=soap_body,
                    headers={
                        "Content-Type": "application/soap+xml; charset=utf-8",
                        "SOAPAction": "http://www.mundialseguros.com.co/CalcularPoliza"
                    }
                )
                
                response.raise_for_status()
                
                logger.info(f"SOAT API response received - Status: {response.status_code}")
                
                # Parse response
                quote = SOATQuoteResponse(response.text)
                
                if not quote.success:
                    logger.error("SOAT quote calculation failed")
                    raise ValidationError("SOAT quote calculation failed")
                
                # Validate expiration date (must be within 2 months)
                if quote.end_date:
                    days_until_expiration = (quote.start_date - datetime.now()).days
                    if days_until_expiration > 60:  # More than 2 months
                        logger.warning(
                            f"SOAT policy too far from expiration - "
                            f"Days until expiration: {days_until_expiration}"
                        )
                        raise ValidationError("Todavia no puedes comprar tu SOAT por que falta mucho para su vencimiento")
                
                return quote
                
        except httpx.HTTPStatusError as e:
            logger.error(f"SOAT API HTTP error: {e.response.status_code} - {e.response.text}")
            raise ValidationError(f"SOAT service error: {e.response.status_code}")
        except httpx.TimeoutException:
            logger.error("SOAT API timeout")
            raise ValidationError("SOAT service timeout - please try again")
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error calling SOAT API: {str(e)}", exc_info=True)
            raise ValidationError(f"Error calculating SOAT quote: {str(e)}")

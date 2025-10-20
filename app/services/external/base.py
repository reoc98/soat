import asyncio
import logging
import httpx
import xmltodict
import time
import json
from typing import Any, Dict, Optional, Union
from app.aws.secrets import AWSSecretsManager

logger = logging.getLogger(__name__)

class ExternalServiceBase:
    """Clase base para consumir servicios externos (JSON, XML, texto plano) con logging automático."""
    BASE_URL: str = ""
    SERVICE_NAME: str = "UNKNOWN"  # Override in child classes

    def __init__(self, sponsor_id: str, base_url: Optional[str] = None, timeout: int = 15, enable_logging: bool = True):
        self.sponsor_id = sponsor_id
        self.client = httpx.Client(timeout=timeout)
        self.base_url = base_url
        self.enable_logging = enable_logging
        
        self._sync_client = httpx.Client(timeout=timeout)
        self._async_client = httpx.AsyncClient(timeout=timeout)
    
    def _is_async_context(self) -> bool:
        """Detecta si se está ejecutando dentro de un contexto async."""
        try:
            asyncio.get_running_loop()
            return True
        except RuntimeError:
            return False

    def _sanitize_headers(self, headers: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sanitize headers to remove sensitive information before logging.
        
        Args:
            headers: Original headers
            
        Returns:
            Sanitized headers
        """
        if not headers:
            return {}
        
        sanitized = headers.copy()
        sensitive_keys = [
            'authorization', 'x-api-key', 'api-key', 'apikey',
            'x-auth-token', 'auth-token', 'bearer', 'token',
            'password', 'secret', 'x-mun-sign'
        ]
        
        for key in list(sanitized.keys()):
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "***REDACTED***"
        
        return sanitized

    async def _log_request_response(
        self,
        http_method: str,
        url: str,
        request_headers: Optional[Dict[str, Any]],
        request_body: Any,
        request_params: Optional[Dict[str, Any]],
        response: Optional[httpx.Response],
        response_time_ms: int,
        error: Optional[Exception] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log complete request/response to hybrid storage.
        
        Args:
            http_method: HTTP method (GET, POST, etc.)
            url: Full URL called
            request_headers: Request headers
            request_body: Request body (can be dict, string, bytes)
            request_params: Query parameters
            response: HTTP response object
            response_time_ms: Response time in milliseconds
            error: Exception if request failed
            metadata: Additional metadata to log
        """
        if not self.enable_logging:
            return
        
        try:
            from .external_response_manager import log_external_service_call
            
            # Prepare request data
            request_data = {
                "url": url,
                "method": http_method,
                "headers": self._sanitize_headers(request_headers),
                "params": request_params or {},
            }
            
            # Add body based on type
            if request_body is not None:
                if isinstance(request_body, (dict, list)):
                    request_data["body"] = request_body
                elif isinstance(request_body, str):
                    # Try to parse as JSON, if fails keep as string
                    try:
                        request_data["body"] = json.loads(request_body)
                    except:
                        request_data["body"] = request_body
                elif isinstance(request_body, bytes):
                    try:
                        request_data["body"] = request_body.decode('utf-8')
                    except:
                        request_data["body"] = f"<binary data: {len(request_body)} bytes>"
                else:
                    request_data["body"] = str(request_body)
            
            # Prepare response data
            response_data = None
            status_code = None
            error_message = None
            
            if response is not None:
                status_code = response.status_code
                response_headers = dict(response.headers)
                
                response_data = {
                    "status_code": status_code,
                    "headers": response_headers,
                }
                
                # Capture raw response body
                try:
                    content_type = response.headers.get("content-type", "").lower()
                    
                    if "application/json" in content_type:
                        try:
                            response_data["body"] = response.json()
                        except:
                            response_data["body"] = response.text
                    elif "application/xml" in content_type or "text/xml" in content_type:
                        # Store both raw XML and parsed version
                        response_data["body_raw"] = response.text
                        try:
                            response_data["body_parsed"] = xmltodict.parse(response.text)
                        except:
                            pass
                    else:
                        # Store as text
                        response_data["body"] = response.text
                        
                except Exception as e:
                    logger.warning(f"Failed to capture response body: {str(e)}")
                    response_data["body"] = "<failed to capture>"
            
            if error:
                error_message = str(error)
                if hasattr(error, 'response') and error.response is not None:
                    status_code = error.response.status_code
                    try:
                        response_data = {
                            "status_code": status_code,
                            "headers": dict(error.response.headers),
                            "body": error.response.text
                        }
                    except:
                        pass
            
            # Merge metadata
            log_metadata = metadata or {}
            client_id = log_metadata.pop("client_id", None)
            # Call logging service
            logging_service = await log_external_service_call(
                sponsor_id=self.sponsor_id,
                service_name=self.SERVICE_NAME,
                endpoint=url,
                http_method=http_method,
                request_data=request_data,
                response_data=response_data,
                status_code=status_code,
                response_time_ms=response_time_ms,
                error_message=error_message,
                client_id=client_id,
                **log_metadata
            )
            return logging_service
            
        except Exception as e:
            # Don't let logging failures break the main flow
            logger.error(f"Failed to log external service call: {str(e)}", exc_info=True)

    def _build_url(self, endpoint: str) -> str:
        # return f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        return endpoint

    def _parse_response(self, response: httpx.Response) -> Union[Dict[str, Any], str]:
        """Detecta el tipo de contenido y lo convierte a dict si aplica."""
        content_type = response.headers.get("content-type", "").lower()

        # JSON
        if "application/json" in content_type:
            return response.json()

        # XML
        if content_type and any(ct in content_type for ct in ("application/xml", "text/xml", "application/soap+xml")):
            try:
                return xmltodict.parse(response.text)
            except Exception as e:
                logger.error(f"Error al parsear XML: {e}")
                raise

        # Texto plano u otros
        return response.text

    def _handle_response(self, response: httpx.Response) -> Union[Dict[str, Any], str]:
        try:
            response.raise_for_status()
            return self._parse_response(response)
        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP {response.status_code} - {response.text}")
            raise
        except Exception as e:
            logger.exception(f"Error procesando respuesta: {e}")
            raise
    
    async def _async_request(self, method: str, url: str, **kwargs):
        async with self._async_client as client:
            response = await client.request(method, url, **kwargs)
        return response

    def _sync_request(self, method: str, url: str, **kwargs):
        with self._sync_client as client:
            response = client.request(method, url, **kwargs)
        return response

    def _build_full_url(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        url = self._build_url(endpoint)
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{query}"
        return url
    
    async def _make_request(self, method: str, endpoint: str, **kwargs):
        """Detecta contexto y hace la request con el cliente adecuado."""
        url = self._build_url(endpoint)
        is_async = self._is_async_context()

        start_time = time.time()
        response = None
        error = None

        metadata = kwargs.pop("metadata", None)
        log = None
        
        try:
            if is_async:
                response = await self._async_request(method, url, **kwargs)
            else:
                response = self._sync_request(method, url, **kwargs)
            parsed = self._handle_response(response)
        except Exception as e:
            error = e
            raise
        finally:
            response_time_ms = int((time.time() - start_time) * 1000)
            log =await self._log_request_response(
                http_method=method,
                url=url,
                request_headers=kwargs.get("headers"),
                request_body=kwargs.get("json") or kwargs.get("content"),
                request_params=kwargs.get("params"),
                response=response,
                response_time_ms=response_time_ms,
                error=error,
                metadata=metadata
            )

        return {"response": parsed, "log": log}

    async def get(self, endpoint: str, **kwargs):
        return await self._make_request("GET", endpoint, **kwargs)

    async def post(self, endpoint: str, **kwargs):
        return await self._make_request("POST", endpoint, **kwargs)
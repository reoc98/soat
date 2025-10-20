import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

from app.aws.dynamodb import ExternalServiceLogStorage
from app.models.external_log import ExternalServiceLog, RequestStatus
from app.database.session import db_manager

logger = logging.getLogger(__name__)


class ExternalResponseManager:
    """
    Hybrid storage manager for external service logs.
    - DynamoDB: Stores complete request/response payloads
    - MySQL: Stores metadata and reference to DynamoDB entry
    """

    def __init__(self, sponsor: str):
        """
        Initialize the hybrid storage manager.
        
        Args:
            sponsor: Sponsor identifier
        """
        self.sponsor = sponsor
        self.dynamo_storage = ExternalServiceLogStorage(sponsor)
        self.dynamo_table_name = self.dynamo_storage.table_name

    async def log_external_call(
        self,
        service_name: str,
        endpoint: str,
        http_method: str,
        request_data: Dict[str, Any],
        response_data: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        client_id: Optional[int] = None,
        ttl_days: int = 90
    ) -> Dict[str, Any]:
        """
        Log an external service call to both DynamoDB and MySQL.
        
        This method stores:
        - Complete request/response in DynamoDB (with TTL)
        - Searchable metadata in MySQL with reference to DynamoDB
        
        Args:
            service_name: Name of the external service (e.g., "RUNT", "INSURANCE_PROVIDER")
            endpoint: API endpoint called (full URL)
            http_method: HTTP method (GET, POST, PUT, DELETE, etc.)
            request_data: Complete request data (headers, params, body)
            response_data: Complete response data (status, headers, body)
            status_code: HTTP status code
            response_time_ms: Response time in milliseconds
            error_message: Error message (if failed)
            client_id: Related client ID
            ttl_days: Days to retain in DynamoDB (default: 90)
            
        Returns:
            dynamodb_log_id: UUID of the log entry in DynamoDB
        """
        try:
            # Prepare metadata for DynamoDB
            metadata = {
                "client_id": client_id
            }
            
            # Step 1: Save full payload to DynamoDB
            dynamodb_log_id = self.dynamo_storage.save_log(
                service_name=service_name,
                endpoint=endpoint,
                http_method=http_method,
                request_data=request_data,
                response_data=response_data,
                status_code=status_code,
                response_time_ms=response_time_ms,
                error_message=error_message,
                metadata=metadata,
                ttl_days=ttl_days
            )
            
            # Determine status
            if error_message:
                status = RequestStatus.ERROR
            elif status_code and 200 <= status_code < 300:
                status = RequestStatus.SUCCESS
            elif status_code and status_code == 504:
                status = RequestStatus.TIMEOUT
            else:
                status = RequestStatus.ERROR
            
            # Step 2: Save reference to MySQL
            async with db_manager.get_async_session("dbw", self.sponsor) as session:
                mysql_log = ExternalServiceLog(
                    service_name=service_name,
                    endpoint=endpoint,
                    http_method=http_method,
                    status=status,
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    dynamodb_log_id=dynamodb_log_id,
                    client_id=client_id,
                    error_message=error_message[:1000] if error_message else None  # Truncate if too long
                )
                
                session.add(mysql_log)
                await session.commit()
                await session.refresh(mysql_log)
                
                logger.info(
                    f"External service log saved - "
                    f"Service: {service_name}, "
                    f"Endpoint: {endpoint}, "
                    f"Status: {status.value}, "
                    f"MySQL ID: {mysql_log.id}, "
                    f"DynamoDB ID: {dynamodb_log_id}"
                )
            
            return {
                "dynamo_id": dynamodb_log_id,
                "mysql_id": mysql_log.id
            }
            
        except Exception as e:
            logger.error(f"Failed to log external service call: {str(e)}", exc_info=True)
            # Don't raise - logging failures shouldn't break the main flow
            return {}

    async def get_log_details(self, dynamodb_log_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve complete log details from DynamoDB.
        
        Args:
            dynamodb_log_id: UUID of the log entry
            
        Returns:
            Complete log data including request/response payloads
        """
        try:
            log_data = self.dynamo_storage.get_log_by_id(dynamodb_log_id)
            return log_data
        except Exception as e:
            logger.error(f"Failed to retrieve log details: {str(e)}")
            return None

    async def get_recent_logs(
        self,
        service_name: str,
        limit: int = 50
    ) -> list:
        """
        Get recent logs for a service from MySQL (metadata only).
        
        Args:
            service_name: Name of the service
            limit: Maximum number of results
            
        Returns:
            List of log metadata from MySQL
        """
        try:
            from sqlalchemy import select
            
            async with db_manager.get_async_session("dbr", self.sponsor) as session:
                stmt = select(ExternalServiceLog).where(
                    ExternalServiceLog.service_name == service_name
                ).order_by(
                    ExternalServiceLog.created_at.desc()
                ).limit(limit)
                
                result = await session.execute(stmt)
                logs = result.scalars().all()
                
                return [
                    {
                        "id": log.id,
                        "service_name": log.service_name.value,
                        "endpoint": log.endpoint,
                        "status": log.status.value,
                        "status_code": log.status_code,
                        "response_time_ms": log.response_time_ms,
                        "dynamodb_log_id": log.dynamodb_log_id,
                        "created_at": log.created_at.isoformat(),
                    }
                    for log in logs
                ]
        except Exception as e:
            logger.error(f"Failed to retrieve recent logs: {str(e)}")
            return []

    @staticmethod
    def create_context_manager(sponsor: str):
        """
        Create a context-aware manager for logging external calls.
        
        Usage:
            manager = ExternalResponseManager.create_context_manager("rappi")
            await manager.log_external_call(...)
        """
        return ExternalResponseManager(sponsor)


# Helper function for easy usage
async def log_external_service_call(
    sponsor_id: str,
    service_name: str,
    endpoint: str,
    http_method: str,
    request_data: Dict[str, Any],
    response_data: Optional[Dict[str, Any]] = None,
    status_code: Optional[int] = None,
    response_time_ms: Optional[int] = None,
    error_message: Optional[str] = None,
    client_id: Optional[int] = None,
    **kwargs
) -> Optional[Dict[str, Any]]:
    """
    Convenience function to log an external service call.
    
    This function creates a manager and logs the complete request/response
    to both DynamoDB (full payload) and MySQL (searchable metadata).
    
    Args:
        sponsor_id: Sponsor identifier
        service_name: Name of the service (RUNT, INSURANCE_PROVIDER, etc.)
        endpoint: API endpoint (full URL)
        http_method: HTTP method (GET, POST, etc.)
        request_data: Complete request data (url, headers, params, body)
        response_data: Complete response data (status, headers, body)
        status_code: HTTP status code
        response_time_ms: Response time in milliseconds
        error_message: Error message if failed
        client_id: Related client ID
        **kwargs: Additional metadata (ignored, for backward compatibility)
        
    Returns:
        DynamoDB log ID (UUID) or None if logging failed
        MySQL log ID (int) or None if logging failed
    """
    manager = ExternalResponseManager(sponsor_id)
    return await manager.log_external_call(
        service_name=service_name,
        endpoint=endpoint,
        http_method=http_method,
        request_data=request_data,
        response_data=response_data,
        status_code=status_code,
        response_time_ms=response_time_ms,
        error_message=error_message,
        client_id=client_id
    )

# storage_dynamo.py
import json
import uuid
import boto3
import logging
from os import getenv
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class DynamoStorage:
    def __init__(self, table_name: str, sponsor: str = None):
        if sponsor:
            table_name = f"{getenv('AWS_STAGE')}_soat_{sponsor}_{table_name}"
        else:
            table_name = f"{getenv('AWS_STAGE')}_soat_{table_name}"
        self.table_name = table_name
        self.dynamo = boto3.resource("dynamodb", region_name=getenv("AWS_REGION"))
        self.table = self.dynamo.Table(table_name)

    def put_response(self, service_name: str, payload: Dict[str, Any], ttl_days: Optional[int] = None) -> str:
        """
        Guarda el payload en DynamoDB. Retorna el response_id (UUID).
        Schema recomendado:
            - PK: service_name#{service_name}
            - SK: response#{response_id}
        """
        response_id = str(uuid.uuid4())
        item = {
            "PK": f"service_name#{service_name}",
            "SK": f"response#{response_id}",
            "response_id": response_id,
            "service_name": str(service_name),
            "payload": payload,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

        if ttl_days:
            expire_ts = int((datetime.utcnow() + timedelta(days=ttl_days)).timestamp())
            item["ttl"] = expire_ts

        try:
            self.table.put_item(Item=item)
            return response_id
        except ClientError as e:
            raise

    def get_response(self, sponsor_id: int, response_id: str) -> Optional[Dict[str, Any]]:
        pk = f"sponsor#{sponsor_id}"
        sk = f"response#{response_id}"
        try:
            r = self.table.get_item(Key={"PK": pk, "SK": sk})
            return r.get("Item")
        except ClientError:
            raise

    def delete_response(self, sponsor_id: int, response_id: str):
        pk = f"sponsor#{sponsor_id}"
        sk = f"response#{response_id}"
        try:
            self.table.delete_item(Key={"PK": pk, "SK": sk})
        except ClientError:
            raise


class ExternalServiceLogStorage:
    """
    DynamoDB storage for external service logs (request/response payloads).
    Uses sponsor-specific tables for data isolation.
    """

    def __init__(self, sponsor: str):
        """
        Initialize DynamoDB storage for external service logs.
        
        Args:
            sponsor: Sponsor identifier for table naming
        """
        self.sponsor = sponsor
        # Table name format: {stage}_soat_{sponsor}_external_logs
        table_name = f"{getenv('AWS_STAGE', 'dev')}_soat_{sponsor}_external_logs"
        self.table_name = table_name
        
        try:
            self.dynamo = boto3.resource("dynamodb", region_name=getenv("AWS_REGION", "us-east-1"))
            self.table = self.dynamo.Table(table_name)
            logger.info(f"Connected to DynamoDB table: {table_name}")
        except Exception as e:
            logger.error(f"Failed to connect to DynamoDB table {table_name}: {str(e)}")
            raise

    def save_log(
        self,
        service_name: str,
        endpoint: str,
        http_method: str,
        request_data: Dict[str, Any],
        response_data: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ttl_days: int = 90
    ) -> str:
        """
        Save external service log to DynamoDB.
        
        Args:
            service_name: Name of the external service (e.g., "RUNT")
            endpoint: API endpoint called
            http_method: HTTP method used (GET, POST, etc.)
            request_data: Request payload/parameters
            response_data: Response payload (if successful)
            status_code: HTTP status code
            response_time_ms: Response time in milliseconds
            error_message: Error message (if failed)
            metadata: Additional metadata (user_email, client_id, etc.)
            ttl_days: Number of days to retain the log (default: 90 days)
            
        Returns:
            log_id: UUID of the created log entry
        """
        log_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        item = {
            # Partition Key: service_name#YYYY-MM (for query efficiency)
            "PK": f"service#{service_name}#{timestamp.strftime('%Y-%m')}",
            # Sort Key: timestamp#log_id
            "SK": f"{timestamp.isoformat()}#{log_id}",
            
            # Core fields
            "log_id": log_id,
            "service_name": service_name,
            "endpoint": endpoint,
            "http_method": http_method,
            "timestamp": timestamp.isoformat() + "Z",
            
            # Request/Response data
            "request": request_data,
            "response": response_data,
            
            # Status information
            "status_code": status_code,
            "response_time_ms": response_time_ms,
            "error_message": error_message,
            
            # Metadata
            "metadata": metadata or {},
            "sponsor": self.sponsor,
        }
        
        # Add TTL if specified
        if ttl_days:
            expire_ts = int((timestamp + timedelta(days=ttl_days)).timestamp())
            item["ttl"] = expire_ts
        
        try:
            self.table.put_item(Item=item)
            logger.info(
                f"Saved external service log - "
                f"Service: {service_name}, Log ID: {log_id}, "
                f"Status: {status_code}, Response Time: {response_time_ms}ms"
            )
            return log_id
        except ClientError as e:
            logger.error(f"Failed to save log to DynamoDB: {str(e)}")
            raise

    def get_log(self, service_name: str, year_month: str, timestamp_log_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific log entry.
        
        Args:
            service_name: Name of the service
            year_month: Year-month in format YYYY-MM
            timestamp_log_id: Combined timestamp and log_id (SK value)
            
        Returns:
            Log entry or None if not found
        """
        pk = f"service#{service_name}#{year_month}"
        sk = timestamp_log_id
        
        try:
            response = self.table.get_item(Key={"PK": pk, "SK": sk})
            return response.get("Item")
        except ClientError as e:
            logger.error(f"Failed to retrieve log from DynamoDB: {str(e)}")
            return None

    def get_log_by_id(self, log_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a log by its UUID (requires scanning - use sparingly).
        
        Args:
            log_id: UUID of the log entry
            
        Returns:
            Log entry or None if not found
        """
        try:
            response = self.table.scan(
                FilterExpression="log_id = :log_id",
                ExpressionAttributeValues={":log_id": log_id},
                Limit=1
            )
            items = response.get("Items", [])
            return items[0] if items else None
        except ClientError as e:
            logger.error(f"Failed to retrieve log by ID from DynamoDB: {str(e)}")
            return None

    def query_logs(
        self,
        service_name: str,
        year_month: str,
        limit: int = 100,
        start_timestamp: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query logs for a specific service and month.
        
        Args:
            service_name: Name of the service
            year_month: Year-month in format YYYY-MM
            limit: Maximum number of results
            start_timestamp: Optional start timestamp for pagination
            
        Returns:
            List of log entries
        """
        pk = f"service#{service_name}#{year_month}"
        
        try:
            query_params = {
                "KeyConditionExpression": "PK = :pk",
                "ExpressionAttributeValues": {":pk": pk},
                "Limit": limit,
                "ScanIndexForward": False  # Most recent first
            }
            
            if start_timestamp:
                query_params["ExclusiveStartKey"] = {
                    "PK": pk,
                    "SK": start_timestamp
                }
            
            response = self.table.query(**query_params)
            return response.get("Items", [])
        except ClientError as e:
            logger.error(f"Failed to query logs from DynamoDB: {str(e)}")
            return []

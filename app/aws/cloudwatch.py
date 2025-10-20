import logging
from typing import Optional, Dict, Any, List
import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)

class AWSCloudWatchClient:
    """AWS CloudWatch client for logging and monitoring."""

    def __init__(self):
        self._logs_client = None
        self._metrics_client = None

    def _get_logs_client(self):
        """Get or create CloudWatch Logs client."""
        if self._logs_client is None:
            self._logs_client = boto3.client(
                'logs',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
        return self._logs_client

    def _get_metrics_client(self):
        """Get or create CloudWatch Metrics client."""
        if self._metrics_client is None:
            self._metrics_client = boto3.client(
                'cloudwatch',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
        return self._metrics_client

    def put_metric_data(self, namespace: str, metric_name: str, value: float,
                       dimensions: Optional[List[Dict[str, str]]] = None,
                       unit: str = 'Count'):
        """Put custom metric data to CloudWatch."""
        try:
            client = self._get_metrics_client()
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit
            }
            if dimensions:
                metric_data['Dimensions'] = dimensions

            client.put_metric_data(
                Namespace=namespace,
                MetricData=[metric_data]
            )
        except ClientError as e:
            logger.error(f"Error putting metric data: {e}")

    def create_log_group(self, log_group_name: str) -> bool:
        """Create a CloudWatch log group."""
        try:
            client = self._get_logs_client()
            client.create_log_group(logGroupName=log_group_name)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                logger.error(f"Error creating log group {log_group_name}: {e}")
            return False

# Global instance
cloudwatch_client = AWSCloudWatchClient()
import logging
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError
from os import getenv
import json

logger = logging.getLogger(__name__)

class AWSSecretsManager:
    """AWS Secrets Manager client for retrieving secrets."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        """Get or create boto3 client."""
        if self._client is None:
            self._client = boto3.client(
                'secretsmanager',
                region_name=getenv("AWS_REGION"),
            )
        return self._client

    def get_secret(self, name: str, sponsor: str = None) -> Optional[Dict[str, Any]]:
        """Fetch secret from AWS Secrets Manager.
        
        Args:
            name: Secret name (e.g., 'dbr', 'dbw', 'api_key')
            sponsor: Sponsor name (e.g., 'rappi')
            
        Returns:
            Parsed JSON secret value or None
        """
        
        if sponsor:
            secret_name = f"{getenv('AWS_STAGE')}/soat_{sponsor}/{name}"
        else:
            secret_name = f"{getenv('AWS_STAGE')}/soat/{name}"
        
        try:
            client = self._get_client()
            if not client:
                return None

            response = client.get_secret_value(SecretId=secret_name)
            secret_string = response.get('SecretString')
            if secret_string:
                return json.loads(secret_string)
            return None
        except ClientError as e:
            logger.error(f"Error fetching secret {secret_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching secret {secret_name}: {e}")
            return None
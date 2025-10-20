import logging
from typing import Optional, Dict, Any, BinaryIO
import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)

class AWSS3Client:
    """AWS S3 client for file storage operations."""

    def __init__(self):
        self._client = None
        self._resource = None

    def _get_client(self):
        """Get or create boto3 S3 client."""
        if self._client is None:
            self._client = boto3.client(
                's3',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
        return self._client

    def _get_resource(self):
        """Get or create boto3 S3 resource."""
        if self._resource is None:
            self._resource = boto3.resource(
                's3',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
        return self._resource

    def upload_file(self, file_obj: BinaryIO, bucket: str, key: str,
                   content_type: Optional[str] = None,
                   metadata: Optional[Dict[str, str]] = None) -> bool:
        """Upload a file to S3 bucket."""
        try:
            client = self._get_client()
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            if metadata:
                extra_args['Metadata'] = metadata

            client.upload_fileobj(file_obj, bucket, key, ExtraArgs=extra_args)
            return True
        except ClientError as e:
            logger.error(f"Error uploading file to S3 {bucket}/{key}: {e}")
            return False

    def download_file(self, bucket: str, key: str, file_obj: BinaryIO) -> bool:
        """Download a file from S3 bucket."""
        try:
            client = self._get_client()
            client.download_fileobj(bucket, key, file_obj)
            return True
        except ClientError as e:
            logger.error(f"Error downloading file from S3 {bucket}/{key}: {e}")
            return False

    def delete_file(self, bucket: str, key: str) -> bool:
        """Delete a file from S3 bucket."""
        try:
            client = self._get_client()
            client.delete_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            logger.error(f"Error deleting file from S3 {bucket}/{key}: {e}")
            return False

    def get_presigned_url(self, bucket: str, key: str, expiration: int = 3600) -> Optional[str]:
        """Generate a presigned URL for S3 object."""
        try:
            client = self._get_client()
            url = client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned URL for {bucket}/{key}: {e}")
            return None

    def list_files(self, bucket: str, prefix: Optional[str] = None) -> list:
        """List files in S3 bucket with optional prefix."""
        try:
            client = self._get_client()
            paginator = client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix or "")

            files = []
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        files.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified']
                        })
            return files
        except ClientError as e:
            logger.error(f"Error listing files in S3 bucket {bucket}: {e}")
            return []

# Global instance
s3_client = AWSS3Client()
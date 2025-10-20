# AWS services module
from .cognito import cognito_client
from .cloudwatch import cloudwatch_client
from .s3 import s3_client

__all__ = ['cognito_client', 'cloudwatch_client', 's3_client']
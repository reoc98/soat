from os import getenv
from fastapi import APIRouter, Depends
from app.aws.secrets import AWSSecretsManager

router = APIRouter()

@router.get("/", response_model=dict, summary="Health Check")
async def health_check():
    """Health check endpoint."""
    secrets = AWSSecretsManager().get_secret("dbr")
    return {"status": "ok", "environment": getenv("AWS_STAGE"), "secrets": secrets}
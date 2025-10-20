from typing import Annotated, Optional
import logging

from fastapi import APIRouter, Depends, Request, status
from app.api.v1.endpoints import auth, health, owner_validation, quote, soat_forms, expedition, session_info, catalog

router = APIRouter()

# Include subrouters
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(health.router, prefix="/health", tags=["Health"])
router.include_router(catalog.router, prefix="/catalogs", tags=["Catalogs"])
router.include_router(session_info.router, prefix="/session", tags=["Session Information"])
router.include_router(owner_validation.router, prefix="/owner-validation", tags=["Owner Validation"])
router.include_router(quote.router, prefix="/quote", tags=["Quote"])
router.include_router(expedition.router, prefix="/expedition", tags=["Expedition"])
router.include_router(soat_forms.router, prefix="/soat-forms", tags=["SOAT Forms"])
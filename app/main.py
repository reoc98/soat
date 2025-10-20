import logging
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.exceptions import (
    AppException,
    TenantNotFoundError,
    AuthenticationError,
    ValidationError,
)
from app.api.v1.routes import router as v1_router
from app.database.session import db_manager
# from app.middleware.tenant import TenantMiddleware
from app.middleware.auth import AuthMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # Startup
    logger.info("Starting FastAPI application")
    try:
        await db_manager.initialize()
        # Start background cleanup for expired connections
        await db_manager.start_background_cleanup(interval=300)  # 5 minutes
        logger.info("Database initialization and background cleanup started")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down FastAPI application")
    try:
        await db_manager.close_all()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {str(e)}")


def create_app() -> FastAPI:
    """Factory function to create and configure FastAPI application."""
    
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/api/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    setup_logging()

    # CORS Configuration
    if settings.ENVIRONMENT != "production":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Custom Middleware (Order matters: innermost executes first)
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(AuthMiddleware)
    # app.add_middleware(TenantMiddleware)

    # Exception Handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """Handle Pydantic validation errors."""
        logger.warning(f"Validation error on {request.url}: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "message": "Request validation failed",
                "details": exc.errors(),
            },
        )

    @app.exception_handler(TenantNotFoundError)
    async def tenant_not_found_handler(request: Request, exc: TenantNotFoundError):
        logger.warning(f"Tenant not found: {exc.tenant_id}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "tenant_not_found", "message": str(exc)},
        )

    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request: Request, exc: AuthenticationError):
        logger.warning(f"Authentication error: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "authentication_error", "message": str(exc)},
        )

    @app.exception_handler(ValidationError)
    async def custom_validation_handler(request: Request, exc: ValidationError):
        logger.warning(f"Custom validation error: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "validation_error", "message": str(exc)},
        )

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.error(f"Application error: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.error_code, "message": exc.message},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(
            f"Unhandled exception on {request.url}: {str(exc)}", exc_info=True
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
            },
        )
    
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        # Agregar el esquema BearerAuth si no existe
        openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
        openapi_schema["components"]["securitySchemes"]["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Ingrese su token JWT de AWS Cognito en formato: **Bearer <token>**",
        }

        # 🔒 Asignar el esquema de seguridad a todas las rutas (excepto las públicas)
        paths = openapi_schema.get("paths", {})
        for path, methods in paths.items():
            if not any(path.startswith(p) for p in AuthMiddleware.PUBLIC_PATHS):
                for method_name, method_spec in methods.items():
                    # Asegurar que la ruta tenga un campo "security"
                    existing_security = method_spec.get("security", [])
                    if not existing_security:
                        method_spec["security"] = [{"BearerAuth": []}]

        # Aplicar seguridad global también (para que el botón "Authorize" funcione)
        openapi_schema["security"] = [{"BearerAuth": []}]

        app.openapi_schema = openapi_schema
        return app.openapi_schema


    # Include routers
    app.include_router(v1_router, prefix="/api/v1")
    
    app.openapi = custom_openapi
    
    logger.info(f"FastAPI application created successfully (v{settings.APP_VERSION})")
    return app
# Create application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT != "production",
        workers=settings.WORKERS if settings.ENVIRONMENT == "production" else 1,
        log_level=settings.LOG_LEVEL.lower(),
    )
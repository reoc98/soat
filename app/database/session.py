import os
import asyncio
import logging
from functools import lru_cache
from typing import Literal, Optional, Dict, Any
from contextlib import asynccontextmanager, contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.aws.secrets import AWSSecretsManager
from app.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Centralized manager for tenant-aware database connections.
    Supports both sync and async modes.
    """

    def __init__(self):
        self.engines: Dict[str, Any] = {}
        self.session_makers: Dict[str, Any] = {}
        self._cleanup_task = None
        self._running = False
    
    async def initialize(self):
        """Initialize internal structures (lazy engine creation)."""
        logger.info("DatabaseManager initialized. Engines will be created lazily.")
    
    async def close_all(self):
        """Cleanly close all engines and cancel cleanup task."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            logger.info("Background cleanup task cancelled")

        for key, engine in self.engines.items():
            try:
                await engine.dispose()
                logger.info(f"Closed engine for {key}")
            except Exception as e:
                logger.warning(f"Error closing engine {key}: {e}")

        self.engines.clear()
        self.session_makers.clear()

    def get_db_credentials(self, mode: Literal["dbr", "dbw"], tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetch database credentials from AWS Secrets Manager."""
        if mode not in ["dbr", "dbw"]:
            raise ValueError("Invalid database mode. Use 'dbr' or 'dbw'.")

        connection_data = AWSSecretsManager().get_secret(mode, tenant_id)
        if not connection_data:
            raise DatabaseError(f"Could not retrieve DB credentials for mode: {mode}, tenant_id: {tenant_id}")

        return connection_data

    def _get_or_create_engine(
        self,
        mode: Literal["dbr", "dbw"] = "dbr",
        tenant_id: Optional[str] = None,
        async_mode: bool = False,
    ):
        """Create or reuse a SQLAlchemy engine for tenant + mode."""
        key = f"{tenant_id or 'soat'}_{mode}_{'async' if async_mode else 'sync'}"
        if key in self.engines:
            return self.engines[key]
        
        creds = self.get_db_credentials(mode, tenant_id)
        echo = os.getenv("SQL_ECHO", "false").lower() == "true"
        url = self._build_url(creds, async_mode)
        
        engine_factory = create_async_engine if async_mode else create_engine
        engine = engine_factory(
            url,
            echo=echo,
            pool_pre_ping=True,
            pool_recycle=int(creds.get('pool_recycle', 3600))
        )
        self.engines[key] = engine
        logger.info(f"Created new engine for {key}")
        return engine

    @contextmanager
    def get_session(
        self, mode: Literal["dbr", "dbw"] = "dbr", tenant_id: Optional[str] = None
    ):
        """Synchronous session context (useful for scripts)."""
        engine = self._get_or_create_engine(mode, tenant_id, async_mode=False)
        SessionLocal = sessionmaker(
            bind=engine, autocommit=False, autoflush=False, expire_on_commit=False, class_=Session
        )
        session: Session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    @asynccontextmanager
    async def get_async_session(
        self, mode: Literal["dbr", "dbw"] = "dbr", tenant_id: Optional[str] = None
    ):
        """Asynchronous session context for FastAPI endpoints."""
        engine = self._get_or_create_engine(mode, tenant_id, async_mode=True)
        AsyncSessionLocal = sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
        async with AsyncSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()
    
    def _build_url(self, creds: Dict[str, Any], async_mode: bool) -> str:
        """Build the SQLAlchemy connection URL."""
        driver = "mysql+asyncmy" if async_mode else "mysql+pymysql"
        return (
            f"{driver}://{creds['username']}:{creds['password']}"
            f"@{creds['host']}:{creds['port']}/{creds['database']}"
        )
    
    async def start_background_cleanup(self, interval: int = 300):
        """Periodically clears engine cache."""
        if self._running:
            return
        self._running = True

        async def _cleanup_loop():
            while self._running:
                await asyncio.sleep(interval)
                cleared = len(self.engines)
                self.engines.clear()
                self.session_makers.clear()
                logger.info(
                    f"Database engine cache cleared ({cleared} engines removed)")

        self._cleanup_task = asyncio.create_task(_cleanup_loop())

    # async def close_all(self):
    #     """Close all engines cleanly on shutdown."""
    #     self._running = False
    #     if self._cleanup_task:
    #         self._cleanup_task.cancel()

    #     for engine in self.engines.values():
    #         try:
    #             await engine.dispose()
    #         except Exception as e:
    #             logger.warning(f"Error disposing engine: {e}")

    #     if self.master_engine:
    #         await self.master_engine.dispose()
    #         logger.info("Master DB engine closed")


db_manager = DatabaseManager()
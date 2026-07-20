from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
)

from app.core.logging import configure_logging
from app.core.settings import Settings, get_settings
from app.db.session import (
    create_database_engine,
    create_session_factory,
)


logger = logging.getLogger(__name__)


async def verify_database_connection(
    engine: AsyncEngine,
) -> None:
    """
    Verify that PostgreSQL is reachable during startup.
    """

    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


def create_http_client(
    settings: Settings,
) -> httpx.AsyncClient:
    """
    Create one shared HTTP client for downstream service clients.
    """

    timeout = httpx.Timeout(
        connect=settings.http_connect_timeout_seconds,
        read=settings.http_read_timeout_seconds,
        write=settings.http_read_timeout_seconds,
        pool=settings.http_connect_timeout_seconds,
    )

    limits = httpx.Limits(
        max_connections=settings.http_max_connections,
        max_keepalive_connections=(
            settings.http_max_keepalive_connections
        ),
    )

    return httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
        follow_redirects=False,
        headers={
            "User-Agent": (
                f"{settings.service_name}/"
                f"{settings.service_version}"
            ),
        },
    )


async def initialize_application_state(
    app: FastAPI,
    settings: Settings,
) -> None:
    """
    Initialize process-level application resources.
    """

    database_engine = create_database_engine(settings)

    session_factory = create_session_factory(
        database_engine
    )

    http_client = create_http_client(settings)

    app.state.settings = settings
    app.state.database_engine = database_engine
    app.state.session_factory = session_factory
    app.state.http_client = http_client

    app.state.started = False
    app.state.ready = False
    app.state.startup_checks = {}

    try:
        await verify_database_connection(
            database_engine
        )

        app.state.startup_checks["database"] = {
            "status": "healthy",
            "message": None,
        }

    except Exception:
        app.state.startup_checks["database"] = {
            "status": "unhealthy",
            "message": "Database connection failed.",
        }

        await http_client.aclose()
        await database_engine.dispose()

        raise

    app.state.started = True
    app.state.ready = True


async def close_application_state(
    app: FastAPI,
) -> None:
    """
    Gracefully close shared application resources.
    """

    app.state.ready = False
    app.state.started = False

    http_client: httpx.AsyncClient | None = getattr(
        app.state,
        "http_client",
        None,
    )

    database_engine: AsyncEngine | None = getattr(
        app.state,
        "database_engine",
        None,
    )

    if http_client is not None:
        try:
            await http_client.aclose()
        except Exception:
            logger.exception(
                "Failed to close the shared HTTP client."
            )

    if database_engine is not None:
        try:
            await database_engine.dispose()
        except Exception:
            logger.exception(
                "Failed to dispose the database engine."
            )


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncIterator[None]:
    """
    FastAPI lifespan manager for startup and graceful shutdown.
    """

    settings = get_settings()

    configure_logging(settings)

    logger.info(
        "Starting Pet Service.",
        extra={
            "service_name": settings.service_name,
            "service_version": settings.service_version,
            "environment": settings.environment,
        },
    )

    try:
        await initialize_application_state(
            app,
            settings,
        )

        logger.info(
            "Pet Service startup completed.",
            extra={
                "startup_checks": (
                    app.state.startup_checks
                ),
            },
        )

        yield

    except Exception:
        logger.exception(
            "Pet Service startup or runtime failed."
        )
        raise

    finally:
        logger.info("Stopping Pet Service.")

        await close_application_state(app)

        logger.info(
            "Pet Service shutdown completed."
        )


def get_database_engine(
    app: FastAPI,
) -> AsyncEngine:
    engine: AsyncEngine | None = getattr(
        app.state,
        "database_engine",
        None,
    )

    if engine is None:
        raise RuntimeError(
            "Database engine has not been initialized."
        )

    return engine


def get_session_factory(
    app: FastAPI,
) -> async_sessionmaker:
    session_factory: async_sessionmaker | None = getattr(
        app.state,
        "session_factory",
        None,
    )

    if session_factory is None:
        raise RuntimeError(
            "Database session factory has not been initialized."
        )

    return session_factory


def get_http_client(
    app: FastAPI,
) -> httpx.AsyncClient:
    http_client: httpx.AsyncClient | None = getattr(
        app.state,
        "http_client",
        None,
    )

    if http_client is None:
        raise RuntimeError(
            "HTTP client has not been initialized."
        )

    return http_client

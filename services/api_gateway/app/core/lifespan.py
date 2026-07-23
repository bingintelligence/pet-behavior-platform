from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging


logger = logging.getLogger(__name__)


def create_http_client(
    settings: Settings,
) -> httpx.AsyncClient:
    """
    Create the shared asynchronous client used for downstream services.
    """

    timeout = httpx.Timeout(
        connect=settings.http_connect_timeout_seconds,
        read=settings.http_read_timeout_seconds,
        write=settings.http_write_timeout_seconds,
        pool=settings.http_pool_timeout_seconds,
    )

    limits = httpx.Limits(
        max_connections=settings.http_max_connections,
        max_keepalive_connections=(
            settings.http_max_keepalive_connections
        ),
        keepalive_expiry=(
            settings.http_keepalive_expiry_seconds
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
            "X-Service-Name": settings.service_name,
        },
    )


async def check_downstream_service(
    *,
    client: httpx.AsyncClient,
    service_name: str,
    service_url: str,
) -> dict[str, str | int | None]:
    """
    Perform a lightweight downstream readiness probe.

    Failure does not prevent Gateway startup because individual downstream
    services may recover independently after the Gateway starts.
    """

    health_url = f"{service_url.rstrip('/')}/health/ready"

    try:
        response = await client.get(health_url)

        return {
            "status": (
                "healthy"
                if response.is_success
                else "unhealthy"
            ),
            "status_code": response.status_code,
            "message": None,
        }

    except httpx.TimeoutException:
        return {
            "status": "unhealthy",
            "status_code": None,
            "message": f"{service_name} readiness check timed out.",
        }

    except httpx.HTTPError:
        return {
            "status": "unhealthy",
            "status_code": None,
            "message": f"{service_name} readiness check failed.",
        }


async def initialize_application_state(
    app: FastAPI,
    settings: Settings,
) -> None:
    """
    Initialize process-level API Gateway resources.
    """

    http_client = create_http_client(settings)

    app.state.settings = settings
    app.state.http_client = http_client

    app.state.started = False
    app.state.ready = False
    app.state.started_at = None
    app.state.startup_checks = {}

    service_urls = {
        "auth-service": str(settings.auth_service_url),
        "user-service": str(settings.user_service_url),
        "pet-service": str(settings.pet_service_url),
        "behavior-service": str(
            settings.behavior_service_url
        ),
        "analysis-service": str(
            settings.analysis_service_url
        ),
        "media-service": str(settings.media_service_url),
        "subscription-service": str(
            settings.subscription_service_url
        ),
    }

    try:
        for service_name, service_url in service_urls.items():
            app.state.startup_checks[service_name] = (
                await check_downstream_service(
                    client=http_client,
                    service_name=service_name,
                    service_url=service_url,
                )
            )

        app.state.started = True
        app.state.ready = True
        app.state.started_at = datetime.now(timezone.utc)

    except Exception:
        await http_client.aclose()
        raise


async def close_application_state(
    app: FastAPI,
) -> None:
    """
    Gracefully close shared API Gateway resources.
    """

    app.state.ready = False
    app.state.started = False

    http_client: httpx.AsyncClient | None = getattr(
        app.state,
        "http_client",
        None,
    )

    if http_client is not None:
        try:
            await http_client.aclose()
        except Exception:
            logger.exception(
                "Failed to close the shared downstream HTTP client."
            )


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncIterator[None]:
    """
    FastAPI lifespan manager for the API Gateway.

    Startup:

    1. Load and validate settings
    2. Configure structured logging
    3. Create the shared downstream HTTP client
    4. Probe downstream service readiness
    5. Mark the Gateway ready

    Shutdown:

    1. Mark the Gateway not ready
    2. Close the HTTP connection pool
    """

    settings = get_settings()

    configure_logging(settings)

    logger.info(
        "Starting API Gateway.",
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

        unhealthy_services = [
            service_name
            for service_name, result
            in app.state.startup_checks.items()
            if result["status"] != "healthy"
        ]

        logger.info(
            "API Gateway startup completed.",
            extra={
                "startup_checks": app.state.startup_checks,
                "unhealthy_services": unhealthy_services,
            },
        )

        yield

    except Exception:
        logger.exception(
            "API Gateway startup or runtime failed."
        )
        raise

    finally:
        logger.info("Stopping API Gateway.")

        await close_application_state(app)

        logger.info(
            "API Gateway shutdown completed."
        )


def get_http_client_from_app(
    app: FastAPI,
) -> httpx.AsyncClient:
    """
    Return the initialized shared HTTP client.
    """

    client: httpx.AsyncClient | None = getattr(
        app.state,
        "http_client",
        None,
    )

    if client is None:
        raise RuntimeError(
            "Gateway HTTP client has not been initialized."
        )

    return client


def is_application_ready(app: FastAPI) -> bool:
    """
    Return the current Gateway readiness state.
    """

    return bool(
        getattr(
            app.state,
            "ready",
            False,
        )
    )

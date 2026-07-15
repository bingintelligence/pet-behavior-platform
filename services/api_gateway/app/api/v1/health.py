from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response, status

from app.core.config import Settings
from app.core.dependencies import (
    get_health_checker,
    get_settings,
)
from app.schemas.health import (
    DependencyHealth,
    HealthResponse,
    HealthStatus,
)
from app.services.health_checker import HealthChecker

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)

HealthCheckerDependency = Annotated[
    HealthChecker,
    Depends(get_health_checker),
]

SettingsDependency = Annotated[
    Settings,
    Depends(get_settings),
]


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Get service health",
    include_in_schema=False,
)
async def health() -> HealthResponse:
    """
    Return a lightweight service health response.

    This endpoint does not perform downstream dependency checks.
    """
    return HealthResponse(
        status=HealthStatus.HEALTHY,
        service="api-gateway",
        timestamp=datetime.now(UTC),
    )


@router.get(
    "/live",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Kubernetes liveness probe",
    include_in_schema=False,
)
async def liveness() -> HealthResponse:
    """
    Confirm that the API Gateway process is running.

    Liveness checks should remain lightweight and should not fail because a
    downstream dependency is temporarily unavailable.
    """
    return HealthResponse(
        status=HealthStatus.HEALTHY,
        service="api-gateway",
        timestamp=datetime.now(UTC),
    )


@router.get(
    "/ready",
    response_model=HealthResponse,
    summary="Kubernetes readiness probe",
    include_in_schema=False,
)
async def readiness(
    response: Response,
    request: Request,
    health_checker: HealthCheckerDependency,
    settings: SettingsDependency,
) -> HealthResponse:
    """
    Confirm that the API Gateway is ready to receive traffic.

    Readiness may check critical internal dependencies such as Redis, service
    discovery, or required downstream services. It should use short timeouts
    and avoid expensive operations.
    """
    checks = await _run_readiness_checks(
        health_checker=health_checker,
        timeout_seconds=settings.health_check_timeout_seconds,
    )

    overall_status = _calculate_overall_status(checks)

    if overall_status is HealthStatus.UNHEALTHY:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status=overall_status,
        service="api-gateway",
        version=settings.app_version,
        timestamp=datetime.now(UTC),
        request_id=_get_request_id(request),
        dependencies=checks,
    )


@router.get(
    "/startup",
    response_model=HealthResponse,
    summary="Kubernetes startup probe",
    include_in_schema=False,
)
async def startup(
    response: Response,
    request: Request,
    health_checker: HealthCheckerDependency,
    settings: SettingsDependency,
) -> HealthResponse:
    """
    Confirm that application startup has completed successfully.

    This may check that configuration was loaded and that critical clients were
    initialized. Kubernetes can use this endpoint to protect slow-starting
    containers from premature liveness failures.
    """
    checks = await _run_startup_checks(
        health_checker=health_checker,
        timeout_seconds=settings.health_check_timeout_seconds,
    )

    overall_status = _calculate_overall_status(checks)

    if overall_status is HealthStatus.UNHEALTHY:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status=overall_status,
        service="api-gateway",
        version=settings.app_version,
        timestamp=datetime.now(UTC),
        request_id=_get_request_id(request),
        dependencies=checks,
    )


async def _run_readiness_checks(
    health_checker: HealthChecker,
    timeout_seconds: float,
) -> list[DependencyHealth]:
    checks: dict[str, Any] = {
        "redis": health_checker.check_redis(),
        "auth-service": health_checker.check_auth_service(),
        "pet-service": health_checker.check_pet_service(),
        "analysis-service": health_checker.check_analysis_service(),
        "media-service": health_checker.check_media_service(),
        "billing-service": health_checker.check_billing_service(),
    }

    results = await asyncio.gather(
        *[
            _execute_check(
                name=name,
                check=check,
                timeout_seconds=timeout_seconds,
            )
            for name, check in checks.items()
        ]
    )

    return list(results)


async def _run_startup_checks(
    health_checker: HealthChecker,
    timeout_seconds: float,
) -> list[DependencyHealth]:
    checks: dict[str, Any] = {
        "configuration": health_checker.check_configuration(),
        "http-client": health_checker.check_http_client(),
    }

    results = await asyncio.gather(
        *[
            _execute_check(
                name=name,
                check=check,
                timeout_seconds=timeout_seconds,
            )
            for name, check in checks.items()
        ]
    )

    return list(results)


async def _execute_check(
    name: str,
    check: Any,
    timeout_seconds: float,
) -> DependencyHealth:
    started_at = asyncio.get_running_loop().time()

    try:
        result = await asyncio.wait_for(
            check,
            timeout=timeout_seconds,
        )

        latency_ms = (
            asyncio.get_running_loop().time() - started_at
        ) * 1000

        return DependencyHealth(
            name=name,
            status=(
                HealthStatus.HEALTHY
                if result
                else HealthStatus.UNHEALTHY
            ),
            latency_ms=round(latency_ms, 2),
        )
    except TimeoutError:
        latency_ms = (
            asyncio.get_running_loop().time() - started_at
        ) * 1000

        return DependencyHealth(
            name=name,
            status=HealthStatus.UNHEALTHY,
            latency_ms=round(latency_ms, 2),
            message="Health check timed out.",
        )
    except Exception as exc:
        latency_ms = (
            asyncio.get_running_loop().time() - started_at
        ) * 1000

        return DependencyHealth(
            name=name,
            status=HealthStatus.UNHEALTHY,
            latency_ms=round(latency_ms, 2),
            message=type(exc).__name__,
        )


def _calculate_overall_status(
    checks: list[DependencyHealth],
) -> HealthStatus:
    if any(
        check.status is HealthStatus.UNHEALTHY
        for check in checks
    ):
        return HealthStatus.UNHEALTHY

    return HealthStatus.HEALTHY


def _get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)

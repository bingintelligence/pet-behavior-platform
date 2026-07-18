from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class HealthSchema(BaseModel):
    """
    Base schema for API Gateway health endpoints.
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
        use_enum_values=False,
    )


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class DependencyHealth(HealthSchema):
    """
    Sanitized health status for an internal dependency.

    Raw exceptions, credentials, internal URLs, hostnames, response bodies,
    and stack traces must not be exposed through this schema.
    """

    name: str = Field(
        min_length=1,
        max_length=100,
    )

    status: HealthStatus

    latency_ms: float | None = Field(
        default=None,
        ge=0,
    )

    message: str | None = Field(
        default=None,
        max_length=500,
    )

    checked_at: datetime


class HealthResponse(HealthSchema):
    """
    General health endpoint response.

    This response may include dependency information when appropriate.
    """

    status: HealthStatus

    service: str = Field(
        min_length=1,
        max_length=100,
    )

    version: str | None = Field(
        default=None,
        max_length=100,
    )

    timestamp: datetime

    request_id: str | None = Field(
        default=None,
        max_length=255,
    )

    uptime_seconds: float | None = Field(
        default=None,
        ge=0,
    )

    dependencies: list[DependencyHealth] = Field(
        default_factory=list,
    )


class LivenessResponse(HealthSchema):
    """
    Kubernetes liveness probe response.

    Liveness must only represent whether the API Gateway process is alive.
    It must not depend on Redis, databases, or downstream services.
    """

    status: HealthStatus
    service: str = Field(
        min_length=1,
        max_length=100,
    )
    timestamp: datetime


class ReadinessResponse(HealthSchema):
    """
    Kubernetes readiness probe response.

    Critical dependencies may be included to explain whether the gateway is
    currently able to serve traffic.
    """

    status: HealthStatus

    service: str = Field(
        min_length=1,
        max_length=100,
    )

    timestamp: datetime

    ready: bool

    dependencies: list[DependencyHealth] = Field(
        default_factory=list,
    )


class StartupCheck(HealthSchema):
    """
    One application startup validation result.
    """

    name: str = Field(
        min_length=1,
        max_length=100,
    )

    status: HealthStatus

    message: str | None = Field(
        default=None,
        max_length=500,
    )


class StartupResponse(HealthSchema):
    """
    Kubernetes startup probe response.

    Startup checks may validate application initialization, required
    configuration, dependency client creation, and other local startup state.
    """

    status: HealthStatus

    service: str = Field(
        min_length=1,
        max_length=100,
    )

    timestamp: datetime

    started: bool

    checks: list[StartupCheck] = Field(
        default_factory=list,
    )

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import (
    AnyHttpUrl,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


Environment = Literal[
    "local",
    "development",
    "test",
    "staging",
    "production",
]

LogLevel = Literal[
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
]


class Settings(BaseSettings):
    """
    Runtime configuration for the API Gateway.

    Environment variables use the ``API_GATEWAY_`` prefix.

    Examples:
        API_GATEWAY_ENVIRONMENT=production
        API_GATEWAY_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----..."
        API_GATEWAY_PET_SERVICE_URL=http://pet-service:8001
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="API_GATEWAY_",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------

    service_name: str = Field(
        default="api-gateway",
        min_length=1,
        max_length=100,
    )

    service_version: str = Field(
        default="0.1.0",
        min_length=1,
        max_length=100,
    )

    environment: Environment = "local"

    debug: bool = False

    host: str = Field(
        default="0.0.0.0",
        min_length=1,
        max_length=255,
    )

    port: int = Field(
        default=8000,
        ge=1,
        le=65_535,
    )

    api_v1_prefix: str = Field(
        default="/api/v1",
        min_length=1,
        max_length=100,
    )

    docs_enabled: bool = True

    # ------------------------------------------------------------------
    # Logging and observability
    # ------------------------------------------------------------------

    log_level: LogLevel = "INFO"

    log_json: bool = True

    access_log_enabled: bool = True

    metrics_enabled: bool = True

    tracing_enabled: bool = False

    otel_exporter_otlp_endpoint: AnyHttpUrl | None = None

    # ------------------------------------------------------------------
    # JWT authentication
    # ------------------------------------------------------------------

    jwt_algorithm: str = Field(
        default="RS256",
        min_length=1,
        max_length=20,
    )

    jwt_public_key: SecretStr | None = None

    jwt_issuer: str = Field(
        default="bing-intelligence-auth-service",
        min_length=1,
        max_length=255,
    )

    jwt_audience: str = Field(
        default="pet-behavior-platform",
        min_length=1,
        max_length=255,
    )

    jwt_leeway_seconds: int = Field(
        default=10,
        ge=0,
        le=300,
    )

    jwt_required_claims: list[str] = Field(
        default_factory=lambda: [
            "sub",
            "iss",
            "aud",
            "exp",
            "iat",
        ],
    )

    # ------------------------------------------------------------------
    # Internal service authentication
    # ------------------------------------------------------------------

    internal_service_token: SecretStr | None = None

    internal_service_name_header: str = Field(
        default="X-Service-Name",
        min_length=1,
        max_length=100,
    )

    internal_service_token_header: str = Field(
        default="X-Internal-Service-Token",
        min_length=1,
        max_length=100,
    )

    # ------------------------------------------------------------------
    # Downstream services
    # ------------------------------------------------------------------

    auth_service_url: AnyHttpUrl = Field(
        default="http://auth-service:8001",
    )

    user_service_url: AnyHttpUrl = Field(
        default="http://user-service:8002",
    )

    pet_service_url: AnyHttpUrl = Field(
        default="http://pet-service:8003",
    )

    behavior_service_url: AnyHttpUrl = Field(
        default="http://behavior-service:8004",
    )

    analysis_service_url: AnyHttpUrl = Field(
        default="http://analysis-service:8005",
    )

    media_service_url: AnyHttpUrl = Field(
        default="http://media-service:8006",
    )

    subscription_service_url: AnyHttpUrl = Field(
        default="http://subscription-service:8007",
    )

    notification_service_url: AnyHttpUrl = Field(
        default="http://notification-service:8008",
    )

    # ------------------------------------------------------------------
    # Downstream HTTP client
    # ------------------------------------------------------------------

    http_connect_timeout_seconds: float = Field(
        default=3.0,
        gt=0,
        le=60,
    )

    http_read_timeout_seconds: float = Field(
        default=15.0,
        gt=0,
        le=300,
    )

    http_write_timeout_seconds: float = Field(
        default=15.0,
        gt=0,
        le=300,
    )

    http_pool_timeout_seconds: float = Field(
        default=5.0,
        gt=0,
        le=60,
    )

    http_max_connections: int = Field(
        default=200,
        ge=1,
        le=5_000,
    )

    http_max_keepalive_connections: int = Field(
        default=50,
        ge=1,
        le=1_000,
    )

    http_keepalive_expiry_seconds: float = Field(
        default=30.0,
        gt=0,
        le=300,
    )

    # ------------------------------------------------------------------
    # Request handling
    # ------------------------------------------------------------------

    request_id_header: str = Field(
        default="X-Request-ID",
        min_length=1,
        max_length=100,
    )

    max_request_body_bytes: int = Field(
        default=10 * 1024 * 1024,
        ge=1_024,
    )

    default_page_size: int = Field(
        default=20,
        ge=1,
        le=100,
    )

    max_page_size: int = Field(
        default=100,
        ge=1,
        le=500,
    )

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------

    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
        ],
    )

    cors_allowed_methods: list[str] = Field(
        default_factory=lambda: [
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "OPTIONS",
        ],
    )

    cors_allowed_headers: list[str] = Field(
        default_factory=lambda: [
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "X-Idempotency-Key",
        ],
    )

    cors_exposed_headers: list[str] = Field(
        default_factory=lambda: [
            "X-Request-ID",
        ],
    )

    cors_allow_credentials: bool = True

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @field_validator("api_v1_prefix")
    @classmethod
    def normalize_api_prefix(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized.startswith("/"):
            normalized = f"/{normalized}"

        normalized = normalized.rstrip("/")

        if not normalized:
            raise ValueError("api_v1_prefix cannot be empty.")

        return normalized

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, value: str) -> str:
        algorithm = value.strip().upper()

        allowed_algorithms = {
            "RS256",
            "RS384",
            "RS512",
            "ES256",
            "ES384",
            "ES512",
        }

        if algorithm not in allowed_algorithms:
            raise ValueError(
                "jwt_algorithm must use an approved asymmetric algorithm."
            )

        return algorithm

    @field_validator("jwt_required_claims")
    @classmethod
    def normalize_required_claims(
        cls,
        values: list[str],
    ) -> list[str]:
        normalized = list(
            dict.fromkeys(
                value.strip()
                for value in values
                if value.strip()
            )
        )

        mandatory_claims = {
            "sub",
            "iss",
            "aud",
            "exp",
            "iat",
        }

        missing_claims = mandatory_claims.difference(normalized)

        if missing_claims:
            raise ValueError(
                "jwt_required_claims is missing mandatory claims: "
                f"{sorted(missing_claims)}"
            )

        return normalized

    @field_validator(
        "cors_allowed_origins",
        "cors_allowed_methods",
        "cors_allowed_headers",
        "cors_exposed_headers",
    )
    @classmethod
    def normalize_string_list(
        cls,
        values: list[str],
    ) -> list[str]:
        return list(
            dict.fromkeys(
                value.strip()
                for value in values
                if value.strip()
            )
        )

    @model_validator(mode="after")
    def validate_settings(self) -> Settings:
        if self.default_page_size > self.max_page_size:
            raise ValueError(
                "default_page_size must not exceed max_page_size."
            )

        if (
            self.http_max_keepalive_connections
            > self.http_max_connections
        ):
            raise ValueError(
                "http_max_keepalive_connections must not exceed "
                "http_max_connections."
            )

        if self.environment in {"staging", "production"}:
            if self.debug:
                raise ValueError(
                    "debug must be disabled in staging and production."
                )

            if self.jwt_public_key is None:
                raise ValueError(
                    "jwt_public_key is required in staging and production."
                )

            if self.internal_service_token is None:
                raise ValueError(
                    "internal_service_token is required in staging "
                    "and production."
                )

            if "*" in self.cors_allowed_origins:
                raise ValueError(
                    "Wildcard CORS origins are not permitted in staging "
                    "or production when credentials are enabled."
                )

        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def jwt_public_key_value(self) -> str:
        if self.jwt_public_key is None:
            raise RuntimeError(
                "JWT public key has not been configured."
            )

        return self.jwt_public_key.get_secret_value()

    @property
    def internal_service_token_value(self) -> str:
        if self.internal_service_token is None:
            raise RuntimeError(
                "Internal service token has not been configured."
            )

        return self.internal_service_token.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    """
    Return one cached settings instance per application process.

    Tests can clear the cache with:

        get_settings.cache_clear()
    """

    return Settings()

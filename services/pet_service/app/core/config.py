from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import (
    AnyHttpUrl,
    Field,
    PostgresDsn,
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
    Pet Service runtime configuration.

    Environment variables use the PET_SERVICE_ prefix.

    Examples:
        PET_SERVICE_ENVIRONMENT=production
        PET_SERVICE_DATABASE_URL=postgresql+asyncpg://...
        PET_SERVICE_JWT_PUBLIC_KEY=...
        PET_SERVICE_INTERNAL_SERVICE_TOKEN=...
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PET_SERVICE_",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------

    service_name: str = Field(
        default="pet-service",
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
        default=8001,
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

    metrics_enabled: bool = True

    tracing_enabled: bool = False

    otel_exporter_otlp_endpoint: AnyHttpUrl | None = None

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------

    database_url: PostgresDsn = Field(
        default=(
            "postgresql+asyncpg://"
            "pet_service:pet_service@localhost:5432/pet_service"
        ),
    )

    database_pool_size: int = Field(
        default=10,
        ge=1,
        le=100,
    )

    database_max_overflow: int = Field(
        default=20,
        ge=0,
        le=200,
    )

    database_pool_timeout_seconds: int = Field(
        default=30,
        ge=1,
        le=300,
    )

    database_pool_recycle_seconds: int = Field(
        default=1_800,
        ge=60,
    )

    database_echo: bool = False

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

    internal_service_header: str = Field(
        default="X-Internal-Service-Token",
        min_length=1,
        max_length=100,
    )

    trusted_service_names: set[str] = Field(
        default_factory=lambda: {
            "api-gateway",
            "analysis-service",
            "media-service",
            "user-service",
        },
    )

    # ------------------------------------------------------------------
    # HTTP clients
    # ------------------------------------------------------------------

    media_service_url: AnyHttpUrl = Field(
        default="http://media-service:8003",
    )

    user_service_url: AnyHttpUrl = Field(
        default="http://user-service:8002",
    )

    analysis_service_url: AnyHttpUrl = Field(
        default="http://analysis-service:8004",
    )

    http_connect_timeout_seconds: float = Field(
        default=3.0,
        gt=0,
        le=60,
    )

    http_read_timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        le=300,
    )

    http_max_connections: int = Field(
        default=100,
        ge=1,
        le=1_000,
    )

    http_max_keepalive_connections: int = Field(
        default=20,
        ge=1,
        le=500,
    )

    # ------------------------------------------------------------------
    # Pet domain limits
    # ------------------------------------------------------------------

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

    max_pets_per_user: int = Field(
        default=100,
        ge=1,
        le=10_000,
    )

    max_pet_name_length: int = Field(
        default=100,
        ge=1,
        le=500,
    )

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------

    cors_allowed_origins: list[str] = Field(
        default_factory=list,
    )

    cors_allow_credentials: bool = True

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized.startswith("/"):
            normalized = f"/{normalized}"

        return normalized.rstrip("/")

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, value: str) -> str:
        algorithm = value.upper()

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

    @field_validator("trusted_service_names")
    @classmethod
    def normalize_service_names(
        cls,
        values: set[str],
    ) -> set[str]:
        normalized = {
            value.strip().lower()
            for value in values
            if value.strip()
        }

        if not normalized:
            raise ValueError(
                "trusted_service_names must contain at least one service."
            )

        return normalized

    @field_validator("cors_allowed_origins")
    @classmethod
    def normalize_cors_origins(
        cls,
        values: list[str],
    ) -> list[str]:
        normalized = list(
            dict.fromkeys(
                value.strip().rstrip("/")
                for value in values
                if value.strip()
            )
        )

        return normalized

    @model_validator(mode="after")
    def validate_environment_configuration(self) -> Settings:
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

            if self.database_echo:
                raise ValueError(
                    "database_echo must be disabled in staging "
                    "and production."
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
                    "or production."
                )

        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def sqlalchemy_database_url(self) -> str:
        """
        Return the database URL as a regular string for SQLAlchemy.
        """

        return str(self.database_url)

    @property
    def jwt_public_key_value(self) -> str:
        """
        Return the configured JWT public key.

        Raises:
            RuntimeError: When no key is configured.
        """

        if self.jwt_public_key is None:
            raise RuntimeError(
                "JWT public key has not been configured."
            )

        return self.jwt_public_key.get_secret_value()

    @property
    def internal_service_token_value(self) -> str:
        """
        Return the configured service token.

        Raises:
            RuntimeError: When no service token is configured.
        """

        if self.internal_service_token is None:
            raise RuntimeError(
                "Internal service token has not been configured."
            )

        return self.internal_service_token.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    """
    Return one cached Settings instance per application process.

    Tests can override environment variables and then call:

        get_settings.cache_clear()
    """

    return Settings()

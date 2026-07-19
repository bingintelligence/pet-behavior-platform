from __future__ import annotations

import secrets
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID

import jwt
from jwt import (
    DecodeError,
    ExpiredSignatureError,
    ImmatureSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
    MissingRequiredClaimError,
    PyJWTError,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    ValidationError,
    field_validator,
)

from app.core.config import Settings


class SecurityErrorCode(StrEnum):
    MISSING_TOKEN = "missing_token"
    INVALID_TOKEN = "invalid_token"
    EXPIRED_TOKEN = "expired_token"
    INVALID_CLAIMS = "invalid_claims"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"
    INVALID_SERVICE_TOKEN = "invalid_service_token"
    UNTRUSTED_SERVICE = "untrusted_service"


class AuthenticationError(Exception):
    """
    Internal authentication failure.

    FastAPI-specific HTTP responses are created in dependencies.py so this
    security module remains independent from the transport layer.
    """

    def __init__(
        self,
        code: SecurityErrorCode,
        message: str,
    ) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class UserRole(StrEnum):
    USER = "user"
    SUPPORT = "support"
    MODERATOR = "moderator"
    ANALYST = "analyst"
    OPERATIONS = "operations"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(StrEnum):
    ACTIVE = "active"
    PENDING_VERIFICATION = "pending_verification"
    DISABLED = "disabled"
    LOCKED = "locked"
    DELETION_PENDING = "deletion_pending"
    DELETED = "deleted"


class AuthenticatedUser(BaseModel):
    """
    Validated user context extracted from an access token.

    This is not a database model. It represents authentication and
    authorization information supplied by the Auth Service.
    """

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
        str_strip_whitespace=True,
    )

    id: UUID
    email: EmailStr | None = None
    roles: frozenset[UserRole] = Field(
        default_factory=lambda: frozenset({UserRole.USER}),
    )
    scopes: frozenset[str] = Field(default_factory=frozenset)
    status: UserStatus = UserStatus.ACTIVE
    session_id: str | None = Field(
        default=None,
        max_length=255,
    )
    token_id: str | None = Field(
        default=None,
        max_length=255,
    )
    issued_at: datetime
    expires_at: datetime

    @field_validator("roles", mode="before")
    @classmethod
    def normalize_roles(cls, value: Any) -> Any:
        if value is None:
            return frozenset({UserRole.USER})

        if isinstance(value, str):
            return frozenset(
                role.strip()
                for role in value.split(",")
                if role.strip()
            )

        return frozenset(value)

    @field_validator("scopes", mode="before")
    @classmethod
    def normalize_scopes(cls, value: Any) -> Any:
        if value is None:
            return frozenset()

        if isinstance(value, str):
            return frozenset(
                scope.strip()
                for scope in value.replace(",", " ").split()
                if scope.strip()
            )

        return frozenset(value)

    @property
    def is_admin(self) -> bool:
        return bool(
            {
                UserRole.ADMIN,
                UserRole.SUPER_ADMIN,
            }
            & self.roles
        )

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE

    def has_role(self, role: UserRole) -> bool:
        return role in self.roles

    def has_any_role(self, roles: set[UserRole]) -> bool:
        return bool(self.roles.intersection(roles))

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    def has_all_scopes(self, scopes: set[str]) -> bool:
        return scopes.issubset(self.scopes)


class InternalServiceIdentity(BaseModel):
    """
    Identity of a trusted internal caller.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )

    service_name: str = Field(
        min_length=1,
        max_length=100,
    )


def decode_access_token(
    token: str,
    settings: Settings,
) -> AuthenticatedUser:
    """
    Verify and decode an access token issued by the Auth Service.

    The token is verified for:

    - digital signature
    - issuer
    - audience
    - expiration
    - required claims
    - supported asymmetric algorithm
    - expected user claims

    Args:
        token: Raw JWT without the ``Bearer`` prefix.
        settings: Current service configuration.

    Returns:
        A validated AuthenticatedUser.

    Raises:
        AuthenticationError: When verification or claim validation fails.
    """

    if not token or not token.strip():
        raise AuthenticationError(
            SecurityErrorCode.MISSING_TOKEN,
            "Authentication token is required.",
        )

    try:
        payload = jwt.decode(
            jwt=token,
            key=settings.jwt_public_key_value,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            leeway=settings.jwt_leeway_seconds,
            options={
                "require": settings.jwt_required_claims,
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_nbf": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )

    except ExpiredSignatureError as exc:
        raise AuthenticationError(
            SecurityErrorCode.EXPIRED_TOKEN,
            "Authentication token has expired.",
        ) from exc

    except (
        InvalidAudienceError,
        InvalidIssuerError,
        MissingRequiredClaimError,
        ImmatureSignatureError,
    ) as exc:
        raise AuthenticationError(
            SecurityErrorCode.INVALID_CLAIMS,
            "Authentication token contains invalid claims.",
        ) from exc

    except (
        InvalidSignatureError,
        DecodeError,
        PyJWTError,
    ) as exc:
        raise AuthenticationError(
            SecurityErrorCode.INVALID_TOKEN,
            "Authentication token is invalid.",
        ) from exc

    return _build_authenticated_user(payload)


def _build_authenticated_user(
    payload: dict[str, Any],
) -> AuthenticatedUser:
    """
    Convert verified JWT claims into an AuthenticatedUser.
    """

    try:
        issued_at = datetime.fromtimestamp(
            float(payload["iat"]),
            tz=timezone.utc,
        )

        expires_at = datetime.fromtimestamp(
            float(payload["exp"]),
            tz=timezone.utc,
        )

        return AuthenticatedUser(
            id=payload["sub"],
            email=payload.get("email"),
            roles=payload.get("roles", ["user"]),
            scopes=payload.get(
                "scope",
                payload.get("scopes", []),
            ),
            status=payload.get("status", "active"),
            session_id=payload.get("sid"),
            token_id=payload.get("jti"),
            issued_at=issued_at,
            expires_at=expires_at,
        )

    except (
        KeyError,
        TypeError,
        ValueError,
        ValidationError,
    ) as exc:
        raise AuthenticationError(
            SecurityErrorCode.INVALID_CLAIMS,
            "Authentication token contains malformed user claims.",
        ) from exc


def verify_internal_service(
    *,
    service_name: str | None,
    supplied_token: str | None,
    settings: Settings,
) -> InternalServiceIdentity:
    """
    Verify an internal service-to-service caller.

    Constant-time token comparison is used to avoid leaking useful timing
    information during secret comparison.
    """

    normalized_service_name = (
        service_name.strip().lower()
        if service_name
        else ""
    )

    if (
        not normalized_service_name
        or normalized_service_name
        not in settings.trusted_service_names
    ):
        raise AuthenticationError(
            SecurityErrorCode.UNTRUSTED_SERVICE,
            "Calling service is not trusted.",
        )

    if not supplied_token:
        raise AuthenticationError(
            SecurityErrorCode.INVALID_SERVICE_TOKEN,
            "Internal service token is required.",
        )

    try:
        expected_token = settings.internal_service_token_value
    except RuntimeError as exc:
        raise AuthenticationError(
            SecurityErrorCode.INVALID_SERVICE_TOKEN,
            "Internal service authentication is unavailable.",
        ) from exc

    if not secrets.compare_digest(
        supplied_token.encode("utf-8"),
        expected_token.encode("utf-8"),
    ):
        raise AuthenticationError(
            SecurityErrorCode.INVALID_SERVICE_TOKEN,
            "Internal service token is invalid.",
        )

    return InternalServiceIdentity(
        service_name=normalized_service_name,
    )


def require_roles(
    user: AuthenticatedUser,
    required_roles: set[UserRole],
) -> None:
    """
    Ensure that a user has at least one required role.
    """

    if not user.has_any_role(required_roles):
        raise AuthenticationError(
            SecurityErrorCode.INSUFFICIENT_PERMISSIONS,
            "The authenticated user does not have a required role.",
        )


def require_scopes(
    user: AuthenticatedUser,
    required_scopes: set[str],
) -> None:
    """
    Ensure that a user has every required authorization scope.
    """

    if not user.has_all_scopes(required_scopes):
        raise AuthenticationError(
            SecurityErrorCode.INSUFFICIENT_PERMISSIONS,
            "The authenticated user does not have required permissions.",
        )

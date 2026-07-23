from __future__ import annotations

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
    INVALID_TOKEN_CLAIMS = "invalid_token_claims"
    INACTIVE_USER = "inactive_user"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"


class SecurityError(Exception):
    """
    Transport-independent authentication or authorization failure.
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
    Validated user identity extracted from an access token.

    This model contains authentication context only. It is not a persisted
    user profile or ORM model.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        str_strip_whitespace=True,
    )

    id: UUID

    email: EmailStr | None = None

    roles: frozenset[UserRole] = Field(
        default_factory=lambda: frozenset(
            {UserRole.USER}
        ),
    )

    scopes: frozenset[str] = Field(
        default_factory=frozenset,
    )

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
                item.strip().lower()
                for item in value.replace(",", " ").split()
                if item.strip()
            )

        return frozenset(value)

    @field_validator("scopes", mode="before")
    @classmethod
    def normalize_scopes(cls, value: Any) -> Any:
        if value is None:
            return frozenset()

        if isinstance(value, str):
            return frozenset(
                item.strip()
                for item in value.replace(",", " ").split()
                if item.strip()
            )

        return frozenset(value)

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE

    @property
    def is_admin(self) -> bool:
        return bool(
            self.roles.intersection(
                {
                    UserRole.ADMIN,
                    UserRole.SUPER_ADMIN,
                }
            )
        )

    def has_role(self, role: UserRole) -> bool:
        return role in self.roles

    def has_any_role(
        self,
        roles: set[UserRole],
    ) -> bool:
        return bool(self.roles.intersection(roles))

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    def has_all_scopes(
        self,
        scopes: set[str],
    ) -> bool:
        return scopes.issubset(self.scopes)


def decode_access_token(
    token: str,
    settings: Settings,
) -> AuthenticatedUser:
    """
    Verify a JWT access token and return its user context.

    Validates:

    - cryptographic signature
    - approved asymmetric algorithm
    - issuer
    - audience
    - expiration
    - issued-at and not-before claims
    - required claims
    - user claim types
    """

    normalized_token = token.strip()

    if not normalized_token:
        raise SecurityError(
            SecurityErrorCode.MISSING_TOKEN,
            "Authentication token is required.",
        )

    try:
        payload = jwt.decode(
            jwt=normalized_token,
            key=settings.jwt_public_key_value,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
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
        raise SecurityError(
            SecurityErrorCode.EXPIRED_TOKEN,
            "Authentication token has expired.",
        ) from exc

    except (
        InvalidAudienceError,
        InvalidIssuerError,
        MissingRequiredClaimError,
        ImmatureSignatureError,
    ) as exc:
        raise SecurityError(
            SecurityErrorCode.INVALID_TOKEN_CLAIMS,
            "Authentication token contains invalid claims.",
        ) from exc

    except (
        InvalidSignatureError,
        DecodeError,
        PyJWTError,
    ) as exc:
        raise SecurityError(
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
            status=payload.get(
                "status",
                UserStatus.ACTIVE.value,
            ),
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
        raise SecurityError(
            SecurityErrorCode.INVALID_TOKEN_CLAIMS,
            "Authentication token contains malformed user claims.",
        ) from exc


def require_active_user(
    user: AuthenticatedUser,
) -> None:
    """
    Require an active user account.
    """

    if not user.is_active:
        raise SecurityError(
            SecurityErrorCode.INACTIVE_USER,
            "The authenticated user account is not active.",
        )


def require_roles(
    user: AuthenticatedUser,
    required_roles: set[UserRole],
) -> None:
    """
    Require at least one matching role.
    """

    if not required_roles:
        raise ValueError(
            "At least one required role must be provided."
        )

    if not user.has_any_role(required_roles):
        raise SecurityError(
            SecurityErrorCode.INSUFFICIENT_PERMISSIONS,
            "The authenticated user does not have a required role.",
        )


def require_scopes(
    user: AuthenticatedUser,
    required_scopes: set[str],
) -> None:
    """
    Require every requested authorization scope.
    """

    normalized_scopes = {
        scope.strip()
        for scope in required_scopes
        if scope.strip()
    }

    if not normalized_scopes:
        raise ValueError(
            "At least one required scope must be provided."
        )

    if not user.has_all_scopes(normalized_scopes):
        raise SecurityError(
            SecurityErrorCode.INSUFFICIENT_PERMISSIONS,
            "The authenticated user does not have required permissions.",
        )

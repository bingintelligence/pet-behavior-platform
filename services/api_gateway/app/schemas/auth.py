from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)


class AuthSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
        use_enum_values=False,
    )


class UserRole(StrEnum):
    USER = "user"
    SUPPORT = "support"
    MODERATOR = "moderator"
    ANALYST = "analyst"
    OPERATIONS = "operations"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(StrEnum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    DISABLED = "disabled"
    LOCKED = "locked"
    DELETION_PENDING = "deletion_pending"
    DELETED = "deleted"


class TokenType(StrEnum):
    BEARER = "bearer"


class ClientType(StrEnum):
    WEB = "web"
    MOBILE = "mobile"
    ADMIN = "admin"
    UNKNOWN = "unknown"


def validate_password(password: SecretStr) -> SecretStr:
    value = password.get_secret_value()

    if not any(character.islower() for character in value):
        raise ValueError(
            "Password must contain at least one lowercase letter."
        )

    if not any(character.isupper() for character in value):
        raise ValueError(
            "Password must contain at least one uppercase letter."
        )

    if not any(character.isdigit() for character in value):
        raise ValueError(
            "Password must contain at least one number."
        )

    if not any(not character.isalnum() for character in value):
        raise ValueError(
            "Password must contain at least one special character."
        )

    return password


class RegisterRequest(AuthSchema):
    email: EmailStr
    password: SecretStr = Field(
        min_length=12,
        max_length=128,
    )
    display_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    locale: str = Field(
        default="en-US",
        min_length=2,
        max_length=35,
        pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$",
    )
    timezone: str = Field(
        default="UTC",
        min_length=1,
        max_length=100,
    )
    client_type: ClientType = ClientType.UNKNOWN
    accepted_terms: bool
    accepted_privacy_policy: bool
    marketing_opt_in: bool = False

    @field_validator("password")
    @classmethod
    def validate_registration_password(
        cls,
        password: SecretStr,
    ) -> SecretStr:
        return validate_password(password)

    @model_validator(mode="after")
    def validate_required_consents(self) -> RegisterRequest:
        if not self.accepted_terms:
            raise ValueError(
                "Terms of service must be accepted."
            )

        if not self.accepted_privacy_policy:
            raise ValueError(
                "Privacy policy must be accepted."
            )

        return self


class LoginRequest(AuthSchema):
    email: EmailStr
    password: SecretStr = Field(
        min_length=1,
        max_length=128,
    )
    client_type: ClientType = ClientType.UNKNOWN
    device_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )


class RefreshTokenRequest(AuthSchema):
    refresh_token: str | None = Field(
        default=None,
        min_length=1,
        max_length=8_192,
    )


class ForgotPasswordRequest(AuthSchema):
    email: EmailStr


class ResetPasswordRequest(AuthSchema):
    token: str = Field(
        min_length=1,
        max_length=8_192,
    )
    new_password: SecretStr = Field(
        min_length=12,
        max_length=128,
    )

    @field_validator("new_password")
    @classmethod
    def validate_reset_password(
        cls,
        password: SecretStr,
    ) -> SecretStr:
        return validate_password(password)


class ChangePasswordRequest(AuthSchema):
    current_password: SecretStr = Field(
        min_length=1,
        max_length=128,
    )
    new_password: SecretStr = Field(
        min_length=12,
        max_length=128,
    )
    revoke_other_sessions: bool = True

    @model_validator(mode="after")
    def validate_password_change(self) -> ChangePasswordRequest:
        current_value = self.current_password.get_secret_value()
        new_value = self.new_password.get_secret_value()

        if current_value == new_value:
            raise ValueError(
                "New password must be different from the current password."
            )

        validate_password(self.new_password)

        return self


class UserResponse(AuthSchema):
    id: UUID
    email: EmailStr
    display_name: str | None = None
    status: UserStatus
    roles: list[UserRole] = Field(default_factory=list)
    email_verified: bool
    locale: str
    timezone: str
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None


class AccessTokenResponse(AuthSchema):
    access_token: str = Field(
        min_length=1,
        max_length=8_192,
    )
    refresh_token: str | None = Field(
        default=None,
        min_length=1,
        max_length=8_192,
    )
    token_type: TokenType = TokenType.BEARER
    expires_in: int = Field(gt=0)
    refresh_expires_in: int | None = Field(
        default=None,
        gt=0,
    )
    scope: list[str] = Field(default_factory=list)
    user: UserResponse


class LogoutResponse(AuthSchema):
    logged_out: bool
    revoked_session: bool
    message: str = Field(
        min_length=1,
        max_length=500,
    )


class MessageResponse(AuthSchema):
    message: str = Field(
        min_length=1,
        max_length=1_000,
    )

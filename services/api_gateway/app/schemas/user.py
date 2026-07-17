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

from app.schemas.auth import UserRole, UserStatus


class UserSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
        use_enum_values=False,
    )


class ThemePreference(StrEnum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


class MeasurementSystem(StrEnum):
    METRIC = "metric"
    IMPERIAL = "imperial"


class AnalysisDetailLevel(StrEnum):
    SIMPLE = "simple"
    STANDARD = "standard"
    DETAILED = "detailed"


class UpdateUserProfileRequest(UserSchema):
    display_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    last_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    phone_number: str | None = Field(
        default=None,
        min_length=7,
        max_length=30,
        pattern=r"^\+?[0-9().\-\s]+$",
    )
    avatar_media_id: UUID | None = None
    locale: str | None = Field(
        default=None,
        min_length=2,
        max_length=35,
        pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$",
    )
    timezone: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    @model_validator(mode="after")
    def require_update(self) -> UpdateUserProfileRequest:
        if not self.model_fields_set:
            raise ValueError(
                "At least one profile field must be provided."
            )

        return self


class UserPreferencesResponse(UserSchema):
    user_id: UUID
    email_notifications_enabled: bool
    push_notifications_enabled: bool
    analysis_complete_notifications: bool
    marketing_notifications_enabled: bool
    product_update_notifications: bool
    behavior_reminder_notifications: bool
    theme: ThemePreference
    measurement_system: MeasurementSystem
    analysis_detail_level: AnalysisDetailLevel
    locale: str
    timezone: str
    created_at: datetime
    updated_at: datetime


class UpdateUserPreferencesRequest(UserSchema):
    email_notifications_enabled: bool | None = None
    push_notifications_enabled: bool | None = None
    analysis_complete_notifications: bool | None = None
    marketing_notifications_enabled: bool | None = None
    product_update_notifications: bool | None = None
    behavior_reminder_notifications: bool | None = None
    theme: ThemePreference | None = None
    measurement_system: MeasurementSystem | None = None
    analysis_detail_level: AnalysisDetailLevel | None = None
    locale: str | None = Field(
        default=None,
        min_length=2,
        max_length=35,
        pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$",
    )
    timezone: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    @model_validator(mode="after")
    def require_update(self) -> UpdateUserPreferencesRequest:
        if not self.model_fields_set:
            raise ValueError(
                "At least one preference field must be provided."
            )

        return self


class DeleteAccountRequest(UserSchema):
    password: SecretStr = Field(
        min_length=1,
        max_length=128,
    )
    confirmation: str = Field(
        min_length=1,
        max_length=50,
    )
    reason: str | None = Field(
        default=None,
        max_length=2_000,
    )

    @field_validator("confirmation")
    @classmethod
    def validate_confirmation(
        cls,
        value: str,
    ) -> str:
        if value.strip().upper() != "DELETE":
            raise ValueError(
                'confirmation must equal "DELETE".'
            )

        return "DELETE"


class UserResponse(UserSchema):
    id: UUID
    email: EmailStr
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    avatar_media_id: UUID | None = None
    avatar_url: str | None = None
    locale: str
    timezone: str
    status: UserStatus
    roles: list[UserRole] = Field(default_factory=list)
    email_verified: bool
    phone_verified: bool = False
    pet_count: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None
    disabled_at: datetime | None = None
    deletion_requested_at: datetime | None = None


class UserListResponse(UserSchema):
    items: list[UserResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    has_next: bool
    has_previous: bool


class MessageResponse(UserSchema):
    message: str = Field(
        min_length=1,
        max_length=1_000,
    )
```

---

### `app/schemas/health.py`

```python
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class HealthSchema(BaseModel):
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
    checked_at: datetime | None = None


class HealthResponse(HealthSchema):
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
    dependencies: list[DependencyHealth] = Field(
        default_factory=list,
    )

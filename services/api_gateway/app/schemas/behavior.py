from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class BehaviorSchema(BaseModel):
    """
    Base schema for behavior observation API models.
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
        use_enum_values=False,
    )


class BehaviorType(StrEnum):
    AGGRESSION = "aggression"
    ANXIETY = "anxiety"
    FEAR = "fear"
    EXCITEMENT = "excitement"
    PLAY = "play"
    VOCALIZATION = "vocalization"
    DESTRUCTIVE = "destructive"
    REPETITIVE = "repetitive"
    SOCIAL = "social"
    EATING = "eating"
    SLEEPING = "sleeping"
    ELIMINATION = "elimination"
    MOBILITY = "mobility"
    GROOMING = "grooming"
    OTHER = "other"


class BehaviorSeverity(StrEnum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class BehaviorSource(StrEnum):
    MANUAL = "manual"
    MOBILE_CAPTURE = "mobile_capture"
    WEB_UPLOAD = "web_upload"
    DEVICE = "device"
    IMPORTED = "imported"


class BehaviorStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


def normalize_string_list(values: list[str]) -> list[str]:
    """
    Normalize user-provided string collections.

    Empty entries are removed, surrounding whitespace is stripped, and
    duplicate values are rejected.
    """

    normalized = [
        value.strip()
        for value in values
        if value.strip()
    ]

    if len(normalized) != len(set(normalized)):
        raise ValueError(
            "List values must not contain duplicates."
        )

    for value in normalized:
        if len(value) > 100:
            raise ValueError(
                "List values must be 100 characters or fewer."
            )

    return normalized


class CreateBehaviorRequest(BehaviorSchema):
    """
    Request to create a pet behavior observation.
    """

    pet_id: UUID
    behavior_type: BehaviorType

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    description: str = Field(
        min_length=1,
        max_length=10_000,
    )

    observed_at: datetime

    duration_seconds: float | None = Field(
        default=None,
        gt=0,
        le=86_400,
    )

    severity: BehaviorSeverity = BehaviorSeverity.NONE

    trigger: str | None = Field(
        default=None,
        max_length=2_000,
    )

    location: str | None = Field(
        default=None,
        max_length=500,
    )

    people_present: list[str] = Field(
        default_factory=list,
        max_length=30,
    )

    animals_present: list[str] = Field(
        default_factory=list,
        max_length=30,
    )

    media_ids: list[UUID] = Field(
        default_factory=list,
        max_length=20,
    )

    source: BehaviorSource = BehaviorSource.MANUAL

    tags: list[str] = Field(
        default_factory=list,
        max_length=30,
    )

    notes: str | None = Field(
        default=None,
        max_length=5_000,
    )

    @field_validator(
        "people_present",
        "animals_present",
        "tags",
    )
    @classmethod
    def validate_string_lists(
        cls,
        values: list[str],
    ) -> list[str]:
        return normalize_string_list(values)

    @model_validator(mode="after")
    def validate_behavior(self) -> CreateBehaviorRequest:
        if len(self.media_ids) != len(set(self.media_ids)):
            raise ValueError(
                "media_ids must not contain duplicate values."
            )

        return self


class UpdateBehaviorRequest(BehaviorSchema):
    """
    Partial update for an existing behavior observation.
    """

    behavior_type: BehaviorType | None = None

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    description: str | None = Field(
        default=None,
        min_length=1,
        max_length=10_000,
    )

    observed_at: datetime | None = None

    duration_seconds: float | None = Field(
        default=None,
        gt=0,
        le=86_400,
    )

    severity: BehaviorSeverity | None = None

    trigger: str | None = Field(
        default=None,
        max_length=2_000,
    )

    location: str | None = Field(
        default=None,
        max_length=500,
    )

    people_present: list[str] | None = Field(
        default=None,
        max_length=30,
    )

    animals_present: list[str] | None = Field(
        default=None,
        max_length=30,
    )

    media_ids: list[UUID] | None = Field(
        default=None,
        max_length=20,
    )

    tags: list[str] | None = Field(
        default=None,
        max_length=30,
    )

    notes: str | None = Field(
        default=None,
        max_length=5_000,
    )

    status: BehaviorStatus | None = None

    @field_validator(
        "people_present",
        "animals_present",
        "tags",
    )
    @classmethod
    def validate_string_lists(
        cls,
        values: list[str] | None,
    ) -> list[str] | None:
        if values is None:
            return None

        return normalize_string_list(values)

    @model_validator(mode="after")
    def validate_update(self) -> UpdateBehaviorRequest:
        if not self.model_fields_set:
            raise ValueError(
                "At least one behavior field must be provided."
            )

        if (
            self.media_ids is not None
            and len(self.media_ids) != len(set(self.media_ids))
        ):
            raise ValueError(
                "media_ids must not contain duplicate values."
            )

        return self


class BehaviorResponse(BehaviorSchema):
    """
    Public representation of a behavior observation.
    """

    id: UUID
    user_id: UUID
    pet_id: UUID

    behavior_type: BehaviorType
    title: str | None = None
    description: str
    observed_at: datetime
    duration_seconds: float | None = None
    severity: BehaviorSeverity

    trigger: str | None = None
    location: str | None = None

    people_present: list[str] = Field(default_factory=list)
    animals_present: list[str] = Field(default_factory=list)
    media_ids: list[UUID] = Field(default_factory=list)

    source: BehaviorSource
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None

    status: BehaviorStatus
    analysis_count: int = Field(default=0, ge=0)

    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class BehaviorListResponse(BehaviorSchema):
    """
    Paginated collection of behavior observations.
    """

    items: list[BehaviorResponse]

    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)

    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)

    has_next: bool
    has_previous: bool


class BehaviorTimelineItem(BehaviorSchema):
    """
    Lightweight behavior representation used in a pet timeline.
    """

    id: UUID
    behavior_type: BehaviorType
    title: str | None = None
    severity: BehaviorSeverity
    observed_at: datetime
    duration_seconds: float | None = None
    media_ids: list[UUID] = Field(default_factory=list)
    analysis_count: int = Field(default=0, ge=0)


class BehaviorTimelineResponse(BehaviorSchema):
    """
    Chronological behavior timeline for a pet.
    """

    pet_id: UUID
    items: list[BehaviorTimelineItem]

    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)

    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)

    has_next: bool
    has_previous: bool

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class PetSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
        use_enum_values=False,
    )


class PetSpecies(StrEnum):
    DOG = "dog"
    CAT = "cat"
    BIRD = "bird"
    RABBIT = "rabbit"
    OTHER = "other"


class PetSex(StrEnum):
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class PetSize(StrEnum):
    EXTRA_SMALL = "extra_small"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    EXTRA_LARGE = "extra_large"
    UNKNOWN = "unknown"


class PetStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"


def normalize_tags(tags: list[str]) -> list[str]:
    normalized = [
        tag.strip().lower()
        for tag in tags
        if tag.strip()
    ]

    if len(normalized) != len(set(normalized)):
        raise ValueError(
            "tags must not contain duplicate values."
        )

    for tag in normalized:
        if len(tag) > 50:
            raise ValueError(
                "Each tag must be 50 characters or fewer."
            )

    return normalized


class CreatePetRequest(PetSchema):
    name: str = Field(
        min_length=1,
        max_length=100,
    )
    species: PetSpecies
    breed: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )
    mixed_breed: bool = False
    sex: PetSex = PetSex.UNKNOWN
    date_of_birth: date | None = None
    approximate_age_months: int | None = Field(
        default=None,
        ge=0,
        le=600,
    )
    weight_kg: float | None = Field(
        default=None,
        gt=0,
        le=500,
    )
    size: PetSize = PetSize.UNKNOWN
    color: str | None = Field(
        default=None,
        max_length=100,
    )
    microchip_id: str | None = Field(
        default=None,
        min_length=5,
        max_length=50,
    )
    is_neutered: bool | None = None
    medical_notes: str | None = Field(
        default=None,
        max_length=5_000,
    )
    behavioral_notes: str | None = Field(
        default=None,
        max_length=5_000,
    )
    avatar_media_id: UUID | None = None
    tags: list[str] = Field(
        default_factory=list,
        max_length=30,
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(
        cls,
        tags: list[str],
    ) -> list[str]:
        return normalize_tags(tags)

    @model_validator(mode="after")
    def validate_age_information(self) -> CreatePetRequest:
        if self.date_of_birth and self.date_of_birth > date.today():
            raise ValueError(
                "date_of_birth must not be in the future."
            )

        if (
            self.date_of_birth is not None
            and self.approximate_age_months is not None
        ):
            raise ValueError(
                "Provide either date_of_birth or approximate_age_months, "
                "not both."
            )

        return self


class UpdatePetRequest(PetSchema):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    species: PetSpecies | None = None
    breed: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )
    mixed_breed: bool | None = None
    sex: PetSex | None = None
    date_of_birth: date | None = None
    approximate_age_months: int | None = Field(
        default=None,
        ge=0,
        le=600,
    )
    weight_kg: float | None = Field(
        default=None,
        gt=0,
        le=500,
    )
    size: PetSize | None = None
    color: str | None = Field(
        default=None,
        max_length=100,
    )
    microchip_id: str | None = Field(
        default=None,
        min_length=5,
        max_length=50,
    )
    is_neutered: bool | None = None
    medical_notes: str | None = Field(
        default=None,
        max_length=5_000,
    )
    behavioral_notes: str | None = Field(
        default=None,
        max_length=5_000,
    )
    avatar_media_id: UUID | None = None
    tags: list[str] | None = Field(
        default=None,
        max_length=30,
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(
        cls,
        tags: list[str] | None,
    ) -> list[str] | None:
        if tags is None:
            return None

        return normalize_tags(tags)

    @model_validator(mode="after")
    def validate_update(self) -> UpdatePetRequest:
        if not self.model_fields_set:
            raise ValueError(
                "At least one pet profile field must be provided."
            )

        if (
            self.date_of_birth is not None
            and self.date_of_birth > date.today()
        ):
            raise ValueError(
                "date_of_birth must not be in the future."
            )

        if (
            self.date_of_birth is not None
            and self.approximate_age_months is not None
        ):
            raise ValueError(
                "Provide either date_of_birth or approximate_age_months, "
                "not both."
            )

        return self


class PetResponse(PetSchema):
    id: UUID
    user_id: UUID
    name: str
    species: PetSpecies
    breed: str | None = None
    mixed_breed: bool
    sex: PetSex
    date_of_birth: date | None = None
    approximate_age_months: int | None = None
    weight_kg: float | None = None
    size: PetSize
    color: str | None = None
    microchip_id: str | None = None
    is_neutered: bool | None = None
    medical_notes: str | None = None
    behavioral_notes: str | None = None
    avatar_media_id: UUID | None = None
    avatar_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    status: PetStatus
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class PetListResponse(PetSchema):
    items: list[PetResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    has_next: bool
    has_previous: bool
```

---

### `app/schemas/behavior.py`

```python
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
    def validate_media_ids(self) -> CreateBehaviorRequest:
        if len(self.media_ids) != len(set(self.media_ids)):
            raise ValueError(
                "media_ids must not contain duplicate values."
            )

        return self


class UpdateBehaviorRequest(BehaviorSchema):
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
    items: list[BehaviorResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    has_next: bool
    has_previous: bool

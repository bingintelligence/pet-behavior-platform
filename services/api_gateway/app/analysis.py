from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AnalysisSchema(BaseModel):
    """
    Base schema for analysis API models.

    Unknown fields are rejected so that accidental or unsupported client
    input does not silently pass through the API Gateway.
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
        use_enum_values=False,
    )


class AnalysisType(StrEnum):
    """
    Supported analysis pipeline categories.

    The exact pipelines may evolve independently inside the Analysis Service,
    but these values form the public API contract.
    """

    BEHAVIOR = "behavior"
    EMOTION = "emotion"
    POSTURE = "posture"
    ACTIVITY = "activity"
    VOCALIZATION = "vocalization"
    MULTIMODAL = "multimodal"


class AnalysisStatus(StrEnum):
    """
    Public lifecycle states for an analysis request.
    """

    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"


class AnalysisPriority(StrEnum):
    """
    Public processing-priority options.

    The Analysis Service remains responsible for enforcing whether a user's
    plan is allowed to request a particular priority.
    """

    STANDARD = "standard"
    HIGH = "high"


class AnalysisSourceType(StrEnum):
    """
    Identifies the primary source attached to the analysis.
    """

    BEHAVIOR = "behavior"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"
    MIXED = "mixed"


class CreateAnalysisRequest(AnalysisSchema):
    """
    Request submitted by a user to start an asynchronous analysis.

    At least one of behavior_id, media_ids, or description must be supplied.
    Ownership and media readiness are validated by the Analysis Service.
    """

    pet_id: UUID
    analysis_type: AnalysisType = AnalysisType.BEHAVIOR
    behavior_id: UUID | None = None
    media_ids: list[UUID] = Field(default_factory=list, max_length=10)
    description: str | None = Field(
        default=None,
        min_length=1,
        max_length=5_000,
    )
    priority: AnalysisPriority = AnalysisPriority.STANDARD
    locale: str = Field(
        default="en-US",
        min_length=2,
        max_length=35,
        pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$",
    )
    requested_features: list[str] = Field(
        default_factory=list,
        max_length=20,
    )
    client_metadata: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Small, non-sensitive client metadata. This field must not contain "
            "tokens, credentials, raw media, or personal information."
        ),
    )

    @model_validator(mode="after")
    def validate_analysis_source(self) -> CreateAnalysisRequest:
        has_description = bool(self.description and self.description.strip())

        if not self.behavior_id and not self.media_ids and not has_description:
            raise ValueError(
                "At least one of behavior_id, media_ids, or description "
                "must be provided."
            )

        if len(set(self.media_ids)) != len(self.media_ids):
            raise ValueError("media_ids must not contain duplicate values.")

        return self


class AnalysisProgress(AnalysisSchema):
    """
    Processing progress reported by the asynchronous analysis pipeline.
    """

    percent: int = Field(ge=0, le=100)
    stage: str | None = Field(default=None, max_length=100)
    message: str | None = Field(default=None, max_length=500)
    updated_at: datetime


class AnalysisFinding(AnalysisSchema):
    """
    One structured finding produced by an analysis pipeline.
    """

    code: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2_000)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    severity: str | None = Field(default=None, max_length=50)
    start_seconds: float | None = Field(default=None, ge=0.0)
    end_seconds: float | None = Field(default=None, ge=0.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_time_range(self) -> AnalysisFinding:
        if (
            self.start_seconds is not None
            and self.end_seconds is not None
            and self.end_seconds < self.start_seconds
        ):
            raise ValueError(
                "end_seconds must be greater than or equal to start_seconds."
            )

        return self


class AnalysisRecommendation(AnalysisSchema):
    """
    Informational recommendation generated from analysis findings.
    """

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2_000)
    priority: str | None = Field(default=None, max_length=50)
    disclaimer: str | None = Field(default=None, max_length=1_000)


class AnalysisResult(AnalysisSchema):
    """
    Structured result returned after successful processing.

    This model intentionally avoids prescribing every model-specific output.
    Pipeline-specific information may be placed in metadata while stable,
    user-facing findings remain strongly typed.
    """

    summary: str = Field(min_length=1, max_length=10_000)
    findings: list[AnalysisFinding] = Field(default_factory=list)
    recommendations: list[AnalysisRecommendation] = Field(
        default_factory=list,
    )
    overall_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    model_name: str | None = Field(default=None, max_length=200)
    model_version: str | None = Field(default=None, max_length=100)
    prompt_version: str | None = Field(default=None, max_length=100)
    completed_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalysisError(AnalysisSchema):
    """
    Safe error information that may be shown to API clients.

    Internal stack traces, provider responses, object-storage locations, and
    infrastructure details must not be exposed through this model.
    """

    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=1_000)
    retryable: bool = False


class AnalysisResponse(AnalysisSchema):
    """
    Public representation of an analysis request.
    """

    id: UUID
    user_id: UUID
    pet_id: UUID
    behavior_id: UUID | None = None
    media_ids: list[UUID] = Field(default_factory=list)
    analysis_type: AnalysisType
    source_type: AnalysisSourceType
    status: AnalysisStatus
    priority: AnalysisPriority = AnalysisPriority.STANDARD
    locale: str
    requested_features: list[str] = Field(default_factory=list)
    progress: AnalysisProgress | None = None
    result: AnalysisResult | None = None
    error: AnalysisError | None = None
    attempt_count: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None


class AnalysisListResponse(AnalysisSchema):
    """
    Paginated analysis collection.
    """

    items: list[AnalysisResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    has_next: bool
    has_previous: bool


class CancelAnalysisResponse(AnalysisSchema):
    """
    Response returned after an analysis cancellation request.
    """

    analysis_id: UUID
    status: AnalysisStatus
    cancellation_requested: bool
    message: str = Field(min_length=1, max_length=500)


class RetryAnalysisResponse(AnalysisSchema):
    """
    Response returned after a failed analysis is submitted for retry.

    A retry may create a new analysis identifier or another processing attempt
    under the existing analysis record. The response supports both designs.
    """

    analysis_id: UUID
    original_analysis_id: UUID
    status: AnalysisStatus
    attempt_count: int = Field(ge=1)
    message: str = Field(min_length=1, max_length=500)

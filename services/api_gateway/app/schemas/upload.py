from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class UploadSchema(BaseModel):
    """
    Base schema for media-upload API models.
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
        use_enum_values=False,
    )


class MediaType(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class UploadStatus(StrEnum):
    CREATED = "created"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    VERIFYING = "verifying"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    ABORTED = "aborted"
    DELETED = "deleted"


class UploadMethod(StrEnum):
    SINGLE_PART = "single_part"
    MULTIPART = "multipart"


class MediaProcessingStatus(StrEnum):
    NOT_STARTED = "not_started"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class CreateUploadRequest(UploadSchema):
    """
    Request to create a direct-to-object-storage upload session.

    The Media Service must validate the declared metadata and independently
    verify the actual object after upload completion.
    """

    pet_id: UUID
    filename: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[^/\\\x00]+$",
    )
    media_type: MediaType
    content_type: str = Field(
        min_length=3,
        max_length=150,
        pattern=r"^[A-Za-z0-9.+-]+/[A-Za-z0-9.+-]+$",
    )
    size_bytes: int = Field(gt=0, le=2_147_483_648)
    checksum_sha256: str | None = Field(
        default=None,
        pattern=r"^[a-fA-F0-9]{64}$",
    )
    duration_seconds: float | None = Field(
        default=None,
        gt=0,
        le=3_600,
    )
    captured_at: datetime | None = None
    purpose: str = Field(
        default="behavior_analysis",
        min_length=1,
        max_length=100,
    )
    client_metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_media_metadata(self) -> CreateUploadRequest:
        expected_prefix = {
            MediaType.IMAGE: "image/",
            MediaType.VIDEO: "video/",
            MediaType.AUDIO: "audio/",
        }[self.media_type]

        if not self.content_type.lower().startswith(expected_prefix):
            raise ValueError(
                f"content_type must start with {expected_prefix!r} "
                f"for media_type={self.media_type.value!r}."
            )

        if self.media_type is MediaType.IMAGE and self.duration_seconds:
            raise ValueError(
                "duration_seconds must not be provided for image uploads."
            )

        return self


class MultipartUploadPart(UploadSchema):
    """
    One signed multipart-upload part.
    """

    part_number: int = Field(ge=1, le=10_000)
    upload_url: HttpUrl
    expires_at: datetime
    required_headers: dict[str, str] = Field(default_factory=dict)


class UploadSessionResponse(UploadSchema):
    """
    Upload instructions returned to the client.

    For single-part uploads, upload_url is populated. For multipart uploads,
    multipart_parts contains the initial signed part instructions.
    """

    upload_id: UUID
    media_id: UUID
    method: UploadMethod
    status: UploadStatus
    upload_url: HttpUrl | None = None
    multipart_upload_id: str | None = Field(
        default=None,
        max_length=500,
    )
    multipart_parts: list[MultipartUploadPart] = Field(
        default_factory=list,
    )
    required_headers: dict[str, str] = Field(default_factory=dict)
    expires_at: datetime
    max_part_size_bytes: int | None = Field(default=None, gt=0)
    min_part_size_bytes: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_upload_instructions(self) -> UploadSessionResponse:
        if self.method is UploadMethod.SINGLE_PART and not self.upload_url:
            raise ValueError(
                "upload_url is required for single-part uploads."
            )

        if self.method is UploadMethod.MULTIPART:
            if not self.multipart_upload_id:
                raise ValueError(
                    "multipart_upload_id is required for multipart uploads."
                )

            if self.upload_url:
                raise ValueError(
                    "upload_url must not be set for multipart uploads."
                )

        return self


class CompletedUploadPart(UploadSchema):
    """
    Multipart-upload part metadata returned by object storage.
    """

    part_number: int = Field(ge=1, le=10_000)
    etag: str = Field(min_length=1, max_length=500)
    checksum_sha256: str | None = Field(
        default=None,
        pattern=r"^[a-fA-F0-9]{64}$",
    )


class CompleteUploadRequest(UploadSchema):
    """
    Request sent after the client finishes uploading the object.

    For multipart uploads, parts must contain the completed part numbers and
    corresponding ETags. The Media Service must not rely solely on these values;
    it should verify the final object directly with object storage.
    """

    parts: list[CompletedUploadPart] = Field(
        default_factory=list,
        max_length=10_000,
    )
    checksum_sha256: str | None = Field(
        default=None,
        pattern=r"^[a-fA-F0-9]{64}$",
    )
    size_bytes: int | None = Field(
        default=None,
        gt=0,
        le=2_147_483_648,
    )

    @model_validator(mode="after")
    def validate_completed_parts(self) -> CompleteUploadRequest:
        part_numbers = [part.part_number for part in self.parts]

        if len(part_numbers) != len(set(part_numbers)):
            raise ValueError(
                "Multipart completion contains duplicate part numbers."
            )

        if part_numbers and part_numbers != sorted(part_numbers):
            raise ValueError(
                "Multipart completion parts must be ordered by part_number."
            )

        return self


class MediaVariant(UploadSchema):
    """
    Generated media artifact such as a thumbnail or transcoded preview.
    """

    name: str = Field(min_length=1, max_length=100)
    content_type: str = Field(min_length=3, max_length=150)
    size_bytes: int = Field(ge=0)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    duration_seconds: float | None = Field(default=None, ge=0)
    access_url: HttpUrl | None = None
    access_url_expires_at: datetime | None = None


class MediaError(UploadSchema):
    """
    Safe media-processing error information.
    """

    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=1_000)
    retryable: bool = False


class MediaResponse(UploadSchema):
    """
    Public representation of uploaded media.

    storage_key and storage bucket information are intentionally excluded from
    the public schema.
    """

    id: UUID
    upload_id: UUID
    user_id: UUID
    pet_id: UUID
    filename: str
    media_type: MediaType
    content_type: str
    size_bytes: int = Field(ge=0)
    checksum_sha256: str | None = None
    status: UploadStatus
    processing_status: MediaProcessingStatus
    duration_seconds: float | None = Field(default=None, ge=0)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    captured_at: datetime | None = None
    access_url: HttpUrl | None = None
    access_url_expires_at: datetime | None = None
    variants: list[MediaVariant] = Field(default_factory=list)
    error: MediaError | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    uploaded_at: datetime | None = None
    ready_at: datetime | None = None


class UploadListResponse(UploadSchema):
    """
    Paginated uploaded-media collection.
    """

    items: list[MediaResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    has_next: bool
    has_previous: bool


class AbortUploadResponse(UploadSchema):
    """
    Response returned after an incomplete upload is aborted.
    """

    upload_id: UUID
    media_id: UUID
    status: UploadStatus
    aborted: bool
    message: str = Field(min_length=1, max_length=500)

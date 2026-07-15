from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.core.dependencies import (
    get_current_user,
    get_media_client,
)
from app.schemas.upload import (
    AbortUploadResponse,
    CompleteUploadRequest,
    CreateUploadRequest,
    MediaResponse,
    UploadListResponse,
    UploadSessionResponse,
)
from app.services.media_client import MediaClient
from shared.schemas.auth import AuthenticatedUser

router = APIRouter(
    prefix="/uploads",
    tags=["Uploads"],
)

MediaClientDependency = Annotated[
    MediaClient,
    Depends(get_media_client),
]

CurrentUserDependency = Annotated[
    AuthenticatedUser,
    Depends(get_current_user),
]


@router.post(
    "",
    response_model=UploadSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an upload session",
)
async def create_upload(
    payload: CreateUploadRequest,
    request: Request,
    media_client: MediaClientDependency,
    current_user: CurrentUserDependency,
) -> UploadSessionResponse:
    """
    Create a direct-to-object-storage upload session.

    The Media Service should validate:

    - pet ownership;
    - supported media type;
    - filename and MIME type;
    - declared file size;
    - account storage quota;
    - upload and subscription limits.

    The response may contain a presigned PUT URL or multipart-upload
    instructions. The file itself should not pass through the API Gateway.
    """
    return await media_client.create_upload(
        user_id=current_user.user_id,
        payload=payload,
        request_id=_get_request_id(request),
        idempotency_key=request.headers.get("idempotency-key"),
    )


@router.get(
    "",
    response_model=UploadListResponse,
    status_code=status.HTTP_200_OK,
    summary="List uploaded media",
)
async def list_uploads(
    request: Request,
    media_client: MediaClientDependency,
    current_user: CurrentUserDependency,
    pet_id: UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> UploadListResponse:
    """
    Return media uploaded by the authenticated user.
    """
    normalized_page = max(page, 1)
    normalized_page_size = min(max(page_size, 1), 100)

    return await media_client.list_uploads(
        user_id=current_user.user_id,
        pet_id=pet_id,
        page=normalized_page,
        page_size=normalized_page_size,
        request_id=_get_request_id(request),
    )


@router.post(
    "/{upload_id}/complete",
    response_model=MediaResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete an upload",
)
async def complete_upload(
    upload_id: UUID,
    payload: CompleteUploadRequest,
    request: Request,
    media_client: MediaClientDependency,
    current_user: CurrentUserDependency,
) -> MediaResponse:
    """
    Mark a direct upload as complete.

    The Media Service should verify the object exists and validate server-side
    metadata such as object size, checksum and content type. It may then enqueue
    malware scanning, media probing, transcoding or thumbnail generation.
    """
    return await media_client.complete_upload(
        user_id=current_user.user_id,
        upload_id=upload_id,
        payload=payload,
        request_id=_get_request_id(request),
        idempotency_key=request.headers.get("idempotency-key"),
    )


@router.post(
    "/{upload_id}/abort",
    response_model=AbortUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Abort an upload",
)
async def abort_upload(
    upload_id: UUID,
    request: Request,
    media_client: MediaClientDependency,
    current_user: CurrentUserDependency,
) -> AbortUploadResponse:
    """
    Abort an incomplete upload session.

    For multipart uploads, the Media Service should also abort the underlying
    object-storage multipart transaction.
    """
    return await media_client.abort_upload(
        user_id=current_user.user_id,
        upload_id=upload_id,
        request_id=_get_request_id(request),
    )


@router.get(
    "/{upload_id}",
    response_model=MediaResponse,
    status_code=status.HTTP_200_OK,
    summary="Get uploaded media metadata",
)
async def get_upload(
    upload_id: UUID,
    request: Request,
    media_client: MediaClientDependency,
    current_user: CurrentUserDependency,
) -> MediaResponse:
    """
    Return uploaded media metadata.

    Private object-storage keys should not be returned directly. When media
    access is needed, the Media Service may return a short-lived signed URL.
    """
    return await media_client.get_upload(
        user_id=current_user.user_id,
        upload_id=upload_id,
        request_id=_get_request_id(request),
    )


@router.delete(
    "/{upload_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete uploaded media",
)
async def delete_upload(
    upload_id: UUID,
    request: Request,
    media_client: MediaClientDependency,
    current_user: CurrentUserDependency,
) -> None:
    """
    Delete uploaded media.

    The Media Service should prevent unsafe deletion when the media is actively
    referenced by a running analysis, or apply an appropriate retention policy.
    """
    await media_client.delete_upload(
        user_id=current_user.user_id,
        upload_id=upload_id,
        request_id=_get_request_id(request),
    )


def _get_request_id(request: Request) -> str | None:
    """
    Return the request ID generated by request-ID middleware.
    """
    return getattr(request.state, "request_id", None)

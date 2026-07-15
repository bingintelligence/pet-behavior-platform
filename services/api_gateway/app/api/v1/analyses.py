from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.dependencies import (
    get_analysis_client,
    get_current_user,
)
from app.schemas.analysis import (
    AnalysisListResponse,
    AnalysisResponse,
    AnalysisStatus,
    CancelAnalysisResponse,
    CreateAnalysisRequest,
    RetryAnalysisResponse,
)
from app.services.analysis_client import AnalysisClient
from shared.schemas.auth import AuthenticatedUser

router = APIRouter(
    prefix="/analyses",
    tags=["Analyses"],
)

AnalysisClientDependency = Annotated[
    AnalysisClient,
    Depends(get_analysis_client),
]

CurrentUserDependency = Annotated[
    AuthenticatedUser,
    Depends(get_current_user),
]


@router.post(
    "",
    response_model=AnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit an analysis request",
)
async def create_analysis(
    payload: CreateAnalysisRequest,
    request: Request,
    analysis_client: AnalysisClientDependency,
    current_user: CurrentUserDependency,
) -> AnalysisResponse:
    """
    Submit a pet behavior analysis request.

    The Analysis Service is responsible for:

    - validating pet and behavior ownership;
    - validating referenced media;
    - enforcing subscription and usage limits;
    - creating the analysis record;
    - publishing the asynchronous analysis job;
    - selecting the appropriate model or pipeline.

    A successful response means the analysis was accepted, not completed.
    """
    return await analysis_client.create_analysis(
        user_id=current_user.user_id,
        payload=payload,
        request_id=_get_request_id(request),
        idempotency_key=request.headers.get("idempotency-key"),
    )


@router.get(
    "",
    response_model=AnalysisListResponse,
    status_code=status.HTTP_200_OK,
    summary="List analyses",
)
async def list_analyses(
    request: Request,
    analysis_client: AnalysisClientDependency,
    current_user: CurrentUserDependency,
    pet_id: UUID | None = None,
    behavior_id: UUID | None = None,
    analysis_status: Annotated[
        AnalysisStatus | None,
        Query(alias="status"),
    ] = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AnalysisListResponse:
    """
    Return a paginated list of analyses owned by the authenticated user.
    """
    return await analysis_client.list_analyses(
        user_id=current_user.user_id,
        pet_id=pet_id,
        behavior_id=behavior_id,
        analysis_status=analysis_status,
        created_after=created_after,
        created_before=created_before,
        page=page,
        page_size=page_size,
        request_id=_get_request_id(request),
    )


@router.get(
    "/pets/{pet_id}/latest",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the latest analysis for a pet",
)
async def get_latest_pet_analysis(
    pet_id: UUID,
    request: Request,
    analysis_client: AnalysisClientDependency,
    current_user: CurrentUserDependency,
) -> AnalysisResponse:
    """
    Return the most recently created analysis for the specified pet.

    The Analysis Service must verify that the authenticated user may access the
    pet and its analysis history.
    """
    return await analysis_client.get_latest_pet_analysis(
        user_id=current_user.user_id,
        pet_id=pet_id,
        request_id=_get_request_id(request),
    )


@router.get(
    "/{analysis_id}",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Get an analysis",
)
async def get_analysis(
    analysis_id: UUID,
    request: Request,
    analysis_client: AnalysisClientDependency,
    current_user: CurrentUserDependency,
) -> AnalysisResponse:
    """
    Return analysis status, metadata, and result data when available.
    """
    return await analysis_client.get_analysis(
        user_id=current_user.user_id,
        analysis_id=analysis_id,
        request_id=_get_request_id(request),
    )


@router.post(
    "/{analysis_id}/cancel",
    response_model=CancelAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel an analysis",
)
async def cancel_analysis(
    analysis_id: UUID,
    request: Request,
    analysis_client: AnalysisClientDependency,
    current_user: CurrentUserDependency,
) -> CancelAnalysisResponse:
    """
    Request cancellation of a queued or running analysis.

    Cancellation is best effort. The Analysis Service decides whether the
    analysis is still cancellable and coordinates with the worker system.
    """
    return await analysis_client.cancel_analysis(
        user_id=current_user.user_id,
        analysis_id=analysis_id,
        request_id=_get_request_id(request),
    )


@router.post(
    "/{analysis_id}/retry",
    response_model=RetryAnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Retry a failed analysis",
)
async def retry_analysis(
    analysis_id: UUID,
    request: Request,
    analysis_client: AnalysisClientDependency,
    current_user: CurrentUserDependency,
) -> RetryAnalysisResponse:
    """
    Retry an analysis that previously failed.

    The Analysis Service should validate retry eligibility, enforce retry
    limits, and generate a new processing attempt.
    """
    return await analysis_client.retry_analysis(
        user_id=current_user.user_id,
        analysis_id=analysis_id,
        request_id=_get_request_id(request),
        idempotency_key=request.headers.get("idempotency-key"),
    )


@router.delete(
    "/{analysis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an analysis",
)
async def delete_analysis(
    analysis_id: UUID,
    request: Request,
    analysis_client: AnalysisClientDependency,
    current_user: CurrentUserDependency,
) -> None:
    """
    Delete or hide an analysis from the user's history.

    The Analysis Service determines retention behavior and whether associated
    generated artifacts should also be deleted.
    """
    await analysis_client.delete_analysis(
        user_id=current_user.user_id,
        analysis_id=analysis_id,
        request_id=_get_request_id(request),
    )


def _get_request_id(request: Request) -> str | None:
    """
    Return the request ID generated by request-ID middleware.
    """
    return getattr(request.state, "request_id", None)

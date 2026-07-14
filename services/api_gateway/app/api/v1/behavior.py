from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.dependencies import (
    get_behavior_client,
    get_current_user,
)
from app.schemas.behavior import (
    BehaviorListResponse,
    BehaviorResponse,
    CreateBehaviorRequest,
    UpdateBehaviorRequest,
)
from app.services.behavior_client import BehaviorClient
from shared.schemas.auth import AuthenticatedUser

router = APIRouter(
    prefix="/behaviors",
    tags=["Behaviors"],
)

BehaviorClientDependency = Annotated[
    BehaviorClient,
    Depends(get_behavior_client),
]

CurrentUserDependency = Annotated[
    AuthenticatedUser,
    Depends(get_current_user),
]


@router.post(
    "",
    response_model=BehaviorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a behavior observation",
)
async def create_behavior(
    payload: CreateBehaviorRequest,
    request: Request,
    behavior_client: BehaviorClientDependency,
    current_user: CurrentUserDependency,
) -> BehaviorResponse:
    """
    Create a behavior observation for one of the user's pets.

    The Behavior Service must validate pet ownership and any referenced media.
    Creating an observation does not necessarily start AI analysis unless the
    downstream service is configured to do so.
    """
    return await behavior_client.create_behavior(
        user_id=current_user.user_id,
        payload=payload,
        request_id=_get_request_id(request),
    )


@router.get(
    "",
    response_model=BehaviorListResponse,
    status_code=status.HTTP_200_OK,
    summary="List behavior observations",
)
async def list_behaviors(
    request: Request,
    behavior_client: BehaviorClientDependency,
    current_user: CurrentUserDependency,
    pet_id: UUID | None = None,
    behavior_type: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> BehaviorListResponse:
    """
    Return behavior observations belonging to the authenticated user.

    Results may be filtered by pet, behavior type, or observation time.
    """
    return await behavior_client.list_behaviors(
        user_id=current_user.user_id,
        pet_id=pet_id,
        behavior_type=behavior_type,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
        request_id=_get_request_id(request),
    )


@router.get(
    "/{behavior_id}",
    response_model=BehaviorResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a behavior observation",
)
async def get_behavior(
    behavior_id: UUID,
    request: Request,
    behavior_client: BehaviorClientDependency,
    current_user: CurrentUserDependency,
) -> BehaviorResponse:
    """
    Return a behavior observation.

    The Behavior Service is responsible for verifying that the user has access
    to the behavior and its related pet and media.
    """
    return await behavior_client.get_behavior(
        user_id=current_user.user_id,
        behavior_id=behavior_id,
        request_id=_get_request_id(request),
    )


@router.patch(
    "/{behavior_id}",
    response_model=BehaviorResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a behavior observation",
)
async def update_behavior(
    behavior_id: UUID,
    payload: UpdateBehaviorRequest,
    request: Request,
    behavior_client: BehaviorClientDependency,
    current_user: CurrentUserDependency,
) -> BehaviorResponse:
    """
    Partially update a behavior observation.

    Analysis-generated fields should generally not be editable through this
    endpoint. The Behavior Service enforces the allowed field set.
    """
    return await behavior_client.update_behavior(
        user_id=current_user.user_id,
        behavior_id=behavior_id,
        payload=payload,
        request_id=_get_request_id(request),
    )


@router.delete(
    "/{behavior_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a behavior observation",
)
async def delete_behavior(
    behavior_id: UUID,
    request: Request,
    behavior_client: BehaviorClientDependency,
    current_user: CurrentUserDependency,
) -> None:
    """
    Delete or deactivate a behavior observation.

    The Behavior Service must safely handle related media and analysis records.
    """
    await behavior_client.delete_behavior(
        user_id=current_user.user_id,
        behavior_id=behavior_id,
        request_id=_get_request_id(request),
    )


@router.get(
    "/pets/{pet_id}/timeline",
    response_model=BehaviorListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a pet's behavior timeline",
)
async def get_pet_behavior_timeline(
    pet_id: UUID,
    request: Request,
    behavior_client: BehaviorClientDependency,
    current_user: CurrentUserDependency,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> BehaviorListResponse:
    """
    Return a chronological behavior timeline for a pet.
    """
    return await behavior_client.get_pet_timeline(
        user_id=current_user.user_id,
        pet_id=pet_id,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
        request_id=_get_request_id(request),
    )


def _get_request_id(request: Request) -> str | None:
    """
    Return the request ID created by request-ID middleware.
    """
    return getattr(request.state, "request_id", None)
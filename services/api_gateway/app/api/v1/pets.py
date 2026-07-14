from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.dependencies import get_current_user, get_pet_client
from app.schemas.pet import (
    CreatePetRequest,
    PetListResponse,
    PetResponse,
    UpdatePetRequest,
)
from app.services.pet_client import PetClient
from shared.schemas.auth import AuthenticatedUser

router = APIRouter(
    prefix="/pets",
    tags=["Pets"],
)

PetClientDependency = Annotated[
    PetClient,
    Depends(get_pet_client),
]

CurrentUserDependency = Annotated[
    AuthenticatedUser,
    Depends(get_current_user),
]


@router.post(
    "",
    response_model=PetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a pet profile",
)
async def create_pet(
    payload: CreatePetRequest,
    request: Request,
    pet_client: PetClientDependency,
    current_user: CurrentUserDependency,
) -> PetResponse:
    """
    Create a pet profile for the authenticated user.

    Ownership validation, persistence, duplicate detection, and business rules
    belong to the Pet Service.
    """
    return await pet_client.create_pet(
        user_id=current_user.user_id,
        payload=payload,
        request_id=_get_request_id(request),
    )


@router.get(
    "",
    response_model=PetListResponse,
    status_code=status.HTTP_200_OK,
    summary="List the current user's pets",
)
async def list_pets(
    request: Request,
    pet_client: PetClientDependency,
    current_user: CurrentUserDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    include_inactive: bool = False,
) -> PetListResponse:
    """
    Return a paginated list of pets belonging to the authenticated user.
    """
    return await pet_client.list_pets(
        user_id=current_user.user_id,
        page=page,
        page_size=page_size,
        include_inactive=include_inactive,
        request_id=_get_request_id(request),
    )


@router.get(
    "/{pet_id}",
    response_model=PetResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a pet profile",
)
async def get_pet(
    pet_id: UUID,
    request: Request,
    pet_client: PetClientDependency,
    current_user: CurrentUserDependency,
) -> PetResponse:
    """
    Return a pet profile.

    The Pet Service must verify that the authenticated user owns the pet or has
    permission to access it.
    """
    return await pet_client.get_pet(
        user_id=current_user.user_id,
        pet_id=pet_id,
        request_id=_get_request_id(request),
    )


@router.patch(
    "/{pet_id}",
    response_model=PetResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a pet profile",
)
async def update_pet(
    pet_id: UUID,
    payload: UpdatePetRequest,
    request: Request,
    pet_client: PetClientDependency,
    current_user: CurrentUserDependency,
) -> PetResponse:
    """
    Partially update a pet profile.

    Only fields included in the request are forwarded to the Pet Service.
    """
    return await pet_client.update_pet(
        user_id=current_user.user_id,
        pet_id=pet_id,
        payload=payload,
        request_id=_get_request_id(request),
    )


@router.delete(
    "/{pet_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a pet profile",
)
async def delete_pet(
    pet_id: UUID,
    request: Request,
    pet_client: PetClientDependency,
    current_user: CurrentUserDependency,
) -> None:
    """
    Delete or deactivate a pet profile.

    The Pet Service decides whether deletion is soft or permanent and must
    handle related behaviors, media, and analysis records safely.
    """
    await pet_client.delete_pet(
        user_id=current_user.user_id,
        pet_id=pet_id,
        request_id=_get_request_id(request),
    )


@router.post(
    "/{pet_id}/restore",
    response_model=PetResponse,
    status_code=status.HTTP_200_OK,
    summary="Restore a deleted pet profile",
)
async def restore_pet(
    pet_id: UUID,
    request: Request,
    pet_client: PetClientDependency,
    current_user: CurrentUserDependency,
) -> PetResponse:
    """
    Restore a previously soft-deleted or deactivated pet profile.
    """
    return await pet_client.restore_pet(
        user_id=current_user.user_id,
        pet_id=pet_id,
        request_id=_get_request_id(request),
    )


def _get_request_id(request: Request) -> str | None:
    """
    Return the request ID created by request-ID middleware.
    """
    return getattr(request.state, "request_id", None)
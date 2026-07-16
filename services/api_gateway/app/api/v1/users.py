from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.core.dependencies import (
    get_current_admin,
    get_current_user,
    get_user_client,
)
from app.schemas.user import (
    DeleteAccountRequest,
    MessageResponse,
    UpdateUserPreferencesRequest,
    UpdateUserProfileRequest,
    UserListResponse,
    UserPreferencesResponse,
    UserResponse,
)
from app.services.user_client import UserClient
from shared.schemas.auth import AuthenticatedUser

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

UserClientDependency = Annotated[
    UserClient,
    Depends(get_user_client),
]

CurrentUserDependency = Annotated[
    AuthenticatedUser,
    Depends(get_current_user),
]

CurrentAdminDependency = Annotated[
    AuthenticatedUser,
    Depends(get_current_admin),
]


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the current user profile",
)
async def get_current_user_profile(
    request: Request,
    user_client: UserClientDependency,
    current_user: CurrentUserDependency,
) -> UserResponse:
    """
    Return the authenticated user's profile.

    Authentication metadata may come from the access token, but the latest
    profile state should be retrieved from the User Service.
    """
    return await user_client.get_user(
        user_id=current_user.user_id,
        request_id=_get_request_id(request),
    )


@router.patch(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update the current user profile",
)
async def update_current_user_profile(
    payload: UpdateUserProfileRequest,
    request: Request,
    user_client: UserClientDependency,
    current_user: CurrentUserDependency,
) -> UserResponse:
    """
    Partially update the authenticated user's profile.

    Email changes, identity verification, and security-sensitive fields should
    be handled by dedicated flows in the User or Auth Service.
    """
    return await user_client.update_user(
        user_id=current_user.user_id,
        payload=payload,
        request_id=_get_request_id(request),
    )


@router.get(
    "/me/preferences",
    response_model=UserPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user preferences",
)
async def get_user_preferences(
    request: Request,
    user_client: UserClientDependency,
    current_user: CurrentUserDependency,
) -> UserPreferencesResponse:
    """
    Return notification, locale, privacy, and application preferences.
    """
    return await user_client.get_preferences(
        user_id=current_user.user_id,
        request_id=_get_request_id(request),
    )


@router.patch(
    "/me/preferences",
    response_model=UserPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user preferences",
)
async def update_user_preferences(
    payload: UpdateUserPreferencesRequest,
    request: Request,
    user_client: UserClientDependency,
    current_user: CurrentUserDependency,
) -> UserPreferencesResponse:
    """
    Partially update the authenticated user's preferences.
    """
    return await user_client.update_preferences(
        user_id=current_user.user_id,
        payload=payload,
        request_id=_get_request_id(request),
    )


@router.delete(
    "/me",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request account deletion",
)
async def delete_current_user_account(
    payload: DeleteAccountRequest,
    request: Request,
    user_client: UserClientDependency,
    current_user: CurrentUserDependency,
) -> MessageResponse:
    """
    Request deletion of the authenticated user's account.

    The User Service is responsible for:

    - verifying the password or confirmation token;
    - applying retention requirements;
    - canceling active subscriptions when appropriate;
    - revoking sessions;
    - scheduling deletion or anonymization;
    - deleting associated pets, media, and analyses safely.

    A 202 response means the deletion workflow was accepted.
    """
    await user_client.request_account_deletion(
        user_id=current_user.user_id,
        payload=payload,
        request_id=_get_request_id(request),
        client_ip=_get_client_ip(request),
    )

    return MessageResponse(
        message="Account deletion request accepted.",
    )


@router.get(
    "",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List users",
)
async def list_users(
    request: Request,
    user_client: UserClientDependency,
    current_admin: CurrentAdminDependency,
    page: int = 1,
    page_size: int = 20,
    email: str | None = None,
    is_active: bool | None = None,
) -> UserListResponse:
    """
    Return a paginated user list for authorized administrators.

    The User Service must enforce administrator permissions and ensure that
    sensitive fields are excluded from the response.
    """
    normalized_page = max(page, 1)
    normalized_page_size = min(max(page_size, 1), 100)

    return await user_client.list_users(
        admin_user_id=current_admin.user_id,
        page=normalized_page,
        page_size=normalized_page_size,
        email=email,
        is_active=is_active,
        request_id=_get_request_id(request),
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a user",
)
async def get_user(
    user_id: UUID,
    request: Request,
    user_client: UserClientDependency,
    current_admin: CurrentAdminDependency,
) -> UserResponse:
    """
    Return a user profile for an authorized administrator.
    """
    return await user_client.get_user_as_admin(
        admin_user_id=current_admin.user_id,
        user_id=user_id,
        request_id=_get_request_id(request),
    )


@router.post(
    "/{user_id}/disable",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Disable a user account",
)
async def disable_user(
    user_id: UUID,
    request: Request,
    user_client: UserClientDependency,
    current_admin: CurrentAdminDependency,
) -> UserResponse:
    """
    Disable a user account.

    The User Service should revoke active sessions and record an audit event.
    """
    return await user_client.disable_user(
        admin_user_id=current_admin.user_id,
        user_id=user_id,
        request_id=_get_request_id(request),
    )


@router.post(
    "/{user_id}/enable",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Enable a user account",
)
async def enable_user(
    user_id: UUID,
    request: Request,
    user_client: UserClientDependency,
    current_admin: CurrentAdminDependency,
) -> UserResponse:
    """
    Re-enable a previously disabled user account.
    """
    return await user_client.enable_user(
        admin_user_id=current_admin.user_id,
        user_id=user_id,
        request_id=_get_request_id(request),
    )


def _get_request_id(request: Request) -> str | None:
    """
    Return the request ID generated by request-ID middleware.
    """
    return getattr(request.state, "request_id", None)


def _get_client_ip(request: Request) -> str | None:
    """
    Return the originating client IP.

    Forwarded headers should only be trusted after trusted-proxy validation.
    """
    forwarded_for = request.headers.get("x-forwarded-for")

    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()

    if request.client:
        return request.client.host

    return None

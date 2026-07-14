from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.core.dependencies import get_auth_client, get_current_user
from app.schemas.auth import (
    AccessTokenResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutResponse,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
)
from app.services.auth_client import AuthClient
from shared.schemas.auth import AuthenticatedUser

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

AuthClientDependency = Annotated[AuthClient, Depends(get_auth_client)]
CurrentUserDependency = Annotated[
    AuthenticatedUser,
    Depends(get_current_user),
]


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    payload: RegisterRequest,
    request: Request,
    auth_client: AuthClientDependency,
) -> UserResponse:
    """
    Register a new Pet Behavior Platform user.

    The API Gateway validates the request schema and forwards the request to
    the authentication service. Password hashing, duplicate-email validation,
    persistence, and verification-email generation belong to the auth service.
    """
    return await auth_client.register(
        payload=payload,
        request_id=_get_request_id(request),
        client_ip=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/login",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate a user",
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    auth_client: AuthClientDependency,
) -> AccessTokenResponse:
    """
    Authenticate a user and issue access and refresh tokens.

    The access token is returned in the response body. The refresh token may
    additionally be stored in a secure HTTP-only cookie, depending on the
    client type and platform configuration.
    """
    token_response = await auth_client.login(
        payload=payload,
        request_id=_get_request_id(request),
        client_ip=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    if token_response.refresh_token:
        _set_refresh_token_cookie(
            response=response,
            refresh_token=token_response.refresh_token,
        )

    return token_response


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh an access token",
)
async def refresh_token(
    payload: RefreshTokenRequest,
    request: Request,
    response: Response,
    auth_client: AuthClientDependency,
) -> AccessTokenResponse:
    """
    Exchange a valid refresh token for a new access token.

    The refresh token may come from the request body or an HTTP-only cookie.
    The auth service remains responsible for token validation, rotation,
    revocation checks, and replay detection.
    """
    refresh_token_value = (
        payload.refresh_token
        or request.cookies.get("refresh_token")
    )

    refresh_payload = payload.model_copy(
        update={"refresh_token": refresh_token_value},
    )

    token_response = await auth_client.refresh_token(
        payload=refresh_payload,
        request_id=_get_request_id(request),
        client_ip=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    if token_response.refresh_token:
        _set_refresh_token_cookie(
            response=response,
            refresh_token=token_response.refresh_token,
        )

    return token_response


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Log out the current user",
)
async def logout(
    payload: RefreshTokenRequest,
    request: Request,
    response: Response,
    auth_client: AuthClientDependency,
    current_user: CurrentUserDependency,
) -> LogoutResponse:
    """
    Revoke the current refresh token and clear the refresh-token cookie.
    """
    refresh_token_value = (
        payload.refresh_token
        or request.cookies.get("refresh_token")
    )

    logout_payload = payload.model_copy(
        update={"refresh_token": refresh_token_value},
    )

    result = await auth_client.logout(
        user_id=current_user.user_id,
        payload=logout_payload,
        request_id=_get_request_id(request),
    )

    _clear_refresh_token_cookie(response)

    return result


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the current user",
)
async def get_current_user_profile(
    request: Request,
    auth_client: AuthClientDependency,
    current_user: CurrentUserDependency,
) -> UserResponse:
    """
    Return the authenticated user's current profile.
    """
    return await auth_client.get_user(
        user_id=current_user.user_id,
        request_id=_get_request_id(request),
    )


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request a password reset",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    auth_client: AuthClientDependency,
) -> MessageResponse:
    """
    Request a password-reset email.

    This endpoint should return the same response regardless of whether the
    email exists, preventing account-enumeration attacks.
    """
    await auth_client.forgot_password(
        payload=payload,
        request_id=_get_request_id(request),
        client_ip=_get_client_ip(request),
    )

    return MessageResponse(
        message=(
            "If an account exists for that email address, "
            "password reset instructions will be sent."
        ),
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset a password",
)
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    auth_client: AuthClientDependency,
) -> MessageResponse:
    """
    Reset a user's password using a password-reset token.
    """
    await auth_client.reset_password(
        payload=payload,
        request_id=_get_request_id(request),
        client_ip=_get_client_ip(request),
    )

    return MessageResponse(
        message="Password reset successfully.",
    )


@router.post(
    "/change-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change the current user's password",
)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    auth_client: AuthClientDependency,
    current_user: CurrentUserDependency,
) -> MessageResponse:
    """
    Change the authenticated user's password.

    The auth service should verify the current password, revoke existing
    sessions when configured, and securely persist the new password hash.
    """
    await auth_client.change_password(
        user_id=current_user.user_id,
        payload=payload,
        request_id=_get_request_id(request),
        client_ip=_get_client_ip(request),
    )

    return MessageResponse(
        message="Password changed successfully.",
    )


def _get_request_id(request: Request) -> str | None:
    """
    Return the request ID created by request-ID middleware.
    """
    return getattr(request.state, "request_id", None)


def _get_client_ip(request: Request) -> str | None:
    """
    Return the originating client IP.

    In production, trusted-proxy middleware should validate forwarded headers
    before this value is used for auditing or rate limiting.
    """
    forwarded_for = request.headers.get("x-forwarded-for")

    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()

    if request.client:
        return request.client.host

    return None


def _set_refresh_token_cookie(
    response: Response,
    refresh_token: str,
) -> None:
    """
    Store a refresh token in a secure HTTP-only cookie.

    The secure flag assumes HTTPS in deployed environments. Local development
    can override this behavior through centralized configuration later.
    """
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/api/v1/auth",
        max_age=60 * 60 * 24 * 30,
    )


def _clear_refresh_token_cookie(response: Response) -> None:
    """
    Remove the refresh-token cookie from the client.
    """
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
        httponly=True,
        secure=True,
        samesite="lax",
    )
from __future__ import annotations

from collections.abc import Callable
from typing import Annotated
from uuid import UUID, uuid4

import httpx
from fastapi import (
    Depends,
    Header,
    HTTPException,
    Request,
    Security,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from app.core.config import Settings, get_settings
from app.core.logging import set_user_id
from app.core.security import (
    AuthenticatedUser,
    SecurityError,
    SecurityErrorCode,
    UserRole,
    decode_access_token,
    require_active_user,
    require_roles,
    require_scopes,
)


bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",
    description="JWT access token issued by the Auth Service.",
    auto_error=False,
)


def security_http_exception(
    error: SecurityError,
) -> HTTPException:
    """
    Convert a transport-independent SecurityError into HTTPException.
    """

    unauthorized_codes = {
        SecurityErrorCode.MISSING_TOKEN,
        SecurityErrorCode.INVALID_TOKEN,
        SecurityErrorCode.EXPIRED_TOKEN,
        SecurityErrorCode.INVALID_TOKEN_CLAIMS,
    }

    if error.code in unauthorized_codes:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": error.code.value,
                "message": error.message,
            },
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": error.code.value,
            "message": error.message,
        },
    )


def authenticate_credentials(
    credentials: HTTPAuthorizationCredentials | None,
    settings: Settings,
) -> AuthenticatedUser:
    """
    Validate parsed HTTP Bearer credentials.
    """

    if credentials is None:
        raise SecurityError(
            SecurityErrorCode.MISSING_TOKEN,
            "Bearer authentication is required.",
        )

    if credentials.scheme.lower() != "bearer":
        raise SecurityError(
            SecurityErrorCode.INVALID_TOKEN,
            "Authorization scheme must be Bearer.",
        )

    user = decode_access_token(
        token=credentials.credentials,
        settings=settings,
    )

    require_active_user(user)

    return user


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(bearer_scheme),
    ],
    settings: Annotated[
        Settings,
        Depends(get_settings),
    ],
) -> AuthenticatedUser:
    """
    Require a valid authenticated user.
    """

    try:
        user = authenticate_credentials(
            credentials,
            settings,
        )
    except SecurityError as error:
        raise security_http_exception(error) from error

    set_user_id(str(user.id))

    return user


async def get_optional_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(bearer_scheme),
    ],
    settings: Annotated[
        Settings,
        Depends(get_settings),
    ],
) -> AuthenticatedUser | None:
    """
    Return the authenticated user when a token is present.

    Missing credentials are allowed, but an invalid supplied token is not.
    This dependency is suitable for public endpoints with personalized
    responses.
    """

    if credentials is None:
        return None

    try:
        user = authenticate_credentials(
            credentials,
            settings,
        )
    except SecurityError as error:
        raise security_http_exception(error) from error

    set_user_id(str(user.id))

    return user


async def get_current_admin(
    user: Annotated[
        AuthenticatedUser,
        Depends(get_current_user),
    ],
) -> AuthenticatedUser:
    """
    Require an administrator or super-administrator role.
    """

    try:
        require_roles(
            user,
            {
                UserRole.ADMIN,
                UserRole.SUPER_ADMIN,
            },
        )
    except SecurityError as error:
        raise security_http_exception(error) from error

    return user


async def get_current_support_user(
    user: Annotated[
        AuthenticatedUser,
        Depends(get_current_user),
    ],
) -> AuthenticatedUser:
    """
    Require support, operations, admin, or super-admin access.
    """

    try:
        require_roles(
            user,
            {
                UserRole.SUPPORT,
                UserRole.OPERATIONS,
                UserRole.ADMIN,
                UserRole.SUPER_ADMIN,
            },
        )
    except SecurityError as error:
        raise security_http_exception(error) from error

    return user


def require_permission(
    *required_scopes: str,
) -> Callable[..., AuthenticatedUser]:
    """
    Build a dependency requiring every supplied authorization scope.

    Example:

        @router.post("/pets")
        async def create_pet(
            user: Annotated[
                AuthenticatedUser,
                Depends(require_permission("pets:write")),
            ],
        ):
            ...
    """

    normalized_scopes = {
        scope.strip()
        for scope in required_scopes
        if scope.strip()
    }

    if not normalized_scopes:
        raise ValueError(
            "At least one authorization scope is required."
        )

    async def permission_dependency(
        user: Annotated[
            AuthenticatedUser,
            Depends(get_current_user),
        ],
    ) -> AuthenticatedUser:
        try:
            require_scopes(
                user,
                normalized_scopes,
            )
        except SecurityError as error:
            raise security_http_exception(error) from error

        return user

    return permission_dependency


async def get_request_id(
    request: Request,
    request_id_header: Annotated[
        str | None,
        Header(
            alias="X-Request-ID",
            min_length=1,
            max_length=255,
        ),
    ] = None,
) -> str:
    """
    Return the request ID established by middleware or the caller.
    """

    existing_request_id = getattr(
        request.state,
        "request_id",
        None,
    )

    request_id = (
        existing_request_id
        or request_id_header
        or str(uuid4())
    )

    request.state.request_id = request_id

    return request_id


async def get_http_client(
    request: Request,
) -> httpx.AsyncClient:
    """
    Return the shared downstream HTTP client.

    The client is created and closed by the application lifespan manager.
    """

    client: httpx.AsyncClient | None = getattr(
        request.app.state,
        "http_client",
        None,
    )

    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "gateway_not_ready",
                "message": (
                    "The API Gateway HTTP client is not initialized."
                ),
            },
        )

    return client


async def get_authenticated_user_id(
    user: Annotated[
        AuthenticatedUser,
        Depends(get_current_user),
    ],
) -> UUID:
    return user.id


async def get_idempotency_key(
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="X-Idempotency-Key",
            min_length=8,
            max_length=255,
        ),
    ] = None,
) -> str | None:
    """
    Return the optional client idempotency key.

    Validation and persistence of the key should be handled by the owning
    downstream service.
    """

    if idempotency_key is None:
        return None

    return idempotency_key.strip()


# ----------------------------------------------------------------------
# Reusable annotated dependency aliases
# ----------------------------------------------------------------------

SettingsDependency = Annotated[
    Settings,
    Depends(get_settings),
]

CurrentUser = Annotated[
    AuthenticatedUser,
    Depends(get_current_user),
]

OptionalUser = Annotated[
    AuthenticatedUser | None,
    Depends(get_optional_user),
]

CurrentUserId = Annotated[
    UUID,
    Depends(get_authenticated_user_id),
]

CurrentAdmin = Annotated[
    AuthenticatedUser,
    Depends(get_current_admin),
]

CurrentSupportUser = Annotated[
    AuthenticatedUser,
    Depends(get_current_support_user),
]

HttpClient = Annotated[
    httpx.AsyncClient,
    Depends(get_http_client),
]

RequestId = Annotated[
    str,
    Depends(get_request_id),
]

IdempotencyKey = Annotated[
    str | None,
    Depends(get_idempotency_key),
]

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Annotated
from uuid import UUID, uuid4

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
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import (
    AuthenticatedUser,
    AuthenticationError,
    InternalServiceIdentity,
    SecurityErrorCode,
    UserRole,
    UserStatus,
    decode_access_token,
    require_roles,
    require_scopes,
    verify_internal_service,
)
from app.db.session import get_db_session


bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",
    description="JWT access token issued by the Auth Service.",
    auto_error=False,
)


def authentication_exception(
    error: AuthenticationError,
) -> HTTPException:
    """
    Translate transport-independent authentication errors into HTTP errors.
    """

    if error.code in {
        SecurityErrorCode.MISSING_TOKEN,
        SecurityErrorCode.INVALID_TOKEN,
        SecurityErrorCode.EXPIRED_TOKEN,
        SecurityErrorCode.INVALID_CLAIMS,
        SecurityErrorCode.INVALID_SERVICE_TOKEN,
        SecurityErrorCode.UNTRUSTED_SERVICE,
    }:
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
    Validate the caller's Bearer token and return its user context.
    """

    if credentials is None:
        raise authentication_exception(
            AuthenticationError(
                SecurityErrorCode.MISSING_TOKEN,
                "Bearer authentication is required.",
            )
        )

    if credentials.scheme.lower() != "bearer":
        raise authentication_exception(
            AuthenticationError(
                SecurityErrorCode.INVALID_TOKEN,
                "Authorization scheme must be Bearer.",
            )
        )

    try:
        user = decode_access_token(
            token=credentials.credentials,
            settings=settings,
        )
    except AuthenticationError as error:
        raise authentication_exception(error) from error

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "inactive_user",
                "message": (
                    "The authenticated user account is not active."
                ),
            },
        )

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
    except AuthenticationError as error:
        raise authentication_exception(error) from error

    return user


async def get_current_support_user(
    user: Annotated[
        AuthenticatedUser,
        Depends(get_current_user),
    ],
) -> AuthenticatedUser:
    """
    Require support, operations, admin, or super-admin privileges.
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
    except AuthenticationError as error:
        raise authentication_exception(error) from error

    return user


def require_permission(
    *required_scopes: str,
) -> Callable[..., AuthenticatedUser]:
    """
    Build a dependency that requires all provided authorization scopes.

    Example:

        @router.post(
            "/pets",
            dependencies=[
                Depends(require_permission("pets:write")),
            ],
        )
        async def create_pet(...):
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
        except AuthenticationError as error:
            raise authentication_exception(error) from error

        return user

    return permission_dependency


async def get_internal_service(
    settings: Annotated[
        Settings,
        Depends(get_settings),
    ],
    service_name: Annotated[
        str | None,
        Header(
            alias="X-Service-Name",
            description="Name of the calling internal service.",
        ),
    ] = None,
    service_token: Annotated[
        str | None,
        Header(
            alias="X-Internal-Service-Token",
            description="Internal service authentication token.",
        ),
    ] = None,
) -> InternalServiceIdentity:
    """
    Authenticate an internal service-to-service request.

    This dependency is intended for private endpoints that are not accessed
    directly by end users.
    """

    try:
        return verify_internal_service(
            service_name=service_name,
            supplied_token=service_token,
            settings=settings,
        )
    except AuthenticationError as error:
        raise authentication_exception(error) from error


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
    Return the request ID assigned by middleware or the upstream gateway.

    The request ID is made available on request.state so logging and tracing
    code can access one consistent value.
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


async def get_authenticated_user_id(
    user: Annotated[
        AuthenticatedUser,
        Depends(get_current_user),
    ],
) -> UUID:
    """
    Convenience dependency that returns only the current user's UUID.
    """

    return user.id


async def get_database_session(
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
) -> AsyncIterator[AsyncSession]:
    """
    Forward the request-scoped SQLAlchemy session.

    The underlying get_db_session dependency owns commit, rollback, and close
    behavior. This wrapper provides a stable import path for API modules.
    """

    yield session


# ----------------------------------------------------------------------
# Reusable annotated dependency aliases
# ----------------------------------------------------------------------

SettingsDependency = Annotated[
    Settings,
    Depends(get_settings),
]

DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_database_session),
]

CurrentUser = Annotated[
    AuthenticatedUser,
    Depends(get_current_user),
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

InternalService = Annotated[
    InternalServiceIdentity,
    Depends(get_internal_service),
]

RequestId = Annotated[
    str,
    Depends(get_request_id),
]

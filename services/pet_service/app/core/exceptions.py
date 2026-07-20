from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID


class ErrorCode(StrEnum):
    AUTHENTICATION_REQUIRED = "authentication_required"
    INVALID_TOKEN = "invalid_token"
    TOKEN_EXPIRED = "token_expired"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"

    PET_NOT_FOUND = "pet_not_found"
    PET_ACCESS_DENIED = "pet_access_denied"
    PET_LIMIT_REACHED = "pet_limit_reached"
    PET_ALREADY_DELETED = "pet_already_deleted"
    PET_NOT_DELETED = "pet_not_deleted"
    PET_VERSION_CONFLICT = "pet_version_conflict"
    INVALID_PET_DATA = "invalid_pet_data"

    MEDIA_NOT_FOUND = "media_not_found"
    INVALID_AVATAR_MEDIA = "invalid_avatar_media"
    MEDIA_SERVICE_UNAVAILABLE = "media_service_unavailable"

    USER_NOT_FOUND = "user_not_found"
    USER_SERVICE_UNAVAILABLE = "user_service_unavailable"

    DATABASE_UNAVAILABLE = "database_unavailable"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    INTERNAL_SERVICE_UNAUTHORIZED = (
        "internal_service_unauthorized"
    )

    VALIDATION_ERROR = "validation_error"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    REQUEST_TOO_LARGE = "request_too_large"

    CONFIGURATION_ERROR = "configuration_error"
    INTERNAL_ERROR = "internal_error"


class ServiceError(Exception):
    """
    Base application-layer exception.

    Domain, repository, and client modules should raise ServiceError
    subclasses rather than FastAPI HTTPException.
    """

    status_code = 500
    code = ErrorCode.INTERNAL_ERROR
    default_message = (
        "An unexpected internal error occurred."
    )

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = (
            message
            or self.default_message
        )

        self.details = details
        self.headers = headers

        super().__init__(self.message)


class AuthenticationRequiredError(ServiceError):
    status_code = 401
    code = ErrorCode.AUTHENTICATION_REQUIRED
    default_message = "Authentication is required."


class InvalidTokenError(ServiceError):
    status_code = 401
    code = ErrorCode.INVALID_TOKEN
    default_message = (
        "The authentication token is invalid."
    )


class TokenExpiredError(ServiceError):
    status_code = 401
    code = ErrorCode.TOKEN_EXPIRED
    default_message = (
        "The authentication token has expired."
    )


class PermissionDeniedError(ServiceError):
    status_code = 403
    code = ErrorCode.INSUFFICIENT_PERMISSIONS
    default_message = (
        "The authenticated caller does not have "
        "permission to perform this operation."
    )


class PetNotFoundError(ServiceError):
    status_code = 404
    code = ErrorCode.PET_NOT_FOUND
    default_message = (
        "The requested pet was not found."
    )

    def __init__(
        self,
        pet_id: UUID | str | None = None,
    ) -> None:
        details = (
            {"pet_id": str(pet_id)}
            if pet_id is not None
            else None
        )

        super().__init__(details=details)


class PetAccessDeniedError(ServiceError):
    status_code = 403
    code = ErrorCode.PET_ACCESS_DENIED
    default_message = (
        "Access to the requested pet is denied."
    )


class PetLimitReachedError(ServiceError):
    status_code = 409
    code = ErrorCode.PET_LIMIT_REACHED
    default_message = (
        "The maximum number of pet profiles "
        "has been reached."
    )

    def __init__(self, limit: int) -> None:
        super().__init__(
            details={
                "limit": limit,
            },
        )


class PetAlreadyDeletedError(ServiceError):
    status_code = 409
    code = ErrorCode.PET_ALREADY_DELETED
    default_message = (
        "The pet profile has already been deleted."
    )


class PetNotDeletedError(ServiceError):
    status_code = 409
    code = ErrorCode.PET_NOT_DELETED
    default_message = (
        "The pet profile is not deleted and "
        "cannot be restored."
    )


class PetVersionConflictError(ServiceError):
    status_code = 409
    code = ErrorCode.PET_VERSION_CONFLICT
    default_message = (
        "The pet profile was modified by "
        "another request."
    )

    def __init__(
        self,
        *,
        expected_version: int | None = None,
        actual_version: int | None = None,
    ) -> None:
        details: dict[str, Any] = {}

        if expected_version is not None:
            details["expected_version"] = (
                expected_version
            )

        if actual_version is not None:
            details["actual_version"] = (
                actual_version
            )

        super().__init__(
            details=details or None
        )


class InvalidPetDataError(ServiceError):
    status_code = 422
    code = ErrorCode.INVALID_PET_DATA
    default_message = (
        "The supplied pet data is invalid."
    )


class MediaNotFoundError(ServiceError):
    status_code = 404
    code = ErrorCode.MEDIA_NOT_FOUND
    default_message = (
        "The requested media resource was not found."
    )


class InvalidAvatarMediaError(ServiceError):
    status_code = 422
    code = ErrorCode.INVALID_AVATAR_MEDIA
    default_message = (
        "The selected media resource cannot "
        "be used as a pet avatar."
    )


class MediaServiceUnavailableError(ServiceError):
    status_code = 503
    code = ErrorCode.MEDIA_SERVICE_UNAVAILABLE
    default_message = (
        "The Media Service is currently unavailable."
    )


class UserNotFoundError(ServiceError):
    status_code = 404
    code = ErrorCode.USER_NOT_FOUND
    default_message = (
        "The requested user was not found."
    )


class UserServiceUnavailableError(ServiceError):
    status_code = 503
    code = ErrorCode.USER_SERVICE_UNAVAILABLE
    default_message = (
        "The User Service is currently unavailable."
    )


class DatabaseUnavailableError(ServiceError):
    status_code = 503
    code = ErrorCode.DATABASE_UNAVAILABLE
    default_message = (
        "The database is currently unavailable."
    )


class DependencyUnavailableError(ServiceError):
    status_code = 503
    code = ErrorCode.DEPENDENCY_UNAVAILABLE
    default_message = (
        "A required dependency is currently unavailable."
    )

    def __init__(
        self,
        dependency_name: str,
        *,
        message: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            details={
                "dependency": dependency_name,
            },
        )


class InternalServiceUnauthorizedError(ServiceError):
    status_code = 401
    code = ErrorCode.INTERNAL_SERVICE_UNAUTHORIZED
    default_message = (
        "Internal service authentication failed."
    )


class RequestValidationError(ServiceError):
    status_code = 422
    code = ErrorCode.VALIDATION_ERROR
    default_message = (
        "The request contains invalid data."
    )


class RateLimitExceededError(ServiceError):
    status_code = 429
    code = ErrorCode.RATE_LIMIT_EXCEEDED
    default_message = (
        "Too many requests have been submitted."
    )

    def __init__(
        self,
        *,
        retry_after_seconds: int | None = None,
    ) -> None:
        details = None
        headers = None

        if retry_after_seconds is not None:
            details = {
                "retry_after_seconds": (
                    retry_after_seconds
                ),
            }

            headers = {
                "Retry-After": str(
                    retry_after_seconds
                ),
            }

        super().__init__(
            details=details,
            headers=headers,
        )


class RequestTooLargeError(ServiceError):
    status_code = 413
    code = ErrorCode.REQUEST_TOO_LARGE
    default_message = (
        "The request body exceeds the allowed size."
    )


class ConfigurationError(ServiceError):
    status_code = 500
    code = ErrorCode.CONFIGURATION_ERROR
    default_message = (
        "The service is incorrectly configured."
    )
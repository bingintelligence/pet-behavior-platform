from __future__ import annotations

import json
import logging
import logging.config
import sys
import traceback
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from typing import Any

from app.core.config import Settings


request_id_context: ContextVar[str | None] = ContextVar(
    "request_id",
    default=None,
)

user_id_context: ContextVar[str | None] = ContextVar(
    "user_id",
    default=None,
)

client_ip_context: ContextVar[str | None] = ContextVar(
    "client_ip",
    default=None,
)

user_agent_context: ContextVar[str | None] = ContextVar(
    "user_agent",
    default=None,
)


SENSITIVE_FIELDS = {
    "authorization",
    "cookie",
    "set-cookie",
    "password",
    "current_password",
    "new_password",
    "access_token",
    "refresh_token",
    "id_token",
    "service_token",
    "internal_service_token",
    "api_key",
    "x-api-key",
    "secret",
    "client_secret",
    "jwt",
}


STANDARD_LOG_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


def set_request_id(
    request_id: str | None,
) -> Token[str | None]:
    return request_id_context.set(request_id)


def reset_request_id(
    token: Token[str | None],
) -> None:
    request_id_context.reset(token)


def set_user_id(
    user_id: str | None,
) -> Token[str | None]:
    return user_id_context.set(user_id)


def reset_user_id(
    token: Token[str | None],
) -> None:
    user_id_context.reset(token)


def set_client_ip(
    client_ip: str | None,
) -> Token[str | None]:
    return client_ip_context.set(client_ip)


def reset_client_ip(
    token: Token[str | None],
) -> None:
    client_ip_context.reset(token)


def set_user_agent(
    user_agent: str | None,
) -> Token[str | None]:
    return user_agent_context.set(user_agent)


def reset_user_agent(
    token: Token[str | None],
) -> None:
    user_agent_context.reset(token)


def is_sensitive_field(key: str) -> bool:
    normalized_key = key.strip().lower()

    return any(
        sensitive == normalized_key
        or sensitive in normalized_key
        for sensitive in SENSITIVE_FIELDS
    )


def sanitize_log_data(value: Any) -> Any:
    """
    Recursively redact sensitive values before logging.
    """

    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}

        for key, item_value in value.items():
            string_key = str(key)

            if is_sensitive_field(string_key):
                sanitized[string_key] = "[REDACTED]"
            else:
                sanitized[string_key] = sanitize_log_data(
                    item_value
                )

        return sanitized

    if isinstance(value, (list, tuple, set, frozenset)):
        return [
            sanitize_log_data(item)
            for item in value
        ]

    return value


class RequestContextFilter(logging.Filter):
    """
    Add request-scoped context to every log record.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        record.user_id = user_id_context.get()
        record.client_ip = client_ip_context.get()
        record.user_agent = user_agent_context.get()

        return True


class JsonFormatter(logging.Formatter):
    """
    Format each log record as a JSON object.
    """

    def __init__(
        self,
        *,
        service_name: str,
        service_version: str,
        environment: str,
    ) -> None:
        super().__init__()

        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment

    def format(
        self,
        record: logging.LogRecord,
    ) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "service_version": self.service_version,
            "environment": self.environment,
            "request_id": getattr(
                record,
                "request_id",
                None,
            ),
            "user_id": getattr(
                record,
                "user_id",
                None,
            ),
            "client_ip": getattr(
                record,
                "client_ip",
                None,
            ),
            "user_agent": getattr(
                record,
                "user_agent",
                None,
            ),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if (
                key not in STANDARD_LOG_RECORD_FIELDS
                and key not in payload
                and not key.startswith("_")
            )
        }

        if extra_fields:
            payload["data"] = sanitize_log_data(
                extra_fields
            )

        if record.exc_info:
            exception_type = record.exc_info[0]

            payload["exception"] = {
                "type": (
                    exception_type.__name__
                    if exception_type
                    else None
                ),
                "message": str(record.exc_info[1]),
                "stack_trace": "".join(
                    traceback.format_exception(
                        *record.exc_info
                    )
                ),
            }

        if record.stack_info:
            payload["stack_info"] = record.stack_info

        return json.dumps(
            payload,
            ensure_ascii=False,
            default=str,
        )


class TextFormatter(logging.Formatter):
    """
    Human-readable local-development formatter.
    """

    def __init__(self) -> None:
        super().__init__(
            fmt=(
                "%(asctime)s %(levelname)s "
                "[%(name)s] "
                "[request_id=%(request_id)s] "
                "[user_id=%(user_id)s] "
                "%(message)s"
            ),
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )


def configure_logging(settings: Settings) -> None:
    """
    Configure API Gateway, Uvicorn, and HTTP client logging.
    """

    formatter_name = (
        "json"
        if settings.log_json
        else "text"
    )

    access_log_level = (
        settings.log_level
        if settings.access_log_enabled
        else "CRITICAL"
    )

    logging_config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_context": {
                "()": RequestContextFilter,
            },
        },
        "formatters": {
            "json": {
                "()": JsonFormatter,
                "service_name": settings.service_name,
                "service_version": settings.service_version,
                "environment": settings.environment,
            },
            "text": {
                "()": TextFormatter,
            },
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "level": settings.log_level,
                "formatter": formatter_name,
                "filters": ["request_context"],
            },
        },
        "root": {
            "handlers": ["stdout"],
            "level": settings.log_level,
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["stdout"],
                "level": settings.log_level,
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["stdout"],
                "level": settings.log_level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["stdout"],
                "level": access_log_level,
                "propagate": False,
            },
            "httpx": {
                "handlers": ["stdout"],
                "level": "WARNING",
                "propagate": False,
            },
            "httpcore": {
                "handlers": ["stdout"],
                "level": "WARNING",
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(logging_config)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

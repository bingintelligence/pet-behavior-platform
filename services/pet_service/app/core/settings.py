from __future__ import annotations

"""
Public configuration interface for Pet Service.

Application modules should import configuration through this module:

    from app.core.settings import Settings, get_settings

The actual BaseSettings implementation remains in app.core.config.
This module provides a stable public import path.
"""

from app.core.config import (
    Environment,
    LogLevel,
    Settings,
    get_settings,
)


__all__ = [
    "Environment",
    "LogLevel",
    "Settings",
    "get_settings",
]

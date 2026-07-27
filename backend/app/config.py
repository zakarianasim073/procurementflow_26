"""
DEPRECATED — This module has been replaced by `app.core.config`.

The legacy AppConfig dataclass and `config` singleton that lived here
were superseded by the pydantic-settings based Settings class in
`app.core.config` which provides validation, env var normalization,
and production safety checks.

Migration guide:
- ``AppConfig.app_name`` → ``from app.core.config import settings; settings.APP_NAME``
- ``AppConfig.debug`` → ``from app.core.config import settings; settings.ENVIRONMENT == "development"``
- ``AppConfig.database_url`` → ``from app.core.config import settings; settings.DATABASE_URL``
- ``config`` (singleton) → ``from app.core.config import settings`` (module-level, never instantiates)

Importing this module still works for backward compatibility but will
emit a DeprecationWarning in development and raise RuntimeError in
production environments.
"""

from __future__ import annotations

import os
import warnings

_ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()
_DEV_ENVIRONMENTS = {"development", "dev", "local", "test"}

if _ENVIRONMENT not in _DEV_ENVIRONMENTS:
    raise RuntimeError(
        "app.config is deprecated and disabled in production. "
        "Use app.core.config.settings instead. "
        f"ENVIRONMENT={_ENVIRONMENT!r}."
    )

warnings.warn(
    "app.config (legacy) is deprecated — use app.core.config.settings. "
    "This file will be removed in a future release.",
    DeprecationWarning,
    stacklevel=2,
)

from app.core.config import settings as _canonical_settings  # noqa: F401

AppConfig = None  # type: ignore[assignment]
config = None
"""
DEPRECATED: This module has been moved to `app.agents.core.base`.

Import from `app.agents.core.base` instead. This compatibility shim will be
removed in a future release.
"""

import warnings

warnings.warn(
    "app.agents.base is deprecated. Import from app.agents.core.base instead.",
    DeprecationWarning,
    stacklevel=2,
)

from app.agents.core.base import (
    AgentStatus,
    AgentResult,
    BaseAgent,
)

__all__ = ["AgentStatus", "AgentResult", "BaseAgent"]

"""
A2A Protocol Core Infrastructure

This module provides the base classes and utilities for implementing
A2A (Agent-to-Agent) protocol wrappers for GenPod agents.
"""

from core.a2a.base.executor import BaseA2AExecutor
from core.a2a.config.loader import A2AConfigLoader
from core.a2a.config.models import A2AConfig, AgentConfig
from core.a2a.exceptions import (
    A2AConfigError,
    A2AExecutionError,
    A2AInputExtractionError,
)

__all__ = [
    "BaseA2AExecutor",
    "A2AConfigLoader",
    "A2AConfig",
    "AgentConfig",
    "A2AConfigError",
    "A2AExecutionError",
    "A2AInputExtractionError",
]
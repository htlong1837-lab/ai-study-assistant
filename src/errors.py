"""Module-A custom exceptions hierarchy."""
from __future__ import annotations


class ModuleAError(Exception):
    """Base class for all Module-A errors."""


class MissingAPIKeyError(ModuleAError):
    """Raised when neither the user nor the host provides a valid API key."""


class InvalidAPIKeyError(ModuleAError):
    """Raised when the API returns a 401/403 authentication failure."""


class QuotaExceededError(ModuleAError):
    """Raised when the API quota or credits are exhausted (429/ResourceExhausted)."""


class LLMUnavailableError(ModuleAError):
    """Raised when every model in the cascade fails."""

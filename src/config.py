"""Application-level configuration loader for Module A.

This module reads ``config/models.yaml`` and exposes the model catalogue
and cascade order to the rest of the application.  It also honours the
``LLM_MODEL_CASCADE`` environment variable so the cascade can be overridden
in CI or for local testing without touching the YAML file.

Design note (L1)
----------------
This module reads ``os.environ`` at the *application* level.  The ``LLMClient``
library class never touches environment variables itself — it only receives
the cascade list and pricing dict from here via ``get_model_cascade()``.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml  # type: ignore[import-untyped]
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

# Path to the YAML file relative to the project root.
_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "models.yaml"


def _load_yaml() -> Dict[str, Any]:
    """Load and parse the models YAML file, or return a minimal fallback."""
    if _YAML_AVAILABLE and _CONFIG_PATH.exists():
        with _CONFIG_PATH.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}

    # Minimal built-in fallback so the app works even without PyYAML installed.
    return {
        "cascade": [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
        ],
        "models": {
            "gemini-2.5-flash": {"tier": "free_tier", "input_per_1k": 0.000075, "output_per_1k": 0.0003, "pricing_known": True},
            "gemini-2.0-flash": {"tier": "free_tier", "input_per_1k": 0.000075, "output_per_1k": 0.0003, "pricing_known": True},
            "gemini-1.5-flash": {"tier": "free_tier", "input_per_1k": 0.000075, "output_per_1k": 0.0003, "pricing_known": True},
        },
    }


_config: Dict[str, Any] = _load_yaml()


def get_model_cascade() -> List[str]:
    """Return the ordered list of model IDs to try.

    The ``LLM_MODEL_CASCADE`` environment variable (comma-separated model IDs)
    takes precedence over the YAML configuration.
    """
    env_override = os.environ.get("LLM_MODEL_CASCADE", "").strip()
    if env_override:
        return [m.strip() for m in env_override.split(",") if m.strip()]
    return list(_config.get("cascade", ["gemini-2.5-flash"]))


def get_model_info(model_id: str) -> Dict[str, Any]:
    """Return the metadata dict for *model_id*, or ``{}`` if unknown."""
    return dict(_config.get("models", {}).get(model_id, {}))


def get_model_tier(model_id: str) -> str:
    """Return the billing tier string for *model_id* (defaults to ``'unknown'``)."""
    return get_model_info(model_id).get("tier", "unknown")


def estimate_cost(model_id: str, input_tokens: int, output_tokens: int = 0) -> Optional[float]:
    """Return the estimated cost in USD, or ``None`` if pricing is unknown."""
    info = get_model_info(model_id)
    if not info.get("pricing_known", False):
        return None
    input_cost = (input_tokens / 1000.0) * info.get("input_per_1k", 0.0)
    output_cost = (output_tokens / 1000.0) * info.get("output_per_1k", 0.0)
    return round(input_cost + output_cost, 8)


def get_all_models() -> Dict[str, Dict[str, Any]]:
    """Return the full model catalogue as a dict keyed by model ID."""
    return dict(_config.get("models", {}))

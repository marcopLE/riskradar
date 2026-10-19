"""Helpers for refreshing stale modules during Streamlit script reruns."""

from __future__ import annotations

import importlib
from types import ModuleType
from typing import Iterable


def ensure_module_exports(module: ModuleType, required_names: Iterable[str]) -> ModuleType:
    """Reload a module when a Streamlit rerun finds it cached without new APIs."""
    missing = [name for name in required_names if not hasattr(module, name)]
    if not missing:
        return module

    module = importlib.reload(module)
    still_missing = [name for name in required_names if not hasattr(module, name)]
    if still_missing:
        names = ", ".join(still_missing)
        raise ImportError(f"Modul {module.__name__!r} exportiert benötigte Namen nicht: {names}")
    return module

"""Deprecated compatibility alias for :mod:`nicegui_base`.

New applications must import :mod:`nicegui_base`.  This package remains only to
provide a migration window for the former ``company_ui`` root import.
"""
from __future__ import annotations

import warnings
from nicegui_base import *  # noqa: F401,F403
from nicegui_base import __all__ as __all__  # type: ignore[attr-defined]

warnings.warn(
    "'company_ui' is deprecated; import 'nicegui_base' instead.",
    DeprecationWarning,
    stacklevel=2,
)

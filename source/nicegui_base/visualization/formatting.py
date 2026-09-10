"""Bounded numeric formatting shared by analytical visual renderers."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import Any


def format_visual_number(value: Any, *, significant: int = 4) -> str:
    """Format a finite analytical value without leaking binary-float noise.

    The formatter deliberately preserves meaningful magnitude while bounding
    ordinary labels to a small number of significant digits.  Units are kept
    outside this helper so axis/tooltip semantics remain explicit.
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not isfinite(number):
        return '—'
    if number == 0:
        return '0'
    try:
        decimal = Decimal(str(number))
    except InvalidOperation:
        return str(number)
    significant = max(1, int(significant))
    exponent = decimal.copy_abs().adjusted()
    if exponent >= significant or exponent <= -4:
        text = format(decimal, f'.{significant - 1}g')
    else:
        places = max(0, significant - exponent - 1)
        text = format(decimal, f'.{places}f')
    if 'e' not in text.lower():
        text = text.rstrip('0').rstrip('.')
    return text


def javascript_visual_number_formatter(unit: str | None = None) -> str:
    """Return a bounded formatter for ECharts axis labels/tooltips."""
    suffix = f" {unit}" if unit else ''
    return (
        "(value) => { const n=Number(value); if (!Number.isFinite(n)) return '—'; "
        "if (n === 0) return '0" + suffix + "'; "
        f"let s=Math.abs(n) >= 1e4 || Math.abs(n) < 1e-4 ? n.toPrecision({max(1, int(4))}) : n.toFixed(4); "
        "s=s.replace(/(\\.\\d*?[1-9])0+$|\\.0+$/,'$1'); "
        "return s + '" + suffix + "'; }"
    )


__all__ = ['format_visual_number', 'javascript_visual_number_formatter']

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

    def trim_fraction(text: str) -> str:
        """Trim zeroes after the decimal point, never from the integer part."""
        if '.' not in text:
            return text
        integer, fraction = text.split('.', 1)
        fraction = fraction.rstrip('0')
        return integer if not fraction else f'{integer}.{fraction}'

    # Keep this threshold aligned with javascript_visual_number_formatter:
    # ordinary engineering values remain easy to scan while genuinely large
    # or small magnitudes retain their scale explicitly.
    if exponent >= significant or exponent < -4:
        mantissa = trim_fraction(format(decimal, f'.{significant - 1}e').split('e', 1)[0])
        scientific_exponent = int(format(decimal, f'.{significant - 1}e').split('e', 1)[1])
        return f'{mantissa}e{scientific_exponent:+d}'

    places = max(0, significant - exponent - 1)
    return trim_fraction(format(decimal, f'.{places}f'))


def javascript_visual_number_formatter(unit: str | None = None) -> str:
    """Return a bounded formatter for ECharts axis labels/tooltips."""
    suffix = f" {unit}" if unit else ''
    return (
        "(value) => { const n=Number(value); if (!Number.isFinite(n)) return '—'; "
        "if (n === 0) return '0" + suffix + "'; "
        "const scientific=Math.abs(n) >= 1e4 || Math.abs(n) < 1e-4; "
        "let s=scientific ? n.toExponential(3) : n.toFixed(4); "
        "if (scientific) { const parts=s.split('e'); "
        "s=parts[0].replace(/(\\.\\d*?[1-9])0+$|\\.0+$/,'$1') + 'e' + "
        "(Number(parts[1]) >= 0 ? '+' : '') + Number(parts[1]); } "
        "else s=s.replace(/(\\.\\d*?[1-9])0+$|\\.0+$/,'$1'); "
        "return s + '" + suffix + "'; }"
    )


__all__ = ['format_visual_number', 'javascript_visual_number_formatter']

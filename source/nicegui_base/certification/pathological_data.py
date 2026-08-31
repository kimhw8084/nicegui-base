from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Mapping


@dataclass(frozen=True, slots=True)
class PathologicalDataFixture:
    """Deterministic reusable data fixture used by certification and regressions."""

    key: str
    description: str
    factory: Callable[[], tuple[Mapping[str, Any], ...]]

    def rows(self) -> tuple[Mapping[str, Any], ...]:
        return self.factory()


def engineering_rows(count: int = 240) -> list[dict[str, Any]]:
    """Stable engineering records shared by the DataTable lab and QA tests."""
    if count < 0:
        raise ValueError('count must be >= 0')
    rows: list[dict[str, Any]] = []
    statuses = ('Normal', 'Normal', 'Normal', 'Watch', 'Critical', 'Maintenance')
    tools = ('ETCH-014', 'ETCH-021', 'CVD-008', 'CMP-004', 'PVD-011', 'MET-030')
    params = ('CD', 'Thickness', 'Overlay', 'Etch Rate')
    for i in range(count):
        status = statuses[(i * 7) % len(statuses)]
        value = 39.2 + math.sin(i / 7.2) * 2.1 + (i % 11) * .11
        rows.append({
            'id': f'MEAS-{100000 + i}', 'lot': f'L{260100 + i // 8}', 'wafer': f'W{1 + i % 25:02d}',
            'tool': tools[i % len(tools)], 'parameter': params[i % len(params)], 'value': round(value, 3),
            'status': status, 'yield': round(94.0 + ((i * 13) % 56) / 10, 1),
            'trend': [round(value + math.sin(j / 2) * .6, 2) for j in range(8)],
            'timestamp': f'2026-08-{18 + (i % 7):02d} {8 + i % 12:02d}:{(i * 7) % 60:02d}',
        })
    return rows


def _one_row() -> tuple[Mapping[str, Any], ...]:
    return tuple(engineering_rows(1))


def _large_rows() -> tuple[Mapping[str, Any], ...]:
    return tuple(engineering_rows(50_000))


def _wide_rows() -> tuple[Mapping[str, Any], ...]:
    return tuple({f'column_{i:03d}': f'value-{i:03d}' for i in range(99)} | {'id': 'WIDE-001'} for _ in range(1))


def _null_mixed_rows() -> tuple[Mapping[str, Any], ...]:
    return (
        {'id':'MIX-001','value':None,'text':'','flag':False,'mixed':1},
        {'id':'MIX-002','value':float('nan'),'text':'   ','flag':True,'mixed':'1'},
        {'id':'MIX-003','value':float('inf'),'text':'정상 Normal','flag':None,'mixed':1.0},
        {'id':'MIX-004','value':float('-inf'),'text':'零 / zero','flag':False,'mixed':'001'},
    )


def _extreme_string_rows() -> tuple[Mapping[str, Any], ...]:
    long_token = 'LOT-' + ('X' * 4096)
    return (
        {'id':'TXT-001','text':long_token,'csv':'=2+2','html':'<img src=x onerror=alert(1)>'},
        {'id':'TXT-002','text':'한글 English 日本語 العربية 🚀 ' * 80,'csv':'+SUM(A1:A2)','html':'<script>alert(1)</script>'},
        {'id':'TXT-003','text':'line1\nline2\ttab\rreturn','csv':'@cmd','html':'&lt;safe&gt;'},
    )


def _date_timezone_rows() -> tuple[Mapping[str, Any], ...]:
    return (
        {'id':'TIME-001','timestamp':'2026-03-08T01:59:59-06:00','zone':'America/Chicago','case':'pre-DST-gap'},
        {'id':'TIME-002','timestamp':'2026-03-08T03:00:00-05:00','zone':'America/Chicago','case':'post-DST-gap'},
        {'id':'TIME-003','timestamp':'2026-11-01T01:30:00-05:00','zone':'America/Chicago','case':'DST-fold-first'},
        {'id':'TIME-004','timestamp':'2026-11-01T01:30:00-06:00','zone':'America/Chicago','case':'DST-fold-second'},
        {'id':'TIME-005','timestamp':'2026-12-31T23:59:59+09:00','zone':'Asia/Seoul','case':'year-boundary'},
    )


PATHOLOGICAL_DATA_FIXTURES: dict[str, PathologicalDataFixture] = {
    'empty': PathologicalDataFixture('empty','Zero-row state.',lambda: ()),
    'one_row': PathologicalDataFixture('one_row','Single-row edge case.',_one_row),
    'fifty_thousand_rows': PathologicalDataFixture('fifty_thousand_rows','50k-row virtualization/performance case.',_large_rows),
    'one_hundred_columns': PathologicalDataFixture('one_hundred_columns','100-column horizontal geometry case.',_wide_rows),
    'null_mixed_numeric': PathologicalDataFixture('null_mixed_numeric','Null/NaN/infinity/mixed-type values.',_null_mixed_rows),
    'extreme_strings': PathologicalDataFixture('extreme_strings','Long, multilingual, CSV-formula and HTML-like strings.',_extreme_string_rows),
    'dates_timezones': PathologicalDataFixture('dates_timezones','DST gaps/folds and cross-zone date boundaries.',_date_timezone_rows),
}


def pathological_rows(key: str) -> tuple[Mapping[str, Any], ...]:
    try:
        fixture = PATHOLOGICAL_DATA_FIXTURES[key]
    except KeyError as exc:
        raise KeyError(f'unknown pathological fixture {key!r}; choose from {tuple(PATHOLOGICAL_DATA_FIXTURES)}') from exc
    return fixture.rows()


__all__ = ['PathologicalDataFixture','PATHOLOGICAL_DATA_FIXTURES','engineering_rows','pathological_rows']

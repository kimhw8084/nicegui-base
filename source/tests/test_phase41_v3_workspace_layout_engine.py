from __future__ import annotations

import pytest

from nicegui_base.workspace import GridPlacement, PanelSpec, WorkspaceBreakpoint, WorkspaceLayoutEngine


def assert_no_overlap(engine: WorkspaceLayoutEngine, breakpoint: WorkspaceBreakpoint) -> None:
    values = engine.layout(breakpoint)
    for index, left in enumerate(values):
        for right in values[index + 1:]:
            assert not left.intersects(right), (left, right)


def test_v3_workspace_grid_registers_deterministically_without_overlap_across_all_breakpoints():
    engine = WorkspaceLayoutEngine()
    for panel in (
        PanelSpec('kpis', preferred_columns=4, preferred_rows=2),
        PanelSpec('trend', preferred_columns=8, preferred_rows=5),
        PanelSpec('table', preferred_columns=12, preferred_rows=7),
        PanelSpec('inspector', preferred_columns=4, preferred_rows=6),
    ):
        engine.register_panel(panel)
    for breakpoint in WorkspaceBreakpoint:
        assert_no_overlap(engine, breakpoint)
        assert {item.panel_id for item in engine.layout(breakpoint)} == {'kpis', 'trend', 'table', 'inspector'}
    assert all(item.column == 0 and item.column_span == 4 for item in engine.layout(WorkspaceBreakpoint.PHONE))


def test_v3_workspace_move_resize_pushes_collisions_and_compacts_without_losing_panel_identity():
    engine = WorkspaceLayoutEngine()
    for key in ('a', 'b', 'c'):
        engine.register_panel(PanelSpec(key, preferred_columns=6, preferred_rows=3))
    before = {item.panel_id for item in engine.layout(WorkspaceBreakpoint.DESKTOP)}
    engine.move('c', WorkspaceBreakpoint.DESKTOP, column=0, row=0)
    resized = engine.resize('c', WorkspaceBreakpoint.DESKTOP, column_span=8, row_span=5)
    assert resized.panel_id == 'c' and resized.column_span == 8 and resized.row_span == 5
    assert {item.panel_id for item in engine.layout(WorkspaceBreakpoint.DESKTOP)} == before
    assert_no_overlap(engine, WorkspaceBreakpoint.DESKTOP)


def test_v3_workspace_constraints_locked_panels_and_grid_bounds_are_governed():
    engine = WorkspaceLayoutEngine()
    engine.register_panel(PanelSpec('locked', preferred_columns=6, min_columns=4, max_columns=8, locked=True))
    with pytest.raises(PermissionError):
        engine.move('locked', WorkspaceBreakpoint.DESKTOP, column=8, row=0)
    engine.register_panel(PanelSpec('flex', preferred_columns=6, min_columns=3, max_columns=7, min_rows=2, max_rows=5))
    placement = engine.resize('flex', WorkspaceBreakpoint.DESKTOP, column_span=99, row_span=99)
    assert placement.column_span == 7 and placement.row_span == 5 and placement.right <= 12


def test_v3_workspace_can_derive_phone_layout_from_desktop_and_preserve_order_without_overlap():
    engine = WorkspaceLayoutEngine()
    engine.register_panel(PanelSpec('left', preferred_columns=4, preferred_rows=4))
    engine.register_panel(PanelSpec('main', preferred_columns=8, preferred_rows=5))
    engine.move('main', WorkspaceBreakpoint.DESKTOP, column=4, row=0)
    engine.derive_breakpoint(WorkspaceBreakpoint.PHONE, source=WorkspaceBreakpoint.DESKTOP)
    phone = engine.layout(WorkspaceBreakpoint.PHONE)
    assert [item.panel_id for item in phone] == ['left', 'main']
    assert all(item.column == 0 and item.column_span == 4 for item in phone)
    assert_no_overlap(engine, WorkspaceBreakpoint.PHONE)


def test_v3_workspace_snapshot_restore_is_defensive_and_rehydrates_exact_geometry():
    engine = WorkspaceLayoutEngine()
    engine.register_panel(PanelSpec('a', preferred_columns=4, metadata={'role': 'metric'}))
    engine.register_panel(PanelSpec('b', preferred_columns=8))
    engine.move('b', WorkspaceBreakpoint.DESKTOP, column=4, row=0)
    snapshot = engine.snapshot()
    clone = WorkspaceLayoutEngine(); calls=[]; clone.watch(lambda value: calls.append(value.revision))
    clone.restore(snapshot)
    assert clone.layout(WorkspaceBreakpoint.DESKTOP) == engine.layout(WorkspaceBreakpoint.DESKTOP)
    assert clone.panels['a'].metadata == {'role': 'metric'}
    assert calls == [1]


def test_v3_workspace_rejects_invalid_or_overlapping_snapshot_geometry():
    engine = WorkspaceLayoutEngine()
    engine.register_panel(PanelSpec('a', preferred_columns=6))
    engine.register_panel(PanelSpec('b', preferred_columns=6))
    snapshot = engine.snapshot()
    bad = type(snapshot)(
        schema_version=1,
        revision=0,
        panels=snapshot.panels,
        placements=(
            GridPlacement('a', WorkspaceBreakpoint.DESKTOP, 0, 0, 6, 4),
            GridPlacement('b', WorkspaceBreakpoint.DESKTOP, 0, 0, 6, 4),
        ),
    )
    with pytest.raises(ValueError, match='overlapping'):
        WorkspaceLayoutEngine().restore(bad)


def test_v3_workspace_breakpoint_resolution_uses_existing_design_constitution_thresholds():
    engine = WorkspaceLayoutEngine()
    assert engine.breakpoint_for_width(599) is WorkspaceBreakpoint.PHONE
    assert engine.breakpoint_for_width(600) is WorkspaceBreakpoint.TABLET
    assert engine.breakpoint_for_width(900) is WorkspaceBreakpoint.LAPTOP
    assert engine.breakpoint_for_width(1200) is WorkspaceBreakpoint.DESKTOP
    assert engine.breakpoint_for_width(1800) is WorkspaceBreakpoint.WIDE

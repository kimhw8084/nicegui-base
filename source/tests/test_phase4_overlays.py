import pytest

from nicegui_base import (
    DialogIntent, DialogSpec, DrawerSide, DrawerSpec, MenuItemSpec, MenuSpec, OverlayRole, OverlaySize, TooltipSpec,
)


def test_drawer_classes_are_semantic():
    spec = DrawerSpec('Tool detail', role=OverlayRole.DETAIL, side=DrawerSide.RIGHT, size=OverlaySize.LARGE, resizable=True)
    assert 'cui-drawer--right' in spec.classes
    assert 'cui-drawer--large' in spec.classes
    assert 'is-resizable' in spec.classes


def test_drawer_requires_title():
    with pytest.raises(ValueError):
        DrawerSpec('')


def test_typed_confirmation_requires_destructive():
    with pytest.raises(ValueError):
        DialogSpec('Delete', typed_confirmation='DELETE')


def test_danger_dialog_class():
    spec = DialogSpec('Delete record', intent=DialogIntent.DANGER, destructive=True, primary_label='Delete')
    assert 'cui-dialog--danger' in spec.classes


def test_menu_keys_must_be_unique():
    with pytest.raises(ValueError):
        MenuSpec((MenuItemSpec('x', 'First'), MenuItemSpec('x', 'Second')))


def test_menu_height_is_bounded():
    with pytest.raises(ValueError):
        MenuSpec((MenuItemSpec('x', 'First'),), max_height=80)


def test_tooltip_validates_delay():
    with pytest.raises(ValueError):
        TooltipSpec('Help', delay_ms=-1)

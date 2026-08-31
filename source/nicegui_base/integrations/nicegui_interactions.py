from __future__ import annotations

import inspect
import json
from contextlib import AbstractContextManager
from itertools import count
from typing import Any, Callable, Sequence

from nicegui_base.forms import (
    DirtyStateGuardSpec, FormActionsSpec, FormFieldSpec, FormSectionSpec, FormSpec, ValidationSummarySpec,
)
from nicegui_base.filters import ActiveFilter, FilterBarSpec, FilterPreset, SavedFilterView as SavedFilterViewSpec
from nicegui_base.feedback import (
    AlertSpec, AsyncContentSpec, AsyncState, BannerSpec, FeedbackIntent, ProgressSpec, SkeletonSpec,
    StateKind, StateViewSpec, ToastSpec,
)
from nicegui_base.overlays import (
    DialogIntent, DialogSpec, DrawerSide, DrawerSpec, MenuItemSpec, MenuSpec, OverlayRole, OverlaySize,
    PopoverSpec, TooltipSpec,
)
from nicegui_base.visual import render_icon_svg
from nicegui_base.integrations.nicegui_feedback_runtime import show_company_toast


_IDS = count(1)


def _ui():
    try:
        from nicegui import ui
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError('NiceGUI is required to render nicegui_base interaction components.') from exc
    return ui


def _call_with_optional_event(callback: Callable[..., Any], event: Any = None) -> Any:
    """Choose callback arity before invocation so callback TypeErrors propagate."""
    try:
        signature = inspect.signature(callback)
    except (TypeError, ValueError):
        return callback(event)
    try:
        signature.bind(event)
    except TypeError:
        signature.bind()  # raises a truthful arity error if neither form is legal
        return callback()
    return callback(event)


async def _invoke(callback: Callable[..., Any] | None, event: Any = None) -> Any:
    if callback is None:
        return None
    value = _call_with_optional_event(callback, event)
    if inspect.isawaitable(value):
        return await value
    return value


def _register_client_delete(ui: Any, callback: Callable[..., Any]) -> bool:
    context=getattr(ui, 'context', None)
    client=getattr(context, 'client', None)
    on_delete=getattr(client, 'on_delete', None)
    if callable(on_delete):
        on_delete(callback)
        return True
    return False


def _icon(ui, key: str, *, label: str | None = None, size: str = 'sm'):
    return ui.html(render_icon_svg(key, size=size, label=label), sanitize=False).classes('cui-svg-icon-host')


def _overlay_client_event(ui: Any, kind: str, opened: bool, overlay_id: str) -> Any:
    """Synchronize focus, scroll-lock and Escape ownership on the client."""
    action = 'open' if opened else 'close'
    payload = json.dumps({'kind': kind, 'id': overlay_id})
    return ui.run_javascript(
        """
        window.__companyUiOverlayManager ||= (() => {
          const stack = [];
          const origins = new Map();
          const lockOwners = new Set();
          let priorOverflow = null;
          const lockingKinds = new Set(['dialog', 'drawer']);
          const syncScrollLock = () => {
            if (lockOwners.size) {
              if (priorOverflow === null) priorOverflow = document.body.style.overflow;
              document.body.style.overflow = 'hidden';
              document.body.dataset.cuiScrollLocked = 'true';
            } else if (priorOverflow !== null) {
              document.body.style.overflow = priorOverflow;
              delete document.body.dataset.cuiScrollLocked;
              priorOverflow = null;
            }
          };
          const open = detail => {
            const id = detail?.id;
            if (!id) return;
            const existing = stack.findIndex(item => item.id === id);
            if (existing >= 0) stack.splice(existing, 1);
            origins.set(id, document.activeElement);
            stack.push({id, kind: detail.kind});
            if (lockingKinds.has(detail.kind)) lockOwners.add(id);
            syncScrollLock();
          };
          const close = detail => {
            const id = detail?.id;
            if (!id) return;
            const index = stack.findIndex(item => item.id === id);
            if (index >= 0) stack.splice(index, 1);
            lockOwners.delete(id);
            syncScrollLock();
            const origin = origins.get(id);
            origins.delete(id);
            requestAnimationFrame(() => {
              if (origin?.isConnected && typeof origin.focus === 'function') origin.focus({preventScroll:true});
            });
          };
          document.addEventListener('cui:overlay-open', event => open(event.detail));
          document.addEventListener('cui:overlay-close', event => close(event.detail));
          addEventListener('keydown', event => {
            if (event.key !== 'Escape' || event.defaultPrevented || !stack.length) return;
            const top = stack[stack.length - 1];
            const surface = document.querySelector(`[data-cui-overlay-id="${CSS.escape(top.id)}"]`);
            if (!surface || surface.dataset.cuiDismissible !== 'true') return;
            const closeButton = surface.querySelector('[data-cui-overlay-close]');
            if (!closeButton) return;
            event.preventDefault();
            event.stopImmediatePropagation();
            closeButton.click();
          }, true);
          addEventListener('pagehide', () => {
            stack.splice(0); origins.clear(); lockOwners.clear(); syncScrollLock();
          }, {once:true});
          return {stack, lockOwners, syncScrollLock};
        })();
        window.__companyUiTooltip?.hide?.();
        """
        f"document.dispatchEvent(new CustomEvent('cui:overlay-{action}', {{detail: {payload}}}));"
    )


class Form(AbstractContextManager):
    """Semantic form container with runtime validation and optional unsaved-change protection."""
    def __init__(self, key: str, *, title: str | None = None, description: str | None = None,
                 dirty_guard: bool = True, validate_on: str = 'hybrid'):
        self.spec = FormSpec(key=key, title=title, description=description, dirty_guard=dirty_guard, validate_on=validate_on)
        self.element = _ui().element('form').classes('cui-form').props(f'data-form-key="{key}" novalidate')
        self.dirty_guard = DirtyStateGuard(enabled=dirty_guard) if dirty_guard else None

    def __enter__(self):
        self.element.__enter__(); return self

    def __exit__(self, exc_type, exc, tb): return self.element.__exit__(exc_type, exc, tb)

    def mark_dirty(self) -> None:
        if self.dirty_guard:self.dirty_guard.set_dirty(True)

    def mark_clean(self) -> None:
        if self.dirty_guard:self.dirty_guard.mark_clean()

    def bind_dirty(self, *elements: Any) -> None:
        for element in elements:
            if hasattr(element,'on'):
                element.on('update:model-value', lambda e=None: self.mark_dirty())

    def dispose(self) -> None:
        if self.dirty_guard:
            self.dirty_guard.remove()


    async def validate(self) -> bool:
        """Validate descendant NiceGUI controls which expose ``validate``."""
        valid=True
        descendants=getattr(self.element,'descendants',lambda **_:())(include_self=False)
        for element in list(descendants):
            validator=getattr(element,'validate',None)
            if not callable(validator):continue
            try:
                inspect.signature(validator).bind()
            except (TypeError, ValueError):
                # A descendant's validate method that requires arguments is not
                # the NiceGUI no-argument validation contract and is skipped.
                continue
            result=validator()
            if inspect.isawaitable(result):result=await result
            valid=bool(result) and valid
        return valid

    async def submit(self, callback: Callable[...,Any] | None=None, event:Any=None) -> bool:
        if not await self.validate(): return False
        await _invoke(callback,event); self.mark_clean(); return True


class FormField(AbstractContextManager):
    def __init__(self, key: str, label: str, *, description: str | None = None, required: bool = False,
                 error: str | None = None, full_width: bool = False):
        self.spec = FormFieldSpec(key, label, description, required, error, full_width)
        self.field_id = f'cui-form-field-{next(_IDS)}'
        self.label_id = f'{self.field_id}-label'
        self.description_id = f'{self.field_id}-description'
        self.error_id = f'{self.field_id}-error'
        self.element = _ui().element('div').classes(self.spec.classes).props(
            f'role="group" aria-labelledby="{self.label_id}"'
        )

    def __enter__(self):
        ui = _ui(); self.element.__enter__()
        with ui.element('div').classes('cui-field-label-row'):
            ui.label(self.spec.label).classes('cui-field-label').props(f'id="{self.label_id}"')
            if self.spec.required:
                ui.label('*').classes('cui-field-required').props('aria-hidden="true"')
        return self

    def __exit__(self, exc_type, exc, tb):
        ui = _ui()
        if self.spec.description:
            ui.label(self.spec.description).classes('cui-field-description').props(f'id="{self.description_id}"')
        if self.spec.error:
            ui.label(self.spec.error).classes('cui-field-error').props(f'id="{self.error_id}" role="alert"')
        return self.element.__exit__(exc_type, exc, tb)


class FormSection(AbstractContextManager):
    def __init__(self, title: str, *, description: str | None = None, collapsible: bool = False, default_open: bool = True):
        self.spec = FormSectionSpec(title=title, description=description, collapsible=collapsible, default_open=default_open)
        ui = _ui()
        if collapsible:
            self.element = ui.expansion(title, value=default_open).classes('cui-form-section cui-collapsible')
        else:
            self.element = ui.element('section').classes('cui-form-section')

    def __enter__(self):
        ui = _ui(); self.element.__enter__()
        if not self.spec.collapsible:
            with ui.element('div').classes('cui-form-section__head'):
                with ui.column().classes('cui-form-section__copy'):
                    ui.label(self.spec.title).classes('cui-form-section__title')
                    if self.spec.description:
                        ui.label(self.spec.description).classes('cui-form-section__description')
        elif self.spec.description:
            ui.label(self.spec.description).classes('cui-form-section__description')
        return self

    def __exit__(self, exc_type, exc, tb):
        return self.element.__exit__(exc_type, exc, tb)


class ValidationSummary:
    def __init__(self, spec: ValidationSummarySpec):
        self.spec = spec; ui = _ui()
        with ui.element('div').classes('cui-validation-summary').props('role="alert" aria-live="polite"') as self.element:
            _icon(ui, 'warning', label='Validation issues')
            with ui.element('div'):
                ui.label(spec.title).classes('cui-validation-summary__title')
                for issue in spec.issues:
                    ui.label(f'{issue.field}: {issue.message}').classes('cui-validation-summary__item')


class FormActions:
    def __init__(self, *, primary_label: str = 'Save', secondary_label: str = 'Cancel',
                 destructive_label: str | None = None, sticky: bool = False, align: str = 'end',
                 on_primary: Callable[..., Any] | None = None, on_secondary: Callable[..., Any] | None = None,
                 on_destructive: Callable[..., Any] | None = None, form: Form | None = None):
        self.spec = FormActionsSpec(primary_label, secondary_label, destructive_label, sticky, align)
        ui = _ui(); classes = f'cui-form-actions cui-form-actions--{align}' + (' is-sticky' if sticky else '')
        with ui.element('div').classes(classes) as self.element:
            if destructive_label:
                ui.button(destructive_label, on_click=on_destructive).props('flat no-caps').classes('cui-button cui-button--danger cui-control--medium')
            ui.element('div').classes('cui-form-actions__spacer')
            ui.button(secondary_label, on_click=on_secondary).props('flat no-caps').classes('cui-button cui-button--secondary cui-control--medium')
            async def primary(e=None):
                if form is not None: await form.submit(on_primary,e)
                else: await _invoke(on_primary,e)
            ui.button(primary_label, on_click=primary).props('unelevated no-caps').classes('cui-button cui-button--primary cui-control--medium')


class DirtyStateGuard:
    """Browser and route-leave protection for forms with unsaved changes.

    The browser controls the wording of the native ``beforeunload`` prompt. Internal
    anchor navigation uses the configured message via ``window.confirm``.
    """
    def __init__(self, enabled: bool = True, message: str = 'You have unsaved changes. Leave without saving?', *, dirty: bool = False):
        self.spec = DirtyStateGuardSpec(enabled=enabled, message=message)
        self.guard_id = f'cui-dirty-{next(_IDS)}'
        self._dirty = bool(dirty)
        self._removed = False
        if enabled:
            self._install()
            _register_client_delete(_ui(), self.remove)

    def _install(self) -> None:
        ui = _ui()
        gid = json.dumps(self.guard_id); message = json.dumps(self.spec.message)
        dirty = 'true' if self._dirty else 'false'
        ui.add_body_html(f'''<script>
(() => {{
  window.__companyUiDirtyGuards = window.__companyUiDirtyGuards || {{}};
  const id = {gid};
  if (window.__companyUiDirtyGuards[id]) return;
  const state = {{dirty:{dirty}, message:{message}, bypass:false}};
  const beforeUnload = (e) => {{
    if (!state.dirty || state.bypass) return;
    e.preventDefault();
    e.returnValue = '';
  }};
  const clickCapture = (e) => {{
    if (!state.dirty || state.bypass) return;
    const anchor = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!anchor || anchor.target === '_blank' || anchor.hasAttribute('download')) return;
    const href = anchor.getAttribute('href') || '';
    if (!href || href.startsWith('#') || href.startsWith('javascript:')) return;
    if (!window.confirm(state.message)) {{ e.preventDefault(); e.stopImmediatePropagation(); }}
    else {{ state.bypass = true; setTimeout(() => state.bypass = false, 1000); }}
  }};
  const cleanup = () => {{
    window.removeEventListener('beforeunload', beforeUnload);
    document.removeEventListener('click', clickCapture, true);
    window.removeEventListener('pagehide', cleanup);
    delete window.__companyUiDirtyGuards[id];
  }};
  window.addEventListener('beforeunload', beforeUnload);
  document.addEventListener('click', clickCapture, true);
  window.addEventListener('pagehide', cleanup, {{once:true}});
  window.__companyUiDirtyGuards[id] = {{state, beforeUnload, clickCapture, cleanup}};
}})();
</script>''')

    def set_dirty(self, dirty: bool = True) -> None:
        self._dirty = bool(dirty)
        if not self.spec.enabled:
            return
        ui = _ui(); gid = json.dumps(self.guard_id); value = 'true' if self._dirty else 'false'
        ui.run_javascript(f'window.__companyUiDirtyGuards?.[{gid}] && (window.__companyUiDirtyGuards[{gid}].state.dirty={value})')

    def mark_clean(self) -> None:
        self.set_dirty(False)

    def remove(self) -> None:
        if not self.spec.enabled or self._removed:
            return
        self._removed = True
        ui = _ui(); gid = json.dumps(self.guard_id)
        ui.run_javascript(f'''(() => {{
          const g=window.__companyUiDirtyGuards?.[{gid}]; if(!g) return;
          if (typeof g.cleanup === 'function') g.cleanup();
          else {{
            window.removeEventListener('beforeunload', g.beforeUnload);
            document.removeEventListener('click', g.clickCapture, true);
            delete window.__companyUiDirtyGuards[{gid}];
          }}
        }})()''')


class FilterChip:
    def __init__(self, active: ActiveFilter, *, on_remove: Callable[..., Any] | None = None):
        self.active = active; ui = _ui()
        with ui.element('span').classes('cui-filter-chip') as self.element:
            ui.label(active.label + ':').classes('cui-filter-chip__label')
            ui.label(active.display_value).classes('cui-filter-chip__value')
            if active.removable:
                button = ui.button(on_click=on_remove).props('flat dense round aria-label="Remove filter"').classes('cui-icon-button')
                with button: _icon(ui, 'close', label='Remove filter', size='xs')


class FilterBar(AbstractContextManager):
    def __init__(self, spec: FilterBarSpec):
        self.spec = spec; self.element = _ui().element('section').classes('cui-filter-bar').props('aria-label="Filters"')

    def __enter__(self):
        self.element.__enter__(); return self

    def __exit__(self, exc_type, exc, tb):
        return self.element.__exit__(exc_type, exc, tb)


class FilterPresetSelector:
    def __init__(self, presets: Sequence[FilterPreset], *, active_key: str | None = None,
                 on_select: Callable[..., Any] | None = None):
        self.presets = tuple(presets); ui = _ui()
        with ui.element('div').classes('cui-preset-strip') as self.element:
            for preset in presets:
                cls = 'cui-preset' + (' is-active' if preset.key == active_key else '')
                callback = (lambda e, p=preset: on_select(p) if on_select else None)
                ui.button(preset.label, on_click=callback).props('flat dense no-caps').classes(cls)


class SavedFilterView:
    def __init__(self, views: Sequence[SavedFilterViewSpec], *, value: str | None = None,
                 on_change: Callable[..., Any] | None = None):
        self.views = tuple(views)
        options = {view.key: view.label for view in views}
        self.element = _ui().select(options=options, value=value, on_change=on_change, clearable=False).props(
            'outlined dense options-dense aria-label="Saved filter view"'
        ).classes('cui-field-control cui-select')


class _Drawer(AbstractContextManager):
    role = OverlayRole.DETAIL
    def __init__(self, title: str, *, subtitle: str | None = None, side: DrawerSide = DrawerSide.RIGHT,
                 size: OverlaySize = OverlaySize.MEDIUM, dismissible: bool = True, resizable: bool = False,
                 persistent: bool = False):
        # Internal clicks/select-drags never dismiss the drawer. Dismissible drawers
        # retain conventional X/Escape/backdrop behavior; non-dismissible drawers are persistent.
        self.spec = DrawerSpec(title=title, role=self.role, side=side, size=size, dismissible=dismissible,
                               resizable=resizable, persistent=(persistent or not dismissible))
        self.subtitle = subtitle; ui = _ui()
        overlay_id = next(_IDS)
        self.overlay_id = f'cui-drawer-{overlay_id}'
        self.title_id = f'cui-drawer-title-{overlay_id}'
        self.subtitle_id = f'cui-drawer-subtitle-{overlay_id}' if self.subtitle else None
        labelled = f'aria-labelledby="{self.title_id}"'
        described = f' aria-describedby="{self.subtitle_id}"' if self.subtitle_id else ''
        self.dialog = ui.dialog().props('maximized transition-show=fade transition-hide=fade').classes('cui-drawer-host')
        if self.spec.persistent: self.dialog.props('persistent')
        with self.dialog:
            self.element = ui.element('aside').classes(self.spec.classes + ' cui-overlay-surface cui-overlay-surface--drawer').props(f'role="dialog" aria-modal="true" {labelled}{described} data-cui-overlay="drawer" data-cui-overlay-id="{self.overlay_id}" data-cui-dismissible="{str(self.spec.dismissible).lower()}" data-cui-overlay-role="{self.role.value}"')
            with self.element:
                with ui.element('div').classes('cui-drawer__header'):
                    with ui.element('div').classes('cui-drawer__copy'):
                        ui.label(self.spec.title).props(f'id="{self.title_id}"').classes('cui-drawer__title')
                        if self.subtitle: ui.label(self.subtitle).props(f'id="{self.subtitle_id}"').classes('cui-drawer__subtitle')
                    if self.spec.dismissible:
                        button = ui.button(on_click=self.close).props('flat round aria-label="Close" data-cui-overlay-close').classes('cui-icon-button cui-drawer__close')
                        with button: _icon(ui, 'close', label='Close')
                self.body = ui.element('div').classes('cui-drawer__body')

    def __enter__(self):
        self.open(); self.body.__enter__(); return self

    def __exit__(self, exc_type, exc, tb):
        return self.body.__exit__(exc_type, exc, tb)

    def open(self):
        _overlay_client_event(_ui(), 'drawer', True, self.overlay_id); self.dialog.open(); return self

    def close(self):
        self.dialog.close(); _overlay_client_event(_ui(), 'drawer', False, self.overlay_id)


class DetailDrawer(_Drawer): role = OverlayRole.DETAIL
class FormDrawer(_Drawer): role = OverlayRole.FORM
class FilterDrawer(_Drawer): role = OverlayRole.FILTER
class AdvancedFilterDrawer(FilterDrawer): pass
class InspectorDrawer(_Drawer): role = OverlayRole.INSPECTOR
class ActivityDrawer(_Drawer): role = OverlayRole.ACTIVITY
class ResponsiveDrawer(_Drawer): pass


class Dialog(AbstractContextManager):
    """Explicit-close Company dialog.

    The frame is built in ``__init__`` so ``ConfirmDialog(...).open()`` is fully
    functional, while ``with Dialog(...):`` still provides a body context. This
    removes the old empty-dialog failure mode from event callbacks.
    """
    def __init__(self, title: str, *, description: str | None = None, size: OverlaySize = OverlaySize.SMALL,
                 dismissible: bool = True, primary_label: str | None = None, secondary_label: str | None = 'Cancel',
                 on_primary: Callable[..., Any] | None = None, on_secondary: Callable[..., Any] | None = None,
                 close_on_primary: bool = True, close_on_secondary: bool = True,
                 intent: DialogIntent = DialogIntent.DEFAULT, destructive: bool = False,
                 typed_confirmation: str | None = None):
        self.spec = DialogSpec(title=title, description=description, size=size, dismissible=dismissible,
                               primary_label=primary_label, secondary_label=secondary_label,
                               intent=intent, destructive=destructive, typed_confirmation=typed_confirmation,
                               close_on_primary=close_on_primary, close_on_secondary=close_on_secondary)
        self.on_primary = on_primary; self.on_secondary = on_secondary
        self.primary_button = None; self.confirmation_input = None
        overlay_id = next(_IDS)
        self.overlay_id = f'cui-dialog-{overlay_id}'
        self.title_id = f'cui-dialog-title-{overlay_id}'
        self.description_id = f'cui-dialog-description-{overlay_id}' if self.spec.description else None
        labelled = f'aria-labelledby="{self.title_id}"'
        described = f' aria-describedby="{self.description_id}"' if self.description_id else ''
        ui = _ui(); self.dialog = ui.dialog().props('transition-show=fade transition-hide=fade')
        if not self.spec.dismissible: self.dialog.props('persistent')
        with self.dialog:
            with ui.element('section').classes(self.spec.classes + ' cui-overlay-surface cui-overlay-surface--dialog').props(f'role="dialog" aria-modal="true" {labelled}{described} data-cui-overlay="dialog" data-cui-overlay-id="{self.overlay_id}" data-cui-dismissible="{str(self.spec.dismissible).lower()}" data-cui-dialog-intent="{self.spec.intent.value}"') as self.element:
                with ui.element('div').classes('cui-dialog__head'):
                    with ui.element('div').classes('cui-dialog__copy'):
                        ui.label(self.spec.title).props(f'id="{self.title_id}"').classes('cui-dialog__title')
                        if self.spec.description: ui.label(self.spec.description).props(f'id="{self.description_id}"').classes('cui-dialog__description')
                    if self.spec.dismissible:
                        close = ui.button(on_click=self.close).props('flat round aria-label="Close" data-cui-overlay-close').classes('cui-icon-button cui-dialog__close')
                        with close: _icon(ui, 'close', label='Close')
                if self.spec.typed_confirmation:
                    phrase = self.spec.typed_confirmation
                    with ui.element('div').classes('cui-dialog__confirmation'):
                        ui.label(f'Type “{phrase}” to confirm').classes('cui-field-label')
                        self.confirmation_input = ui.input(
                            on_change=lambda e: self._set_confirmation_ready(getattr(e, 'value', '')),
                        ).props(f'outlined dense hide-bottom-space autocomplete=off autofocus aria-label="Type {phrase} to confirm"').classes('cui-field-control cui-field-width--full cui-dialog__confirmation-input')
                self.body = ui.element('div').classes('cui-dialog__body')
                self._render_footer()

    def __enter__(self):
        self.open(); self.body.__enter__(); return self

    def _set_confirmation_ready(self, value: str) -> None:
        if self.primary_button is None or not self.spec.typed_confirmation: return
        if value == self.spec.typed_confirmation: self.primary_button.enable()
        else: self.primary_button.disable()

    async def _primary(self, event=None):
        await _invoke(self.on_primary, event)
        if self.spec.close_on_primary: self.close()

    async def _secondary(self, event=None):
        await _invoke(self.on_secondary, event)
        if self.spec.close_on_secondary: self.close()

    def _render_footer(self) -> None:
        if not self.spec.primary_label and not self.spec.secondary_label: return
        ui = _ui()
        with ui.element('div').classes('cui-dialog__footer'):
            ui.element('div').classes('cui-dialog__footer-spacer')
            if self.spec.secondary_label:
                ui.button(self.spec.secondary_label, on_click=self._secondary).props('flat no-caps').classes('cui-button cui-button--secondary cui-control--medium')
            if self.spec.primary_label:
                intent = 'danger' if self.spec.destructive else 'primary'
                self.primary_button = ui.button(self.spec.primary_label, on_click=self._primary).props('unelevated no-caps').classes(f'cui-button cui-button--{intent} cui-control--medium')
                if self.spec.typed_confirmation: self.primary_button.disable()

    def __exit__(self, exc_type, exc, tb):
        return self.body.__exit__(exc_type, exc, tb)

    def open(self):
        _overlay_client_event(_ui(), 'dialog', True, self.overlay_id); self.dialog.open(); return self

    def close(self):
        self.dialog.close(); _overlay_client_event(_ui(), 'dialog', False, self.overlay_id)


class ConfirmDialog(Dialog):
    def __init__(self, title: str, *, description: str | None = None, primary_label: str = 'Confirm',
                 secondary_label: str = 'Cancel', on_confirm: Callable[..., Any] | None = None,
                 on_cancel: Callable[..., Any] | None = None):
        super().__init__(title, description=description, intent=DialogIntent.CONFIRM,
                         primary_label=primary_label, secondary_label=secondary_label,
                         on_primary=on_confirm, on_secondary=on_cancel)


class DangerConfirmDialog(Dialog):
    def __init__(self, title: str, *, description: str | None = None, primary_label: str = 'Delete',
                 secondary_label: str = 'Cancel', typed_confirmation: str | None = None,
                 on_confirm: Callable[..., Any] | None = None, on_cancel: Callable[..., Any] | None = None):
        super().__init__(title, description=description, intent=DialogIntent.DANGER, destructive=True,
                         primary_label=primary_label, secondary_label=secondary_label,
                         typed_confirmation=typed_confirmation, on_primary=on_confirm, on_secondary=on_cancel)


class FormDialog(Dialog): pass
class PreviewDialog(Dialog): pass
class FullScreenDialog(Dialog):
    def __init__(self, title: str, **kwargs): super().__init__(title, size=OverlaySize.FULL, **kwargs)


class Tooltip:
    """Company-owned transient tooltip with deterministic lifetime and viewport clamping."""
    def __init__(self, text: str, *, delay_ms: int = 450):
        self.spec = TooltipSpec(text=text, delay_ms=delay_ms)

    def attach(self, element):
        ui = _ui(); token = f'cui-tooltip-target-{next(_IDS)}'
        element.classes(f'cui-tooltip-target {token}')
        text = json.dumps(self.spec.text); delay = int(self.spec.delay_ms); max_width = int(self.spec.max_width)
        ui.run_javascript(f"""(() => {{
          const install = () => {{
            const target = document.querySelector('.{token}');
            if (!target || target.dataset.cuiTooltipBound === '1') return;
            target.dataset.cuiTooltipBound = '1';
            window.__companyUiTooltip = window.__companyUiTooltip || (() => {{
              let node = null, timer = null, targetEl = null;
              const hide = () => {{
                if (timer) {{ clearTimeout(timer); timer = null; }}
                if (node) {{ node.remove(); node = null; }}
                targetEl = null;
              }};
              const position = () => {{
                if (!node || !targetEl) return;
                const r = targetEl.getBoundingClientRect(), t = node.getBoundingClientRect(), edge = 10, gap = 8;
                let left = r.left + r.width / 2 - t.width / 2;
                let top = r.top - t.height - gap;
                if (top < edge) top = r.bottom + gap;
                left = Math.max(edge, Math.min(left, innerWidth - t.width - edge));
                top = Math.max(edge, Math.min(top, innerHeight - t.height - edge));
                node.style.left = `${{left}}px`; node.style.top = `${{top}}px`;
              }};
              const show = (el, copy, wait, maxWidth) => {{
                hide(); targetEl = el;
                timer = setTimeout(() => {{
                  if (!el.matches(':hover,:focus-visible,:focus-within')) return;
                  node = document.createElement('div');
                  node.className = 'cui-tooltip cui-tooltip--company';
                  node.setAttribute('role', 'tooltip'); node.textContent = copy;
                  node.style.maxWidth = `${{maxWidth}}px`; document.body.appendChild(node); position();
                }}, wait);
              }};
              addEventListener('resize', hide, {{passive:true}});
              addEventListener('scroll', hide, {{passive:true,capture:true}});
              document.addEventListener('pointerdown', hide, true);
              document.addEventListener('cui:overlay-open', hide);
              return {{show, hide}};
            }})();
            const manager = window.__companyUiTooltip;
            target.addEventListener('mouseenter', () => manager.show(target, {text}, {delay}, {max_width}));
            target.addEventListener('mouseleave', manager.hide);
            target.addEventListener('focusin', () => manager.show(target, {text}, Math.min({delay}, 180), {max_width}));
            target.addEventListener('focusout', manager.hide);
          }};
          requestAnimationFrame(install);
        }})()""")
        return element


class Popover(AbstractContextManager):
    def __init__(self, *, title: str | None = None):
        self.spec = PopoverSpec(title=title); ui = _ui(); self.overlay_id=f'cui-popover-{next(_IDS)}'
        self.element = ui.menu().props(f'anchor="bottom left" self="top left" :offset="[0,8]" data-cui-overlay-id="{self.overlay_id}" data-cui-dismissible="true"').classes('cui-popover cui-overlay-surface cui-overlay-surface--popover')
        self.element.on('show', lambda *_: _overlay_client_event(ui,'popover',True,self.overlay_id))
        self.element.on('hide', lambda *_: _overlay_client_event(ui,'popover',False,self.overlay_id))
    def __enter__(self):
        self.element.__enter__()
        if self.spec.title:
            _ui().label(self.spec.title).classes('cui-popover__title')
        return self
    def __exit__(self, exc_type, exc, tb): return self.element.__exit__(exc_type, exc, tb)
    def open(self): self.element.open(); return self
    def close(self): self.element.close()


class DropdownMenu:
    def __init__(self, items: Sequence[MenuItemSpec]):
        self.spec = MenuSpec(tuple(items)); ui = _ui(); self.overlay_id=f'cui-menu-{next(_IDS)}'
        self.element = ui.menu().props(f'anchor="bottom left" self="top left" :offset="[0,8]" data-cui-overlay-id="{self.overlay_id}" data-cui-dismissible="true"').classes('cui-menu cui-overlay-surface cui-overlay-surface--popover')
        self.element.on('show', lambda *_: _overlay_client_event(ui,'menu',True,self.overlay_id))
        self.element.on('hide', lambda *_: _overlay_client_event(ui,'menu',False,self.overlay_id))
        with self.element:
            for item in items:
                if item.separator_before: ui.separator().classes('cui-menu-separator')
                cls = 'cui-menu-item' + (' is-danger' if item.danger else '')
                async def handler(e=None, _item=item):
                    await _invoke(_item.on_select, e)
                    if _item.close_on_select:
                        self.element.close()
                button = ui.button(on_click=handler).props('flat dense no-caps').classes(cls)
                with button:
                    if item.icon: _icon(ui, item.icon, size='xs')
                    ui.label(item.label)
                    if item.shortcut: ui.label(item.shortcut).classes('cui-menu-shortcut')
                if item.disabled: button.disable()


class ActionMenu(DropdownMenu): pass


class ContextMenu:
    """Right-click menu positioned by Quasar/NiceGUI at the actual pointer."""
    def __init__(self, items: Sequence[MenuItemSpec]):
        self.spec = MenuSpec(tuple(items)); ui = _ui(); self.overlay_id=f'cui-context-menu-{next(_IDS)}'
        self.element = ui.context_menu().props(f'data-cui-overlay-id="{self.overlay_id}" data-cui-dismissible="true"').classes('cui-menu cui-context-menu cui-overlay-surface cui-overlay-surface--popover')
        self.element.on('show', lambda *_: _overlay_client_event(ui,'menu',True,self.overlay_id))
        self.element.on('hide', lambda *_: _overlay_client_event(ui,'menu',False,self.overlay_id))
        with self.element:
            for item in items:
                if item.separator_before: ui.separator().classes('cui-menu-separator')
                cls = 'cui-menu-item' + (' is-danger' if item.danger else '')
                async def handler(e=None, _item=item):
                    await _invoke(_item.on_select, e)
                    if _item.close_on_select: self.element.close()
                button = ui.button(on_click=handler).props('flat dense no-caps').classes(cls)
                with button:
                    if item.icon: _icon(ui, item.icon, size='xs')
                    ui.label(item.label)
                    if item.shortcut: ui.label(item.shortcut).classes('cui-menu-shortcut')
                if item.disabled: button.disable()


class Toast:
    def __init__(self, message: str, *, intent: FeedbackIntent = FeedbackIntent.INFO, duration_ms: int = 3500, dismissible: bool = True):
        self.spec = ToastSpec(message=message, intent=intent, duration_ms=duration_ms, dismissible=dismissible)

    def show(self):
        return show_company_toast(_ui(), self.spec.message, intent=self.spec.intent.value, duration_ms=self.spec.duration_ms, dismissible=self.spec.dismissible)


class _Alert:
    spec: AlertSpec | BannerSpec
    icon_map = {
        FeedbackIntent.INFO: 'info', FeedbackIntent.SUCCESS: 'success', FeedbackIntent.WARNING: 'warning',
        FeedbackIntent.DANGER: 'error', FeedbackIntent.NEUTRAL: 'info',
    }
    def _render(self):
        ui = _ui()
        with ui.element('div').classes(self.spec.classes).props('role="status" aria-live="polite"') as self.element:
            _icon(ui, self.icon_map[self.spec.intent], label=self.spec.intent.value)
            with ui.element('div').classes('cui-alert__copy'):
                ui.label(self.spec.title).classes('cui-alert__title')
                if self.spec.message: ui.label(self.spec.message).classes('cui-alert__message')
            if getattr(self.spec, 'dismissible', False):
                close = ui.button(on_click=lambda: self.element.delete()).props('flat round dense aria-label="Dismiss"').classes('cui-icon-button cui-alert__dismiss')
                with close: _icon(ui, 'close', label='Dismiss')


class Alert(_Alert):
    def __init__(self, title: str, *, message: str | None = None, intent: FeedbackIntent = FeedbackIntent.INFO, dismissible: bool = False):
        self.spec = AlertSpec(title, message, intent, dismissible); self._render()


class Banner(_Alert):
    def __init__(self, title: str, *, message: str | None = None, intent: FeedbackIntent = FeedbackIntent.INFO):
        self.spec = BannerSpec(title, message, intent); self._render()


class ValidationMessage(Alert):
    def __init__(self, message: str): super().__init__('Validation issue', message=message, intent=FeedbackIntent.DANGER)


class ProgressBar:
    """Company-owned progress track with deterministic animation and no in-track text."""
    def __init__(self, *, value: float | None = None, indeterminate: bool = False, label: str | None = None):
        self.spec = ProgressSpec(value=value, indeterminate=indeterminate)
        ui = _ui(); classes = 'cui-progress' + (' is-indeterminate' if indeterminate else '')
        props = ['role="progressbar"']
        if label: props.append(f'aria-label="{label}"')
        if value is not None and not indeterminate:
            props.extend(['aria-valuemin="0"', 'aria-valuemax="100"', f'aria-valuenow="{max(0,min(100,value*100)):.1f}"'])
        with ui.element('div').classes(classes).props(' '.join(props)) as self.element:
            pct = max(0.0, min(1.0, value or 0.0)) * 100.0
            style = '' if indeterminate else f'width:{pct:.4f}%'
            self.bar = ui.element('span').classes('cui-progress__bar').style(style)

    def set_value(self, value: float) -> None:
        """Update determinate progress without remounting or rendering text inside the track."""
        value = max(0.0, min(1.0, float(value)))
        self.spec = ProgressSpec(value=value, indeterminate=False)
        self.element.classes(remove='is-indeterminate')
        self.element.props(remove='aria-valuenow')
        self.element.props(add=f'aria-valuemin="0" aria-valuemax="100" aria-valuenow="{value*100:.1f}"')
        self.bar.style(replace=f'width:{value*100:.4f}%')

    def set_indeterminate(self, active: bool = True) -> None:
        """Toggle the single Company-owned indeterminate animation contract."""
        if active:
            self.spec = ProgressSpec(value=None, indeterminate=True)
            self.element.classes(add='is-indeterminate')
            self.element.props(remove='aria-valuenow aria-valuemin aria-valuemax')
            self.bar.style(replace='')
        else:
            self.element.classes(remove='is-indeterminate')
            value = 0.0 if self.spec.value is None else self.spec.value
            self.set_value(value)


class Spinner:
    def __init__(self): self.element = _ui().spinner().classes('cui-spinner').props('aria-label="Loading"')


class Skeleton:
    def __init__(self, *, kind: str = 'content', rows: int = 3):
        self.spec = SkeletonSpec(kind, rows); ui = _ui()
        with ui.element('div').classes('cui-skeleton').props('aria-hidden="true"') as self.element:
            for _ in range(rows): ui.element('div').classes('cui-skeleton__row')


class AsyncContent:
    """Render one canonical loading/ready/refreshing/empty/error lifecycle."""
    def __init__(self, state: AsyncState = AsyncState.IDLE, *, preserve_content_while_refreshing: bool = True,
                 content: Callable[[], Any] | None = None, on_retry: Callable[..., Any] | None = None,
                 empty_title: str = 'No data yet', empty_message: str | None = None,
                 error_title: str = 'Unable to load this content', error_message: str | None = None,
                 error_id: str | None = None, skeleton_rows: int = 4):
        self.spec = AsyncContentSpec(state, preserve_content_while_refreshing)
        self.on_retry = on_retry; self.empty_title = empty_title; self.empty_message = empty_message
        self.error_title = error_title; self.error_message = error_message; self.error_id = error_id
        self.skeleton_rows = skeleton_rows; self.element = None
        if content is not None:
            self.render(content)

    def render(self, content: Callable[[], Any]) -> Any:
        ui = _ui()
        busy = 'true' if self.spec.state in {AsyncState.IDLE, AsyncState.LOADING, AsyncState.REFRESHING} else 'false'
        with ui.element('section').classes(f'cui-async-content is-{self.spec.state.value}').props(f'aria-busy="{busy}"') as self.element:
            if self.spec.state in {AsyncState.IDLE, AsyncState.LOADING}:
                ui.label('Loading content').classes('cui-live-region').props('role="status" aria-live="polite" aria-atomic="true"')
                return Skeleton(rows=self.skeleton_rows)
            if self.spec.state is AsyncState.EMPTY:
                return EmptyState(self.empty_title, message=self.empty_message)
            if self.spec.state is AsyncState.ERROR:
                return ErrorState(self.error_title, message=self.error_message, error_id=self.error_id, on_retry=self.on_retry)
            if self.spec.state is AsyncState.READY:
                ui.label('Content loaded').classes('cui-live-region').props('role="status" aria-live="polite" aria-atomic="true"')
            elif self.spec.state is AsyncState.REFRESHING:
                ui.label('Refreshing content').classes('cui-live-region').props('role="status" aria-live="polite" aria-atomic="true"')
            elif self.spec.state is AsyncState.STALE:
                ui.label('Refresh failed. Showing previously loaded content.').classes('cui-live-region').props('role="status" aria-live="polite" aria-atomic="true"')
            result = content()
            if self.spec.state is AsyncState.REFRESHING:
                if not self.spec.preserve_content_while_refreshing:
                    return Skeleton(rows=self.skeleton_rows)
                with ui.element('div').classes('cui-async-refresh-indicator'):
                    ProgressBar(indeterminate=True)
                    ui.label('Refreshing…').classes('cui-field-description')
            elif self.spec.state is AsyncState.STALE:
                with ui.element('div').classes('cui-async-stale-indicator').props('role="status"'):
                    with ui.element('div').classes('cui-async-stale-indicator__copy'):
                        _icon(ui, 'warning', label='Refresh warning', size='xs')
                        ui.label(self.error_message or 'Refresh failed. Showing the last successfully loaded content.').classes('cui-field-description')
                    if self.on_retry is not None:
                        ui.button(self.spec.retry_label, on_click=self.on_retry).props('flat no-caps').classes('cui-button cui-button--secondary cui-control--small')
            return result


_STATE_ICONS = {
    StateKind.EMPTY: 'database', StateKind.NO_RESULTS: 'search', StateKind.ERROR: 'error',
    StateKind.PERMISSION: 'lock', StateKind.NOT_FOUND: 'search', StateKind.OFFLINE: 'warning',
}


class StateView:
    def __init__(self, spec: StateViewSpec, *, on_action: Callable[..., Any] | None = None,
                 on_secondary_action: Callable[..., Any] | None = None):
        self.spec = spec; ui = _ui(); self.on_action = on_action; self.on_secondary_action = on_secondary_action
        with ui.element('section').classes(spec.classes).props('role="status" aria-live="polite"') as self.element:
            with ui.element('div').classes('cui-state-view__mark'):
                _icon(ui, _STATE_ICONS[spec.kind], label=spec.kind.value, size='md')
            ui.label(spec.title).classes('cui-state-view__title')
            if spec.message: ui.label(spec.message).classes('cui-state-view__message')
            if spec.error_id: ui.label('Error ID: ' + spec.error_id).classes('cui-state-view__error-id')
            if spec.action_label or spec.secondary_action_label:
                with ui.element('div').classes('cui-state-view__actions'):
                    if spec.secondary_action_label:
                        ui.button(spec.secondary_action_label, on_click=on_secondary_action).props('flat no-caps').classes('cui-button cui-button--secondary cui-control--medium')
                    if spec.action_label:
                        ui.button(spec.action_label, on_click=on_action).props('unelevated no-caps').classes('cui-button cui-button--primary cui-control--medium')


class EmptyState(StateView):
    def __init__(self, title: str = 'No data yet', *, message: str | None = None, action_label: str | None = None,
                 compact: bool = False, on_action: Callable[..., Any] | None = None):
        super().__init__(StateViewSpec(StateKind.EMPTY, title, message, action_label=action_label, compact=compact), on_action=on_action)
class NoResultsState(StateView):
    def __init__(self, title: str = 'No matching results', *, message: str | None = None, action_label: str | None = 'Clear filters',
                 compact: bool = False, on_clear: Callable[..., Any] | None = None):
        super().__init__(StateViewSpec(StateKind.NO_RESULTS, title, message, action_label=action_label, compact=compact), on_action=on_clear)
class ErrorState(StateView):
    def __init__(self, title: str = 'Unable to load this content', *, message: str | None = None, error_id: str | None = None,
                 compact: bool = False, on_retry: Callable[..., Any] | None = None):
        super().__init__(StateViewSpec(StateKind.ERROR, title, message, action_label='Retry', error_id=error_id, compact=compact), on_action=on_retry)
class PermissionDeniedState(StateView):
    def __init__(self, title: str = 'Access restricted', *, message: str | None = None, compact: bool = False):
        super().__init__(StateViewSpec(StateKind.PERMISSION, title, message, compact=compact))
class NotFoundState(StateView):
    def __init__(self, title: str = 'Page not found', *, message: str | None = None, compact: bool = False,
                 on_back: Callable[..., Any] | None = None):
        super().__init__(StateViewSpec(StateKind.NOT_FOUND, title, message, action_label='Go back', compact=compact), on_action=on_back)
class OfflineState(StateView):
    def __init__(self, title: str = 'Connection unavailable', *, message: str | None = None, compact: bool = False,
                 on_retry: Callable[..., Any] | None = None):
        super().__init__(StateViewSpec(StateKind.OFFLINE, title, message, action_label='Retry', compact=compact), on_action=on_retry)

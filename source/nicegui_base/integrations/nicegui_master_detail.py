from __future__ import annotations

import json
from typing import Any


OVERLAY_MANAGER_RUNTIME = r'''(() => {
  if (window.__niceguiBaseOverlayManager) return;
  const focusables = surface => [...surface.querySelectorAll(
    'button,a[href],input,select,textarea,[contenteditable="true"],[tabindex]:not([tabindex="-1"])'
  )].filter(element => !element.disabled && element.getAttribute('aria-hidden') !== 'true' &&
    getComputedStyle(element).display !== 'none' && getComputedStyle(element).visibility !== 'hidden' &&
    element.getClientRects().length > 0);
  const visible = element => element?.isConnected && element.getClientRects().length > 0 &&
    getComputedStyle(element).visibility !== 'hidden' && getComputedStyle(element).display !== 'none';
  const stack = [];
  const origins = new Map();
  const lockOwners = new Set();
  let priorOverflow = null;
  const lockingKinds = new Set(['dialog', 'drawer', 'master-detail-context']);
  const surfaceFor = id => id ? document.querySelector(`[data-cui-overlay-id="${CSS.escape(id)}"]`) : null;
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
  const focusSurface = surface => {
    if (!surface) return;
    const items = focusables(surface);
    (items[0] || surface).focus?.({preventScroll: true});
  };
  const open = detail => {
    const id = detail?.id;
    if (!id) return;
    const existing = stack.findIndex(item => item.id === id);
    if (existing >= 0) stack.splice(existing, 1);
    if (!origins.has(id)) origins.set(id, visible(detail.origin) ? detail.origin : document.activeElement);
    stack.push({id, kind: detail.kind});
    if (lockingKinds.has(detail.kind)) lockOwners.add(id);
    syncScrollLock();
    requestAnimationFrame(() => focusSurface(surfaceFor(id)));
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
      if (visible(origin) && typeof origin.focus === 'function') origin.focus({preventScroll: true});
    });
  };
  document.addEventListener('cui:overlay-open', event => open(event.detail));
  document.addEventListener('cui:overlay-close', event => close(event.detail));
  addEventListener('focusin', event => {
    const top = stack[stack.length - 1];
    if (!top || !lockingKinds.has(top.kind)) return;
    const surface = surfaceFor(top.id);
    if (surface && !surface.contains(event.target)) {
      event.stopPropagation();
      focusSurface(surface);
    }
  }, true);
  addEventListener('keydown', event => {
    if (!stack.length) return;
    const top = stack[stack.length - 1];
    const surface = surfaceFor(top.id);
    if (!surface) return;
    if (event.key === 'Escape' && !event.defaultPrevented && surface.dataset.cuiDismissible === 'true') {
      const closeButton = surface.querySelector('[data-cui-overlay-close]');
      if (closeButton) {
        event.preventDefault();
        event.stopImmediatePropagation();
        closeButton.click();
      }
      return;
    }
    if (event.key !== 'Tab' || !lockingKinds.has(top.kind)) return;
    const items = focusables(surface);
    if (!items.length) {
      event.preventDefault();
      surface.focus?.({preventScroll: true});
      return;
    }
    const first = items[0];
    const last = items[items.length - 1];
    const active = document.activeElement;
    if (event.shiftKey && (active === first || !surface.contains(active))) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && (active === last || !surface.contains(active))) {
      event.preventDefault();
      first.focus();
    }
  }, true);
  addEventListener('pagehide', () => {
    stack.splice(0); origins.clear(); lockOwners.clear(); syncScrollLock();
  }, {once: true});
  window.__niceguiBaseOverlayManager = {stack, lockOwners, syncScrollLock};
})();'''


MASTER_DETAIL_CONTEXT_RUNTIME = f'''<script>
{OVERLAY_MANAGER_RUNTIME}
(() => {{
  if (window.NiceGUIBaseMasterDetailContext) return;
  const phone = matchMedia('(max-width: 599px)');
  const visible = element => element?.isConnected && element.getClientRects().length > 0 &&
    getComputedStyle(element).display !== 'none' && getComputedStyle(element).visibility !== 'hidden';
  const selectedRow = context => context.closest('[data-cui-pattern="master_detail"]')?.querySelector(
    '[data-cui-slot="data"] .ag-row-selected,[data-cui-slot="data"] [aria-selected="true"]'
  );
  const selectionKey = row => row?.getAttribute('row-id') || row?.dataset.rowId ||
    row?.getAttribute('aria-rowindex') || row?.textContent?.trim().slice(0, 120) || '';
  const patternFor = context => context.closest('[data-cui-pattern="master_detail"]');
  const restoreBackground = context => {{
    for (const item of context.__cuiInert || []) {{
      item.element.inert = item.inert;
      if (item.ariaHidden === null) item.element.removeAttribute('aria-hidden');
      else item.element.setAttribute('aria-hidden', item.ariaHidden);
    }}
    context.__cuiInert = [];
  }};
  const setBackground = (context, active) => {{
    const pattern = patternFor(context);
    if (!pattern) return;
    if (!active) {{ restoreBackground(context); return; }}
    context.__cuiInert = [];
    for (const element of [...pattern.children]) {{
      if (element === context || element.contains(context)) continue;
      context.__cuiInert.push({{element, inert: element.inert, ariaHidden: element.getAttribute('aria-hidden')}});
      element.inert = true;
      element.setAttribute('aria-hidden', 'true');
    }}
  }};
  const syncSemantics = (context, active) => {{
    context.setAttribute('role', active ? 'dialog' : 'region');
    context.setAttribute('aria-hidden', active ? 'false' : (phone.matches ? 'true' : 'false'));
    if (active) context.setAttribute('aria-modal', 'true');
    else context.removeAttribute('aria-modal');
  }};
  const activate = context => {{
    if (context.dataset.cuiOverlayActive === 'true') return;
    context.dataset.cuiOverlayActive = 'true';
    syncSemantics(context, true);
    setBackground(context, true);
    const origin = context.__cuiOrigin || selectedRow(context) || document.activeElement;
    document.dispatchEvent(new CustomEvent('cui:overlay-open', {{detail: {{
      id: context.dataset.cuiOverlayId, kind: 'master-detail-context', origin
    }}}}));
  }};
  const deactivate = context => {{
    if (context.dataset.cuiOverlayActive !== 'true') {{
      syncSemantics(context, false);
      return;
    }}
    restoreBackground(context);
    delete context.dataset.cuiOverlayActive;
    syncSemantics(context, false);
    document.dispatchEvent(new CustomEvent('cui:overlay-close', {{detail: {{
      id: context.dataset.cuiOverlayId, kind: 'master-detail-context'
    }}}}));
  }};
  const sync = context => {{
    if (!context) return;
    if (phone.matches && context.dataset.cuiContextState === 'open') activate(context);
    else deactivate(context);
  }};
  const open = (contextOrId, force = true) => {{
    const context = typeof contextOrId === 'number'
      ? getHtmlElement(contextOrId)
      : (typeof contextOrId === 'string' ? document.querySelector(`[data-cui-overlay-id="${{CSS.escape(contextOrId)}}"]`) : contextOrId);
    if (!context) return;
    if (force) delete context.dataset.cuiContextClosedSelection;
    context.__cuiOrigin = visible(document.activeElement) ? document.activeElement : selectedRow(context);
    context.dataset.cuiContextState = 'open';
    sync(context);
  }};
  const close = contextOrId => {{
    const context = typeof contextOrId === 'number'
      ? getHtmlElement(contextOrId)
      : (typeof contextOrId === 'string' ? document.querySelector(`[data-cui-overlay-id="${{CSS.escape(contextOrId)}}"]`) : contextOrId);
    if (!context) return;
    context.dataset.cuiContextClosedSelection = selectionKey(selectedRow(context));
    context.dataset.cuiContextState = 'closed';
    sync(context);
  }};
  const checkSelection = (context, force = false) => {{
    const row = selectedRow(context);
    if (!row) return;
    const key = selectionKey(row);
    if (force || key !== context.dataset.cuiContextClosedSelection) {{
      context.__cuiOrigin = row;
      delete context.dataset.cuiContextClosedSelection;
      context.dataset.cuiContextState = 'open';
      sync(context);
    }}
  }};
  const attachPattern = pattern => {{
    const data = pattern.querySelector('[data-cui-slot="data"]');
    const context = pattern.querySelector('[data-cui-master-detail-context]');
    if (!data || !context || data.dataset.cuiMasterDetailObserved === 'true') return;
    data.dataset.cuiMasterDetailObserved = 'true';
    new MutationObserver(() => checkSelection(context)).observe(data, {{subtree: true, attributes: true, attributeFilter: ['class', 'aria-selected']}});
    data.addEventListener('click', event => {{
      if (event.target.closest('.ag-row,[role="row"]')) setTimeout(() => checkSelection(context, true), 0);
    }}, true);
    data.addEventListener('keydown', event => {{
      if ((event.key === 'Enter' || event.key === ' ') && event.target.closest('.ag-row,[role="row"]'))
        setTimeout(() => checkSelection(context, true), 0);
    }}, true);
  }};
  const scan = () => document.querySelectorAll('[data-cui-pattern="master_detail"]').forEach(pattern => {{
    const context = pattern.querySelector('[data-cui-master-detail-context]');
    if (context) {{ attachPattern(pattern); sync(context); }}
  }});
  const observer = new MutationObserver(records => {{
    if (records.some(record => record.type === 'childList')) scan();
    for (const record of records) if (record.type === 'attributes') sync(record.target);
  }});
  observer.observe(document.documentElement, {{childList: true, subtree: true, attributes: true, attributeFilter: ['data-cui-context-state']}});
  const changed = () => scan();
  phone.addEventListener?.('change', changed);
  phone.addListener?.(changed);
  window.NiceGUIBaseMasterDetailContext = {{open, close, sync, scan}};
  scan();
}})();
</script>'''


def set_master_detail_context_state(ui: Any, element_id: int, state: str, *, force: bool = False) -> Any:
    if state not in {'open', 'closed'}:
        raise ValueError('MasterDetail context state must be open or closed.')
    method = 'open' if state == 'open' else 'close'
    return ui.run_javascript(
        f"window.NiceGUIBaseMasterDetailContext?.{method}(getHtmlElement({int(element_id)}), {str(force).lower()})"
    )


__all__ = ['MASTER_DETAIL_CONTEXT_RUNTIME', 'OVERLAY_MANAGER_RUNTIME', 'set_master_detail_context_state']

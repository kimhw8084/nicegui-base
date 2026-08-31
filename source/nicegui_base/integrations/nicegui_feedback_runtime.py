from __future__ import annotations

import json
from typing import Any


def show_company_toast(
    ui: Any,
    message: str,
    *,
    intent: str = 'info',
    duration_ms: int = 3500,
    dismissible: bool = True,
) -> Any:
    """Render Company-owned toast feedback with explicit lifetime and dismissal.

    The lifetime indicator is driven by the Web Animations API so hover can pause
    both the visible gauge and removal without a second unsynchronised timer.
    """
    safe_intent = intent if intent in {'info', 'success', 'warning', 'danger', 'neutral'} else 'info'
    duration = 0 if int(duration_ms) == 0 else max(800, min(int(duration_ms), 30_000))
    script = f"""
(() => {{
  let stack = document.getElementById('cui-toast-stack');
  if (!stack) {{
    stack = document.createElement('div');
    stack.id = 'cui-toast-stack'; stack.className = 'cui-toast-stack';
    stack.setAttribute('aria-live', 'polite'); stack.setAttribute('aria-relevant', 'additions removals');
    document.body.appendChild(stack);
  }}
  const toast = document.createElement('div');
  toast.className = 'cui-toast cui-toast--{safe_intent}';
  toast.setAttribute('role', {json.dumps('alert' if safe_intent in {'danger', 'warning'} else 'status')});
  const body = document.createElement('div'); body.className = 'cui-toast__body';
  const dot = document.createElement('span'); dot.className = 'cui-toast__dot'; dot.setAttribute('aria-hidden','true');
  const copy = document.createElement('span'); copy.className = 'cui-toast__message'; copy.textContent = {json.dumps(str(message))};
  body.append(dot, copy);
  let close = null;
  if ({str(bool(dismissible)).lower()}) {{
    close = document.createElement('button'); close.type = 'button'; close.className = 'cui-toast__close';
    close.setAttribute('aria-label', 'Dismiss notification'); close.innerHTML = '<span aria-hidden="true">×</span>';
    body.appendChild(close);
  }}
  toast.appendChild(body);
  let animation = null;
  if ({duration} > 0) {{
    const track = document.createElement('div'); track.className = 'cui-toast__lifetime'; track.setAttribute('aria-hidden','true');
    const bar = document.createElement('span'); bar.className = 'cui-toast__lifetime-bar'; track.appendChild(bar); toast.appendChild(track);
    animation = bar.animate([{{transform:'scaleX(1)'}},{{transform:'scaleX(0)'}}],{{duration:{duration},easing:'linear',fill:'forwards'}});
  }}
  stack.appendChild(toast);
  let removed = false;
  const remove = () => {{
    if (removed) return; removed = true; animation?.cancel();
    toast.classList.add('is-leaving'); setTimeout(() => toast.remove(), 150);
  }};
  if (animation) animation.onfinish = remove;
  close?.addEventListener('click', (event) => {{ event.stopPropagation(); remove(); }});
  toast.addEventListener('mouseenter', () => animation?.pause());
  toast.addEventListener('mouseleave', () => animation?.play());
  return true;
}})()
"""
    return ui.run_javascript(script)


__all__ = ['show_company_toast']

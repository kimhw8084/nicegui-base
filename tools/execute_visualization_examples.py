"""Execute every promoted visualization example in a bounded UI context.

This is deliberately a reference/evidence tool, not a second renderer.  The
fake UI only supplies the lifecycle surface required to construct NiceGUI Base
components; all public model validation and option construction remains real.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import types
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class _Element:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args=args; self.kwargs=kwargs; self.options={}; self.id=1; self.value=False
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def classes(self, *args, **kwargs): return self
    def props(self, *args, **kwargs): return self
    def on(self, *args, **kwargs): return self
    def on_point_click(self, *args, **kwargs): return self
    def update(self): return None
    async def run_chart_method(self, *args, **kwargs): return {'dataZoom': []}
    def set_text(self, *args, **kwargs): return self
    def open(self): return self
    def close(self): return self


class _Client:
    def on_delete(self, callback): return None


class _UI:
    context=types.SimpleNamespace(client=_Client())
    download=types.SimpleNamespace(content=lambda content, filename: (content, filename))
    fullscreen=types.SimpleNamespace(enter=lambda: None, exit=lambda: None, toggle=lambda: None)
    def element(self, *args, **kwargs): return _Element(*args, **kwargs)
    def html(self, *args, **kwargs): return _Element(*args, **kwargs)
    def echart(self, *args, **kwargs):
        item=_Element(*args, **kwargs)
        if args and isinstance(args[0], dict): item.options=dict(args[0])
        return item
    def plotly(self, *args, **kwargs): return _Element(*args, **kwargs)
    def button(self, *args, **kwargs): return _Element(*args, **kwargs)
    def menu(self, *args, **kwargs): return _Element(*args, **kwargs)
    def dialog(self, *args, **kwargs): return _Element(*args, **kwargs)
    def row(self, *args, **kwargs): return _Element(*args, **kwargs)
    def column(self, *args, **kwargs): return _Element(*args, **kwargs)
    def label(self, *args, **kwargs): return _Element(*args, **kwargs)
    def run_javascript(self, *args, **kwargs): return None
    def dark_mode(self, *args, **kwargs): return types.SimpleNamespace(value=False)


@contextmanager
def _fake_nicegui():
    previous=sys.modules.get('nicegui')
    module=types.ModuleType('nicegui'); module.ui=_UI()
    sys.modules['nicegui']=module
    try: yield
    finally:
        if previous is None: sys.modules.pop('nicegui',None)
        else: sys.modules['nicegui']=previous


def execute() -> dict[str, Any]:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
    from nicegui_base.workbench.catalog import analytics_entries
    from nicegui_base.workbench.public_examples import production_example_code
    results=[]
    with _fake_nicegui():
        for entry in analytics_entries():
            code=production_example_code(entry)
            record={'key': entry.key, 'ok': False}
            try:
                compile(code, f'<example:{entry.key}>', 'exec')
                if 'nicegui_base.integrations.nicegui_visualization' in code:
                    raise AssertionError('example imports visualization integration internals')
                namespace={'__name__': f'__example_{entry.key}__'}
                exec(code, namespace, namespace)
                record['ok']=True
            except Exception as exc:
                record.update(error=f'{type(exc).__name__}: {exc}')
            results.append(record)
    return {'count':len(results), 'passed':sum(item['ok'] for item in results), 'failed':[item for item in results if not item['ok']], 'results':results}


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument('--json', type=Path)
    args=parser.parse_args(); result=execute()
    payload=json.dumps(result, indent=2, sort_keys=True)
    if args.json: args.json.write_text(payload+'\n', encoding='utf-8')
    print(payload)
    return 0 if not result['failed'] else 1


if __name__ == '__main__': raise SystemExit(main())

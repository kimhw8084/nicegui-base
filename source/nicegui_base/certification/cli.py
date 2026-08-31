from __future__ import annotations
import argparse, json
from pathlib import Path
from .engine import run_certification

def main()->int:
    p=argparse.ArgumentParser(description='Run NiceGUI Base release-candidate certification')
    p.add_argument('root',nargs='?',default='.')
    p.add_argument('--require-nicegui',action='store_true')
    p.add_argument('--format',choices=('text','json'),default='text')
    a=p.parse_args(); r=run_certification(Path(a.root),require_nicegui=a.require_nicegui)
    if a.format=='json':
        print(json.dumps({'version':r.framework_version,'passed':r.passed,'summary':r.summary,'checks':[{'key':c.key,'label':c.label,'status':c.status.value,'detail':c.detail,'category':c.category,'required':c.required} for c in r.checks]},indent=2))
    else:
        for c in r.checks: print(f'[{c.status.value.upper():7}] {c.label}: {c.detail}')
        print('PASS' if r.passed else 'FAIL',r.summary)
    return 0 if r.passed else 1
if __name__=='__main__': raise SystemExit(main())

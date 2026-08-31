from __future__ import annotations

import argparse,hashlib,json,os,signal,subprocess,sys,time
from dataclasses import asdict,dataclass
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import urlopen

from nicegui_base.security.redaction import redact
from nicegui_base.version import FRAMEWORK_VERSION,NICEGUI_VERSION
from .live_checks import run_gold_certification
from .live_models import BrowserProbeConfig,LiveCertificationConfig,LoadProbeConfig
from .live_baseline import verify_visual_baseline
from .mac_browser import MacBrowserReport,run_mac_browser_matrix
from .mac_coverage import coverage_summary
from .live_lab import LAB_PORT
from .live_preflight import PreflightCheck,discover_browsers,run_preflight

@dataclass(frozen=True,slots=True)
class LiveCertificationReport:
    framework_version:str;nicegui_version:str;generated_at_utc:str;target_url:str;platform:str;exhaustive:bool;require_baseline:bool;baseline_verified:bool;baseline_detail:str
    preflight:tuple[PreflightCheck,...];live:dict[str,object];browser:dict[str,object];coverage:dict[str,object];lab_log:str
    @property
    def preflight_ok(self)->bool:return not any(c.required and c.status=='fail' for c in self.preflight)
    @property
    def live_ok(self)->bool:return bool(self.live.get('gold_eligible'))
    @property
    def browser_ok(self)->bool:
        if not bool(self.browser.get('passed')):return False
        if self.require_baseline:
            for item in self.browser.get('results',[]):
                visual=item.get('visual_diff') if isinstance(item,dict) else None
                if isinstance(visual,dict) and visual.get('status') in {'missing','unavailable','fail'}:return False
        return True
    @property
    def passed(self)->bool:
        return self.preflight_ok and self.live_ok and self.browser_ok and (self.baseline_verified if self.require_baseline else True) and not self.coverage.get('uncovered')
    def to_dict(self)->dict[str,object]:
        return {'framework_version':self.framework_version,'nicegui_version':self.nicegui_version,'generated_at_utc':self.generated_at_utc,'target_url':self.target_url,'platform':self.platform,'exhaustive':self.exhaustive,'require_baseline':self.require_baseline,'baseline_verified':self.baseline_verified,'baseline_detail':self.baseline_detail,'passed':self.passed,'preflight_ok':self.preflight_ok,'live_ok':self.live_ok,'browser_ok':self.browser_ok,'preflight':[asdict(c) for c in self.preflight],'live':self.live,'browser':self.browser,'coverage':self.coverage,'lab_log':self.lab_log}

def _sha256(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()

def _wait_ready(url:str,process:subprocess.Popen[bytes],timeout:float=40.0)->None:
    deadline=time.monotonic()+timeout;last='not started'
    while time.monotonic()<deadline:
        if process.poll() is not None:raise RuntimeError(f'Live lab exited before ready (exit={process.returncode})')
        try:
            with urlopen(url,timeout=1.5) as response:
                if 200<=response.status<300:return
                last=f'HTTP {response.status}'
        except Exception as exc:last=str(exc)
        time.sleep(.25)
    raise TimeoutError(f'Live lab did not become ready within {timeout:.0f}s: {last}')

def _stop(process:subprocess.Popen[bytes])->None:
    if process.poll() is not None:return
    try:process.send_signal(signal.SIGINT);process.wait(timeout=8)
    except Exception:
        process.terminate()
        try:process.wait(timeout=5)
        except Exception:process.kill()

def run_live_certification(*,output_dir:Path,baseline_dir:Path|None=None,root:Path|None=None,port:int=LAB_PORT,exhaustive:bool=False,include_edge:bool=True,require_edge:bool=False,require_baseline:bool=False,load_requests:int=120,load_concurrency:int=12)->LiveCertificationReport:
    import platform as platform_module
    output_dir=output_dir.resolve();output_dir.mkdir(parents=True,exist_ok=True)
    baseline_dir=baseline_dir.resolve() if baseline_dir is not None else None
    preflight=run_preflight(port=port,require_browser=True,require_edge=require_edge);required=[c for c in preflight if c.required and c.status=='fail']
    if required:
        report=LiveCertificationReport(FRAMEWORK_VERSION,NICEGUI_VERSION,datetime.now(timezone.utc).isoformat(),f'http://127.0.0.1:{port}',platform_module.system(),exhaustive,require_baseline,False,'not checked because preflight failed',tuple(preflight),{'gold_eligible':False,'summary':{'fail':len(required)},'checks':[]},MacBrowserReport((),{},str(baseline_dir) if baseline_dir else None).to_dict(),coverage_summary(),str(output_dir/'live_lab.log'))
        _write(report,output_dir);return report
    log_path=output_dir/'live_lab.log';env=os.environ.copy();env['NICEGUI_BASE_STORAGE_SECRET']=env.get('NICEGUI_BASE_STORAGE_SECRET','nicegui-base-live-certification-v1.6')
    command=[sys.executable,'-m','nicegui_base.certification.live_lab_cli','--host','127.0.0.1','--port',str(port)]
    with log_path.open('wb') as log:process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=env,cwd=str(output_dir))
    target=f'http://127.0.0.1:{port}'
    try:
        _wait_ready(target+'/healthz',process)
        live_config=LiveCertificationConfig(target_url=target,health_path='/healthz',readiness_path='/readyz',websocket_path='/_nicegui_ws/socket.io/?EIO=4&transport=websocket',require_security_headers=True,browser=BrowserProbeConfig(enabled=False,required=False),load=LoadProbeConfig(url=target,requests=max(20,min(load_requests,500)),concurrency=max(1,min(load_concurrency,32)),min_success_rate=.99,timeout_seconds=10.0),require_nicegui_runtime=True)
        live_report=run_gold_certification(live_config,root=root or Path.cwd())
        found=discover_browsers();executables={k:v.executable for k,v in found.items()};use_edge=include_edge and 'msedge' in executables
        browser_report=run_mac_browser_matrix(target,output_dir=output_dir,baseline_dir=baseline_dir,exhaustive=exhaustive,include_edge=use_edge,browser_executables=executables,report_name='LIVE_BROWSER_REPORT.json')
    finally:_stop(process)
    baseline_verified,baseline_detail=(verify_visual_baseline(baseline_dir) if baseline_dir is not None else (False,'no approved baseline configured; inspect screenshots and approve only after human review'))
    report=LiveCertificationReport(FRAMEWORK_VERSION,NICEGUI_VERSION,datetime.now(timezone.utc).isoformat(),target,platform_module.system(),exhaustive,require_baseline,baseline_verified,baseline_detail,tuple(preflight),live_report.to_dict(),browser_report.to_dict(),coverage_summary(),str(log_path));_write(report,output_dir);return report

def _write(report:LiveCertificationReport,output_dir:Path)->Path:
    path=output_dir/'LIVE_CERTIFICATION_REPORT.json';path.write_text(json.dumps(redact(report.to_dict()),indent=2,sort_keys=True)+'\n');path.with_suffix(path.suffix+'.sha256').write_text(f'{_sha256(path)}  {path.name}\n');return path

def main()->int:
    p=argparse.ArgumentParser(description='Run complete platform-neutral NiceGUI Base live certification')
    p.add_argument('--output',type=Path,default=Path('certification_output'));p.add_argument('--baseline',type=Path,default=Path('visual_baseline'));p.add_argument('--root',type=Path,default=Path.cwd());p.add_argument('--port',type=int,default=LAB_PORT);p.add_argument('--exhaustive',action='store_true');p.add_argument('--no-edge',action='store_true');p.add_argument('--require-edge',action='store_true');p.add_argument('--require-baseline',action='store_true');p.add_argument('--load-requests',type=int,default=120);p.add_argument('--load-concurrency',type=int,default=12);p.add_argument('--format',choices=('text','json'),default='text');a=p.parse_args()
    baseline=a.baseline if (a.baseline/'BASELINE_MANIFEST.json').exists() else None
    report=run_live_certification(output_dir=a.output,baseline_dir=baseline,root=a.root,port=a.port,exhaustive=a.exhaustive,include_edge=not a.no_edge,require_edge=a.require_edge,require_baseline=a.require_baseline,load_requests=a.load_requests,load_concurrency=a.load_concurrency)
    if a.format=='json':print(json.dumps(report.to_dict(),indent=2,sort_keys=True))
    else:
        print(f'NiceGUI Base {FRAMEWORK_VERSION} live certification · {report.platform}');print(f'Preflight: {"PASS" if report.preflight_ok else "FAIL"}');print(f'Runtime/WebSocket/load: {"PASS" if report.live_ok else "FAIL"}');print(f'Browser + geometry: {"PASS" if report.browser_ok else "FAIL"} {report.browser.get("summary",{})}');print(f'Visual baseline: {"VERIFIED" if report.baseline_verified else "PENDING"} — {report.baseline_detail}');print(f'\nLIVE CERTIFICATION: {"PASS" if report.passed else "FAIL"}');print(f'Evidence: {a.output/"LIVE_CERTIFICATION_REPORT.json"}')
    return 0 if report.passed else 1

if __name__=='__main__':raise SystemExit(main())
__all__=['LiveCertificationReport','run_live_certification']

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

from nicegui_base.certification.live_lab import ROUTES
from nicegui_base.certification.nicegui_runtime_contract import run_installed_runtime_contract
from nicegui_base.version import FRAMEWORK_VERSION


ERROR_PATTERNS = (
    'Traceback (most recent call last):',
    'AttributeError:',
    'TypeError:',
    'RuntimeError:',
    'ImportError:',
    'ModuleNotFoundError:',
    'Exception in ASGI application',
)


@dataclass(frozen=True, slots=True)
class RouteSmokeResult:
    path: str
    status: int | None
    ok: bool
    detail: str = ''


@dataclass(frozen=True, slots=True)
class RuntimeSmokeReport:
    ok: bool
    port: int
    routes: tuple[RouteSmokeResult, ...]
    log_path: str
    log_error_patterns: tuple[str, ...]
    process_returncode: int | None


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def _request(url: str, *, timeout: float = 5.0) -> tuple[int | None, str]:
    req = urllib.request.Request(url, headers={'User-Agent': f'nicegui-base-runtime-smoke/{FRAMEWORK_VERSION}'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return int(response.status), ''
    except urllib.error.HTTPError as exc:
        return int(exc.code), f'HTTPError: {exc}'
    except Exception as exc:
        return None, f'{type(exc).__name__}: {exc}'


def _wait_ready(base_url: str, process: subprocess.Popen, *, timeout: float = 30.0) -> tuple[bool, str]:
    deadline = time.monotonic() + timeout
    last = ''
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False, f'lab process exited early with code {process.returncode}'
        status, detail = _request(base_url + '/healthz', timeout=.8)
        if status is not None and 200 <= status < 400:
            return True, ''
        last = detail or f'health status={status}'
        time.sleep(.15)
    return False, last or 'health endpoint did not become ready'


def _stop_process(process: subprocess.Popen) -> int | None:
    """Stop the smoke server without synthesizing a user KeyboardInterrupt.

    SIGINT is intentionally avoided: asyncio.Runner translates it through task
    cancellation and can emit CancelledError/KeyboardInterrupt tracebacks during
    an otherwise successful certification run. Uvicorn handles SIGTERM as its
    normal graceful server-shutdown signal on the supported macOS/Linux targets.
    """
    if process.poll() is not None:
        return process.returncode
    try:
        process.terminate()
        process.wait(timeout=8)
    except Exception:
        try:
            process.kill()
            process.wait(timeout=3)
        except Exception:
            pass
    return process.poll()


def run_runtime_smoke(*, output_dir: Path | str | None = None, port: int | None = None,
                      python_executable: str | None = None) -> RuntimeSmokeReport:
    contract = run_installed_runtime_contract()
    if not contract.ok:
        details = [i.detail for i in (*contract.source_issues, *contract.runtime_issues)]
        route = RouteSmokeResult('/runtime-contract', None, False, '; '.join(details) or 'runtime contract failed')
        return RuntimeSmokeReport(False, port or 0, (route,), '', (), None)

    output = Path(output_dir) if output_dir is not None else Path.cwd() / 'certification_output' / 'runtime_smoke'
    output.mkdir(parents=True, exist_ok=True)
    port = port or _free_port()
    log_path = output / 'RUNTIME_SMOKE_SERVER.log'
    report_path = output / 'RUNTIME_SMOKE_REPORT.json'
    python_executable = python_executable or sys.executable
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    base_url = f'http://127.0.0.1:{port}'

    routes: list[RouteSmokeResult] = []
    process: subprocess.Popen | None = None
    returncode: int | None = None
    with tempfile.TemporaryDirectory(prefix='nicegui-base-runtime-smoke-') as neutral_cwd:
        with log_path.open('w', encoding='utf-8') as log:
            process = subprocess.Popen(
                [python_executable, '-m', 'nicegui_base.certification.live_lab_cli', '--host', '127.0.0.1', '--port', str(port)],
                cwd=neutral_cwd,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
            )
            ready, ready_detail = _wait_ready(base_url, process)
            if not ready:
                routes.append(RouteSmokeResult('/healthz', None, False, ready_detail))
            else:
                # Operational endpoints first, then every live route. Initial HTML requests execute NiceGUI page builders.
                for path in ('/healthz', '/readyz', *(route.path for route in ROUTES)):
                    status, detail = _request(base_url + path, timeout=8.0)
                    ok = status is not None and 200 <= status < 400
                    routes.append(RouteSmokeResult(path, status, ok, detail))
                    if process.poll() is not None:
                        routes.append(RouteSmokeResult('/process', None, False, f'lab process exited with {process.returncode}'))
                        break
                # Give server-side logging a short chance to flush callback/page-construction errors.
                time.sleep(.25)
            returncode = _stop_process(process)

    log_text = log_path.read_text(encoding='utf-8', errors='replace') if log_path.exists() else ''
    matched = tuple(pattern for pattern in ERROR_PATTERNS if pattern in log_text)
    ok = bool(routes) and all(r.ok for r in routes) and not matched
    report = RuntimeSmokeReport(ok, port, tuple(routes), str(log_path), matched, returncode)
    report_path.write_text(json.dumps({
        'ok': report.ok,
        'port': report.port,
        'route_count': len(report.routes),
        'routes': [asdict(r) for r in report.routes],
        'log_path': report.log_path,
        'log_error_patterns': list(report.log_error_patterns),
        'process_returncode': report.process_returncode,
    }, indent=2), encoding='utf-8')
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description='Start the real installed NiceGUI lab and browserlessly smoke every route')
    parser.add_argument('--output', type=Path, default=Path('certification_output/runtime_smoke'))
    parser.add_argument('--port', type=int, default=0, help='0 chooses an available localhost port')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args()
    report = run_runtime_smoke(output_dir=args.output, port=args.port or None)
    if args.format == 'json':
        print(json.dumps({
            'ok': report.ok,
            'port': report.port,
            'routes': [asdict(r) for r in report.routes],
            'log_path': report.log_path,
            'log_error_patterns': list(report.log_error_patterns),
            'process_returncode': report.process_returncode,
        }, indent=2))
    else:
        for result in report.routes:
            status = result.status if result.status is not None else '-'
            print(f'[{"PASS" if result.ok else "FAIL"}] {status!s:>3} {result.path} {result.detail}')
        if report.log_error_patterns:
            print('Server error markers: ' + ', '.join(report.log_error_patterns))
        print(f'Log: {report.log_path}')
        print(f'\nRuntime smoke: {"PASS" if report.ok else "FAIL"}')
    return 0 if report.ok else 1


if __name__ == '__main__':
    raise SystemExit(main())


__all__ = ['RouteSmokeResult', 'RuntimeSmokeReport', 'ERROR_PATTERNS', 'run_runtime_smoke']

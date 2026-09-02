from __future__ import annotations

import io
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from .generated_smoke import smoke_generated_zip


@dataclass(frozen=True, slots=True)
class RouteProof:
    route: str
    status: int | None
    elapsed_ms: int
    ok: bool
    detail: str = ''

    def to_dict(self) -> dict[str, object]:
        return {
            'route': self.route,
            'status': self.status,
            'elapsed_ms': self.elapsed_ms,
            'ok': self.ok,
            'detail': self.detail,
        }


@dataclass(frozen=True, slots=True)
class LiveSmokeReport:
    ok: bool
    findings: tuple[str, ...]
    routes: tuple[RouteProof, ...]
    elapsed_ms: int
    process_returncode: int | None
    stdout_tail: str = ''
    stderr_tail: str = ''

    def to_dict(self) -> dict[str, object]:
        return {
            'ok': self.ok,
            'findings': list(self.findings),
            'routes': [item.to_dict() for item in self.routes],
            'elapsed_ms': self.elapsed_ms,
            'process_returncode': self.process_returncode,
            'stdout_tail': self.stdout_tail,
            'stderr_tail': self.stderr_tail,
        }


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def _tail(text: str, limit: int = 4000) -> str:
    value = str(text or '')
    return value if len(value) <= limit else value[-limit:]


def _read_log(file_obj) -> str:
    try:
        file_obj.flush()
        file_obj.seek(0)
        return _tail(file_obj.read())
    except Exception:
        return ''


def _request(url: str, timeout: float) -> tuple[int | None, str]:
    request = urllib.request.Request(url, headers={'User-Agent': 'nicegui-base-runtime-proof/1'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=max(.2, timeout)) as response:
            status = int(getattr(response, 'status', 200) or 200)
            # Consume a bounded portion so route-render failures surface while large pages remain cheap.
            body = response.read(128 * 1024).decode('utf-8', errors='replace')
            if 'Traceback (most recent call last)' in body:
                return status, 'traceback rendered in response body'
            return status, ''
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(16 * 1024).decode('utf-8', errors='replace')
        except Exception:
            body = ''
        return int(exc.code), _tail(body, 800) or str(exc.reason)
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
        return None, f'{type(exc).__name__}: {exc}'


def _run_http_process(
    *,
    command: Sequence[str],
    cwd: Path,
    port: int,
    routes: Sequence[str],
    env: Mapping[str, str],
    timeout_seconds: float,
) -> LiveSmokeReport:
    if timeout_seconds <= 0:
        raise ValueError('timeout_seconds must be positive')
    started = time.monotonic()
    findings: list[str] = []
    proofs: list[RouteProof] = []
    stdout_file = tempfile.TemporaryFile(mode='w+t', encoding='utf-8')
    stderr_file = tempfile.TemporaryFile(mode='w+t', encoding='utf-8')
    kwargs = {
        'cwd': str(cwd),
        'env': dict(env),
        'stdout': stdout_file,
        'stderr': stderr_file,
        'text': True,
    }
    if os.name != 'nt':
        kwargs['start_new_session'] = True
    try:
        process = subprocess.Popen(list(command), **kwargs)
    except OSError as exc:
        stdout_file.close(); stderr_file.close()
        return LiveSmokeReport(False, (f'process_start:{type(exc).__name__}:{exc}',), (), int((time.monotonic() - started) * 1000), None)
    try:
        deadline = started + timeout_seconds
        base = f'http://127.0.0.1:{port}'
        # First route doubles as readiness. Retry connection failures until the server starts.
        first = routes[0] if routes else '/'
        first_status: int | None = None
        first_detail = ''
        first_started = time.monotonic()
        while time.monotonic() < deadline:
            if process.poll() is not None:
                break
            status, detail = _request(base + first, min(.8, max(.2, deadline - time.monotonic())))
            if status is not None:
                first_status, first_detail = status, detail
                break
            time.sleep(.12)
        first_elapsed = int((time.monotonic() - first_started) * 1000)
        if first_status is None:
            if process.poll() is not None:
                findings.append(f'process_exited_before_ready:{process.returncode}')
            else:
                findings.append(f'server_not_ready_within:{timeout_seconds:.1f}s')
            proofs.append(RouteProof(first, None, first_elapsed, False, first_detail or 'server did not become reachable'))
        else:
            first_ok = 200 <= first_status < 400 and not first_detail
            proofs.append(RouteProof(first, first_status, first_elapsed, first_ok, first_detail))
            if not first_ok:
                findings.append(f'route:{first}:status={first_status}:{first_detail or "unexpected response"}')

        if proofs and proofs[0].ok:
            for route in routes[1:]:
                route_started = time.monotonic()
                remaining = deadline - route_started
                if remaining <= 0:
                    proofs.append(RouteProof(route, None, 0, False, 'overall smoke timeout exceeded'))
                    findings.append(f'route:{route}:timeout')
                    continue
                status, detail = _request(base + route, min(2.0, max(.2, remaining)))
                elapsed = int((time.monotonic() - route_started) * 1000)
                ok = status is not None and 200 <= status < 400 and not detail
                proofs.append(RouteProof(route, status, elapsed, ok, detail))
                if not ok:
                    findings.append(f'route:{route}:status={status}:{detail or "unreachable"}')
        returncode = process.poll()
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        returncode = process.returncode
        stdout_tail = _read_log(stdout_file)
        stderr_tail = _read_log(stderr_file)
        stdout_file.close()
        stderr_file.close()

    elapsed_ms = int((time.monotonic() - started) * 1000)
    if returncode not in (None, 0, -15, 143):
        # A process killed after a successful probe is expected to report a signal code on POSIX.
        findings.append(f'process_returncode:{returncode}')
    if findings and stderr_tail:
        marker = stderr_tail.casefold()
        if 'traceback' in marker or 'error' in marker or 'exception' in marker:
            findings.append('server_stderr_contains_error')
    findings = list(dict.fromkeys(findings))
    return LiveSmokeReport(not findings and bool(proofs) and all(item.ok for item in proofs), tuple(findings), tuple(proofs), elapsed_ms, returncode, stdout_tail, stderr_tail)


def _python_env(*, pythonpath: str | Path | None = None, extra_env: Mapping[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env.setdefault('NICEGUI_BASE_STORAGE_SECRET', 'nicegui-base-runtime-proof')
    if pythonpath is not None:
        current = env.get('PYTHONPATH', '')
        prefix = str(Path(pythonpath).resolve())
        env['PYTHONPATH'] = prefix if not current else prefix + os.pathsep + current
    if extra_env:
        env.update({str(key): str(value) for key, value in extra_env.items()})
    return env


def run_generated_live_smoke(
    payload: bytes,
    *,
    python_executable: str | Path | None = None,
    pythonpath: str | Path | None = None,
    timeout_seconds: float = 15.0,
) -> LiveSmokeReport:
    static = smoke_generated_zip(payload)
    if not static.ok:
        return LiveSmokeReport(False, tuple(f'static:{item}' for item in static.findings), (), 0, None)
    python = str(python_executable or sys.executable)
    with tempfile.TemporaryDirectory(prefix='nicegui-base-live-generated-') as temp:
        root = Path(temp).resolve()
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            for info in archive.infolist():
                destination = (root / info.filename).resolve()
                try:
                    destination.relative_to(root)
                except ValueError as exc:
                    return LiveSmokeReport(False, (f'zip_path_escape:{info.filename}',), (), 0, None)
            archive.extractall(root)
        port = _free_port()
        env = _python_env(pythonpath=pythonpath, extra_env={
            'NICEGUI_BASE_HOST': '127.0.0.1',
            'NICEGUI_BASE_PORT': str(port),
        })
        return _run_http_process(
            command=(python, 'app.py'), cwd=root, port=port, routes=('/',), env=env,
            timeout_seconds=timeout_seconds,
        )


def run_workbench_live_smoke(
    *,
    python_executable: str | Path | None = None,
    pythonpath: str | Path | None = None,
    routes: Sequence[str] = ('/', '/build', '/layouts', '/quality'),
    timeout_seconds: float = 20.0,
) -> LiveSmokeReport:
    python = str(python_executable or sys.executable)
    port = _free_port()
    env = _python_env(pythonpath=pythonpath)
    source = (
        'from nicegui_base.workbench.app import run_workbench; '
        f"run_workbench(host='127.0.0.1', port={port}, show=False)"
    )
    return _run_http_process(
        command=(python, '-c', source), cwd=Path.cwd(), port=port,
        routes=tuple(routes) or ('/',), env=env, timeout_seconds=timeout_seconds,
    )


__all__ = ['LiveSmokeReport', 'RouteProof', 'run_generated_live_smoke', 'run_workbench_live_smoke']

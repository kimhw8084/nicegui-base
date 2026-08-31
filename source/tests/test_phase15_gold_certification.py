from __future__ import annotations

import base64
import hashlib
import json
import socketserver
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from nicegui_base.certification.live_checks import probe_auth, probe_health, probe_http, probe_load, probe_websocket, write_evidence
from nicegui_base.certification.live_models import AuthProbeConfig, GoldCertificationReport, LiveCertificationConfig, LiveGateResult, LiveGateStatus, LoadProbeConfig


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.endswith('/protected') and not self.headers.get('Authorization'):
            self.send_response(403); self.end_headers(); return
        if self.path.endswith('/healthz'):
            body=b'{"status":"ok"}'
        elif self.path.endswith('/readyz'):
            body=b'{"status":"ready"}'
        else:
            body=b'<html><main>ok</main></html>'
        self.send_response(200)
        self.send_header('Content-Type','text/html')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','same-origin')
        self.end_headers(); self.wfile.write(body)
    def log_message(self, format, *args):
        pass


class WsHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data=b''
        while b'\r\n\r\n' not in data:
            chunk=self.request.recv(4096)
            if not chunk: return
            data+=chunk
        text=data.decode('latin1')
        key=''
        for line in text.split('\r\n'):
            if line.lower().startswith('sec-websocket-key:'):
                key=line.split(':',1)[1].strip(); break
        accept=base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
        self.request.sendall((
            'HTTP/1.1 101 Switching Protocols\r\n'
            'Upgrade: websocket\r\nConnection: Upgrade\r\n'
            f'Sec-WebSocket-Accept: {accept}\r\n\r\n'
        ).encode())


def _http_server():
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    return server


def test_http_health_and_load_probes():
    server=_http_server()
    try:
        url=f'http://127.0.0.1:{server.server_port}/nicegui-base'
        cfg=LiveCertificationConfig(url, require_nicegui_runtime=False)
        http=probe_http(cfg)
        assert all(r.status is LiveGateStatus.PASS for r in http)
        health=probe_health(cfg)
        assert all(r.status is LiveGateStatus.PASS for r in health)
        load=probe_load(LoadProbeConfig(url=url,requests=12,concurrency=4,min_success_rate=1.0),{})
        assert load.status is LiveGateStatus.PASS
        assert load.evidence['success_rate']==1.0
    finally:
        server.shutdown(); server.server_close()



def test_auth_probe_verifies_fail_closed_and_authenticated_access():
    server=_http_server()
    try:
        url=f'http://127.0.0.1:{server.server_port}/nicegui-base'
        cfg=LiveCertificationConfig(url, headers={'Authorization':'Bearer ephemeral'}, auth=AuthProbeConfig('/protected'), require_nicegui_runtime=False)
        results=probe_auth(cfg)
        assert [r.status for r in results]==[LiveGateStatus.PASS,LiveGateStatus.PASS]
    finally:
        server.shutdown(); server.server_close()


def test_websocket_upgrade_probe_verifies_accept_header():
    server=socketserver.TCPServer(('127.0.0.1',0),WsHandler)
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    try:
        cfg=LiveCertificationConfig(f'http://127.0.0.1:{server.server_address[1]}', require_nicegui_runtime=False)
        result=probe_websocket(cfg)
        assert result.status is LiveGateStatus.PASS
        assert '101' in result.detail
    finally:
        server.shutdown(); server.server_close()


def test_gold_eligibility_requires_no_required_fail_or_skip():
    good=LiveGateResult('a','A',LiveGateStatus.PASS,'ok','x')
    optional_skip=LiveGateResult('b','B',LiveGateStatus.SKIP,'optional','x',required=False)
    assert GoldCertificationReport('1.4.0','http://example',(good,optional_skip)).gold_eligible
    required_skip=LiveGateResult('c','C',LiveGateStatus.SKIP,'missing','x',required=True)
    assert not GoldCertificationReport('1.4.0','http://example',(good,required_skip)).gold_eligible


def test_evidence_is_hashed_and_secrets_are_redacted(tmp_path: Path):
    check=LiveGateResult('auth','Auth',LiveGateStatus.PASS,'ok','security',evidence={'authorization':'Bearer secret-token'})
    report=GoldCertificationReport('1.4.0','http://example',(check,),metadata={'token':'secret'})
    path=write_evidence(report,tmp_path/'evidence.json')
    data=json.loads(path.read_text())
    assert data['checks'][0]['evidence']['authorization']=='[REDACTED]'
    assert data['metadata']['token']=='[REDACTED]'
    assert path.with_suffix('.json.sha256').exists()

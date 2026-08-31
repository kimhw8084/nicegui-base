import asyncio
import pytest

from nicegui_base.security import (
    AccessPolicy, AuthorizationModel, HeaderAuthenticationAdapter, HeaderIdentityConfig, IdentityMiddleware,
    Principal, RoleDefinition, SecurityHeaders, SecurityHeadersMiddleware, TrustedProxyPolicy, UploadPolicy,
    redact, redact_text, safe_filename,
)


def test_principal_and_policy_validation():
    p=Principal('u1', roles=frozenset({'engineer'}), permissions=frozenset({'tool.read'}))
    assert p.has_role('engineer') and p.has_permission('tool.read')
    assert not Principal.anonymous().authenticated
    with pytest.raises(ValueError): Principal(' ', authenticated=True)


def test_authorization_expands_role_permissions():
    model=AuthorizationModel({'engineer': RoleDefinition('engineer', frozenset({'tool.read','analysis.run'}))})
    p=Principal('u1', roles=frozenset({'engineer'}))
    assert model.check(p, AccessPolicy(required_permissions=frozenset({'analysis.run'}))).allowed
    denied=model.check(p, AccessPolicy(required_permissions=frozenset({'admin.delete'})))
    assert not denied.allowed and denied.missing_permissions==('admin.delete',)


def test_any_permission_and_role_rules():
    model=AuthorizationModel()
    p=Principal('u', roles=frozenset({'reviewer'}), permissions=frozenset({'a'}))
    assert model.check(p, AccessPolicy(any_permissions=frozenset({'a','b'}))).allowed
    assert not model.check(p, AccessPolicy(any_roles=frozenset({'admin','owner'}))).allowed


def test_anonymous_policy_is_explicit():
    model=AuthorizationModel(); anon=Principal.anonymous()
    assert not model.check(anon, AccessPolicy()).allowed
    assert model.check(anon, AccessPolicy(allow_anonymous=True)).allowed


def test_trusted_proxy_policy_supports_cidrs():
    policy=TrustedProxyPolicy(('10.0.0.0/8','127.0.0.1/32'))
    assert policy.contains('10.2.3.4') and policy.contains('127.0.0.1')
    assert not policy.contains('192.168.1.2') and not policy.contains('bad')


@pytest.mark.asyncio
async def test_header_auth_rejects_spoofed_untrusted_identity():
    adapter=HeaderAuthenticationAdapter(trusted_proxies=TrustedProxyPolicy(('10.0.0.0/8',)))
    headers={'x-auth-user':'alice','x-auth-roles':'engineer, reviewer','x-auth-permissions':'tool.read'}
    assert not (await adapter.authenticate(headers,'192.168.1.2')).authenticated
    p=await adapter.authenticate(headers,'10.1.2.3')
    assert p.subject=='alice' and p.roles==frozenset({'engineer','reviewer'}) and 'tool.read' in p.permissions


@pytest.mark.asyncio
async def test_header_auth_can_be_explicitly_non_proxy_for_custom_env():
    cfg=HeaderIdentityConfig(require_trusted_proxy=False)
    p=await HeaderAuthenticationAdapter(cfg).authenticate({'X-Auth-User':'bob'},None)
    assert p.subject=='bob'


def test_redaction_is_recursive_and_catches_authorization_text():
    value={'password':'pw','nested':{'api_key':'abc','text':'Bearer abc.def.ghi'},'ok':42}
    redacted=redact(value)
    assert redacted['password']=='[REDACTED]' and redacted['nested']['api_key']=='[REDACTED]'
    assert 'abc.def.ghi' not in redacted['nested']['text'] and redacted['ok']==42
    assert 'supersecret' not in redact_text('token=supersecret')


def test_safe_filename_removes_paths_and_unsafe_characters():
    assert safe_filename('../../my report?.csv')=='my report_.csv'
    assert safe_filename(r'C:\\temp\\x.csv')=='x.csv'
    with pytest.raises(ValueError): safe_filename('..')


def test_upload_policy_blocks_active_and_oversized_content():
    p=UploadPolicy(max_bytes=100)
    assert p.validate('data.csv',50,'text/csv')=='data.csv'
    with pytest.raises(ValueError): p.validate('x.html',10,'text/html')
    with pytest.raises(ValueError): p.validate('data.csv',101,'text/csv')
    with pytest.raises(ValueError): p.validate('data.csv',10,'application/x-bad')


@pytest.mark.asyncio
async def test_security_headers_middleware_adds_without_overwriting_existing():
    sent=[]
    async def app(scope, receive, send):
        await send({'type':'http.response.start','status':200,'headers':[(b'x-frame-options',b'SAMEORIGIN')]})
        await send({'type':'http.response.body','body':b''})
    mw=SecurityHeadersMiddleware(app, SecurityHeaders())
    async def receive(): return {'type':'http.request'}
    async def send(msg): sent.append(msg)
    await mw({'type':'http'}, receive, send)
    headers=dict(sent[0]['headers'])
    assert headers[b'x-frame-options']==b'SAMEORIGIN'
    assert headers[b'x-content-type-options']==b'nosniff'


@pytest.mark.asyncio
async def test_identity_middleware_attaches_principal_to_scope_state():
    adapter=HeaderAuthenticationAdapter(HeaderIdentityConfig(require_trusted_proxy=False))
    captured={}
    async def app(scope, receive, send): captured.update(scope['state'])
    scope={'type':'http','headers':[(b'x-auth-user',b'alice')],'client':('127.0.0.1',1234)}
    await IdentityMiddleware(app, adapter)(scope, lambda: None, lambda m: None)
    assert captured['nicegui_base_principal'].subject=='alice'


@pytest.mark.asyncio
async def test_header_auth_accepts_proxy_assertion_when_forwarded_client_is_rewritten():
    adapter=HeaderAuthenticationAdapter(
        trusted_proxies=TrustedProxyPolicy(('10.0.0.0/8',)), assertion_secret='gateway-secret'
    )
    headers={'x-auth-user':'alice','x-company-auth-assertion':'gateway-secret'}
    p=await adapter.authenticate(headers,'203.0.113.55')
    assert p.subject=='alice'
    spoof=await adapter.authenticate({'x-auth-user':'mallory','x-company-auth-assertion':'wrong'},'203.0.113.55')
    assert not spoof.authenticated

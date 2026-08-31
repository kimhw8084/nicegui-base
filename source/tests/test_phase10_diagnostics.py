import asyncio
import json
import logging
import pytest

from nicegui_base.diagnostics import (
    CorrelationIdMiddleware, HealthCheck, HealthRegistry, HealthResult, HealthState, JsonLogFormatter,
    get_correlation_id, set_correlation_id, reset_correlation_id, validate_incoming_correlation_id,
)


def test_correlation_id_validation():
    assert validate_incoming_correlation_id('abcDEF12-xyz')=='abcDEF12-xyz'
    assert validate_incoming_correlation_id('short') is None
    assert validate_incoming_correlation_id('<script>abcdefgh') is None


def test_correlation_context_roundtrip():
    token=set_correlation_id('abcdef12')
    try: assert get_correlation_id()=='abcdef12'
    finally: reset_correlation_id(token)


@pytest.mark.asyncio
async def test_correlation_middleware_generates_response_header_and_context():
    sent=[]; seen=[]
    async def app(scope, receive, send):
        seen.append(get_correlation_id()); await send({'type':'http.response.start','status':200,'headers':[]})
    async def send(msg): sent.append(msg)
    await CorrelationIdMiddleware(app)({'type':'http','headers':[]}, lambda: None, send)
    assert seen[0] and len(seen[0])==32
    assert dict(sent[0]['headers'])[b'x-correlation-id']==seen[0].encode()


def test_json_logging_redacts_secret_fields_and_bearer_tokens():
    formatter=JsonLogFormatter(); record=logging.LogRecord('x',logging.INFO,'',1,'Bearer abc.def.ghi',(),None)
    record.context={'password':'pw','safe':'ok'}
    data=json.loads(formatter.format(record))
    assert 'abc.def.ghi' not in data['message'] and data['context']['password']=='[REDACTED]' and data['context']['safe']=='ok'


@pytest.mark.asyncio
async def test_health_registry_aggregates_critical_and_noncritical():
    r=HealthRegistry()
    r.register(HealthCheck('db',lambda: True,critical=True))
    r.register(HealthCheck('cache',lambda: HealthResult('cache',HealthState.DEGRADED,'slow'),critical=False))
    report=await r.run()
    assert report.state is HealthState.DEGRADED and report.ready


@pytest.mark.asyncio
async def test_critical_health_failure_makes_not_ready():
    r=HealthRegistry(); r.register(HealthCheck('db',lambda: False,critical=True))
    report=await r.run(); assert report.state is HealthState.UNHEALTHY and not report.ready


@pytest.mark.asyncio
async def test_health_timeout_is_reported_not_raised():
    async def slow(): await asyncio.sleep(.05); return True
    r=HealthRegistry(); r.register(HealthCheck('slow',slow,timeout_seconds=.005))
    report=await r.run(); assert report.checks[0].state is HealthState.UNHEALTHY and report.checks[0].detail=='timeout'


def test_duplicate_health_check_rejected():
    r=HealthRegistry(); r.register(HealthCheck('x',lambda: True))
    with pytest.raises(ValueError): r.register(HealthCheck('x',lambda: True))

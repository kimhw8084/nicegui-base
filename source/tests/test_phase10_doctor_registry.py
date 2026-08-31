from nicegui_base.diagnostics import RuntimeDoctor
from nicegui_base.runtime import RUNTIME_REGISTRY, RuntimeConfig
from nicegui_base.security import SECURITY_REGISTRY


def test_security_and_runtime_registries_are_ai_discoverable():
    assert {'principal','header_auth','access_policy','security_headers','upload_policy','redaction','correlation_id'} <= set(SECURITY_REGISTRY)
    assert {'runtime_config','root_path','proxy_headers','health','runtime_doctor','compatibility_manifest'} <= set(RUNTIME_REGISTRY)


def test_runtime_doctor_reports_missing_nicegui_without_crashing(monkeypatch):
    import nicegui_base.diagnostics.doctor as module
    original=module.metadata.version
    def version(name):
        if name=='nicegui':
            raise module.metadata.PackageNotFoundError
        return original(name)
    monkeypatch.setattr(module.metadata,'version',version)
    report=RuntimeDoctor(RuntimeConfig('Tool')).run({'NICEGUI_BASE_STORAGE_SECRET':'x'})
    assert any(f.code=='NICEGUI_VERSION' and not f.ok for f in report.findings)
    assert any(f.code=='VISUAL_ASSETS' and f.ok for f in report.findings)


def test_runtime_doctor_multi_instance_reports_shared_storage_requirements(monkeypatch):
    import nicegui_base.diagnostics.doctor as module
    monkeypatch.setattr(module.metadata,'version',lambda name:'3.15.0' if name=='nicegui' else '0.90.0')
    cfg=RuntimeConfig('Tool',expected_replicas=2)
    report=RuntimeDoctor(cfg).run({'NICEGUI_BASE_STORAGE_SECRET':'x'})
    shared=next(f for f in report.findings if f.code=='SHARED_STORAGE')
    assert not shared.ok

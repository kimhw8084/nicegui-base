from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_ENGINEERING_KEYS = frozenset({
    'EngineeringEntityCard', 'EngineeringStatusBadge', 'SpecLimitIndicator',
    'OutOfSpecIndicator', 'BaselineComparison', 'ProcessTrendSpec',
    'DistributionComparisonSpec', 'PopulationComparisonPanel', 'CommonalityTable',
    'EvidenceCard', 'ConfidenceIndicator', 'RcaEvidencePanel', 'RcaWorkspaceSpec',
    'EngineeringTimeline',
})


class _FakeElement:
    def __init__(self, evidence, tag):
        self.evidence = evidence
        self.tag = tag

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def classes(self, value=''):
        return self

    def props(self, value=''):
        self.evidence['props'].append(value)
        return self


class _FakeUI:
    def __init__(self):
        self.evidence = {'labels': [], 'props': []}

    def element(self, tag):
        return _FakeElement(self.evidence, tag)

    def label(self, value):
        self.evidence['labels'].append(str(value))
        return _FakeElement(self.evidence, 'label')


def _canonical_engineering_keys() -> frozenset[str]:
    catalog = json.loads((ROOT / 'nicegui_base/ai/framework_catalog.json').read_text(encoding='utf-8'))
    return frozenset(item['_registry_key'] for item in catalog['registries']['engineering'])


def test_chg259_catalog_and_workbench_engineering_keys_have_exact_parity():
    from nicegui_base.workbench.catalog import all_entries
    from nicegui_base.workbench.domain_specimens import ENGINEERING_KEYS

    canonical_keys = _canonical_engineering_keys()
    catalog_entries = tuple(
        entry for entry in all_entries()
        if entry.metadata.get('registry_name') == 'engineering'
    )
    workbench_catalog_keys = frozenset(entry.metadata['registry_key'] for entry in catalog_entries)

    assert len(canonical_keys) == 15
    assert canonical_keys == workbench_catalog_keys == ENGINEERING_KEYS
    assert 'InvestigationContextBar' in canonical_keys
    assert PREVIOUS_ENGINEERING_KEYS <= ENGINEERING_KEYS
    assert len(PREVIOUS_ENGINEERING_KEYS) == 14


def test_every_advertised_engineering_route_uses_the_shared_specimen_dispatch(monkeypatch):
    from nicegui_base.integrations import nicegui_engineering
    from nicegui_base.workbench import catalog_runtime, domain_specimens
    from nicegui_base.workbench.catalog import all_entries
    from nicegui_base.engineering import InvestigationContextSpec

    ui = _FakeUI()
    monkeypatch.setitem(sys.modules, 'nicegui', SimpleNamespace(ui=ui))
    monkeypatch.setattr('nicegui_base.workbench.specimen_css.install_specimen_css', lambda: None)

    for name in (
        'EngineeringEntityCard', 'EngineeringStatusBadge', 'SpecLimitIndicator',
        'OutOfSpecIndicator', 'BaselineComparison', 'ConfidenceIndicator',
        'EvidenceCard', 'RcaEvidencePanel', 'EngineeringProcessTrend',
        'PopulationComparisonPanel', 'CommonalityTable', 'EngineeringTimeline',
    ):
        monkeypatch.setattr(
            nicegui_engineering, name,
            lambda *args, _name=name, **kwargs: SimpleNamespace(renderer=_name, args=args, kwargs=kwargs),
        )

    expected = {
        entry.metadata['registry_key']: entry
        for entry in all_entries()
        if entry.metadata.get('registry_name') == 'engineering'
    }
    dispatched = []
    render_shared_specimen = domain_specimens.render_engineering

    def record_shared_dispatch(key, **kwargs):
        dispatched.append(key)
        return render_shared_specimen(key, **kwargs)

    monkeypatch.setattr(domain_specimens, 'render_engineering', record_shared_dispatch)

    for key, entry in expected.items():
        rendered = catalog_runtime.render_catalog_example(entry.key)
        assert rendered is not None

    assert set(dispatched) == set(expected)
    assert len(dispatched) == len(expected) == 15

    context = catalog_runtime.render_catalog_example(expected['InvestigationContextBar'].key)
    assert type(context) is nicegui_engineering.InvestigationContextBar
    assert isinstance(context.spec, InvestigationContextSpec)
    assert context.spec == InvestigationContextSpec(
        'SYN-INV-259-001',
        'Illustrative chamber CD shift',
        'Example Process Engineer',
        'Evidence review · synthetic',
        'Synthetic fixture · 2026-09-26 09:00 UTC',
    )
    assert {
        'Investigation', 'Owner', 'Stage', 'Updated',
        'Synthetic engineering example — evidence and confidence below are illustrative, not production conclusions.',
    } <= set(ui.evidence['labels'])
    assert 'aria-label="Investigation context"' in ui.evidence['props']


def test_investigation_context_has_no_route_specific_workbench_branch():
    app = (ROOT / 'nicegui_base/workbench/app.py').read_text(encoding='utf-8')
    studio = (ROOT / 'nicegui_base/workbench/capability_studio.py').read_text(encoding='utf-8')
    runtime = (ROOT / 'nicegui_base/workbench/catalog_runtime.py').read_text(encoding='utf-8')

    assert 'InvestigationContextBar' not in app
    assert 'InvestigationContextBar' not in studio
    assert 'from .domain_specimens import render_engineering' in runtime
    assert 'return render_engineering(key' in runtime

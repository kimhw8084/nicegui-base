from __future__ import annotations


def test_every_catalog_entry_has_a_complete_typed_reference_contract():
    from nicegui_base.workbench.catalog import catalog_contract_audit, all_entries

    entries = all_entries()
    audit = catalog_contract_audit(entries)
    assert audit.complete, audit.issues[:10]
    assert audit.total == len(entries) == 465
    assert audit.conforming == audit.total
    assert all(
        entry.reference_contract.live_example or entry.reference_contract.nonvisual_variant
        for entry in entries
    )
    assert all(entry.reference_contract.recommended_code.strip() for entry in entries)


def test_reference_contract_is_machine_readable_and_nonvisual_is_explicit():
    from nicegui_base.workbench.catalog import all_entries

    contract = next(entry.reference_contract for entry in all_entries() if entry.key == 'component:button').to_dict()
    assert {
        'variants', 'configuration', 'when_to_use', 'when_not_to_use', 'data_contract',
        'states', 'responsive_behavior', 'accessibility', 'recommended_code',
        'alternatives', 'complements', 'best_for', 'avoid_for', 'requires', 'produces',
        'domain_tags', 'complexity', 'density', 'live_example', 'example_proof',
    } <= set(contract)
    nonvisual = next(entry for entry in all_entries() if entry.key == 'framework:analysis:analysis_context')
    assert nonvisual.reference_contract.live_example is False
    assert nonvisual.reference_contract.nonvisual_variant
    assert nonvisual.reference_contract.example_proof


def test_catalog_search_supports_intent_data_shape_domain_and_relationship_filters():
    from nicegui_base.workbench.catalog import search

    assert search('', intent='monitoring')[0].entry.key == 'recipe:fdc-tool-health'
    row_results = search('', data_shape='rows', limit=100)
    assert any(result.entry.key == 'framework:tables:data_table' for result in row_results)
    assert all(any('semiconductor' in tag for tag in result.entry.reference_contract.domain_tags) for result in search('', domain='semiconductor', limit=20))
    related = search('', related_to='analytics:fdc_recipe_step_trace', limit=20)
    assert any(result.entry.key == 'recipe:fdc-tool-health' for result in related)


def test_twelve_developer_intents_rank_deterministically_to_appropriate_references():
    from nicegui_base.workbench.catalog import search

    expectations = {
        'monitor equipment health': 'recipe:fdc-tool-health',
        'search process records': 'pattern:search',
        'compare wafers': 'recipe:lot-wafer-explorer',
        'investigate root cause': 'recipe:rca-cockpit',
        'show SPC trend': 'recipe:spc-monitor',
        'analyze distribution': 'analytics:box_distribution',
        'manage settings': 'pattern:settings',
        'create edit records': 'pattern:crud',
        'guided onboarding workflow': 'pattern:wizard',
        'show data table': 'pattern:data_explorer',
        'plot wafer spatial map': 'recipe:lot-wafer-explorer',
        'export code': 'framework:content:code_viewer',
    }
    first = {query: search(query, limit=5)[0].entry.key for query in expectations}
    second = {query: search(query, limit=5)[0].entry.key for query in expectations}
    assert first == second
    assert first == expectations


def test_reference_pages_use_direct_dispatch_and_no_generic_iframe_fallback():
    from pathlib import Path

    root = Path(__file__).parents[1]
    runtime = (root / 'nicegui_base' / 'workbench' / 'catalog_runtime.py').read_text()
    studio = (root / 'nicegui_base' / 'workbench' / 'capability_studio.py').read_text()
    assert "ui.element('iframe')" not in runtime
    assert 'render_catalog_example' in studio
    assert 'data-reference-contract' in studio
    assert 'No live visual required' in runtime


def test_contract_validation_rejects_blank_recommendation_and_unjustified_nonvisual():
    from dataclasses import replace

    from nicegui_base.workbench.catalog import catalog_contract_audit
    from nicegui_base.workbench.models import ReferenceContract, WorkbenchEntry, WorkbenchKind

    entry = WorkbenchEntry('reference:broken', WorkbenchKind.REFERENCE, 'Broken', 'Broken contract', '/broken')
    invalid = replace(entry, contract=ReferenceContract(
        variants=(), configuration=(), when_to_use=(), when_not_to_use=(), data_contract=(),
        states=(), responsive_behavior=(), accessibility=(), recommended_code='',
        alternatives=(), complements=(), best_for=(), avoid_for=(), requires=(), produces=(),
        domain_tags=(), complexity='', density='', live_example=False, example_proof='',
        nonvisual_variant=None,
    ))
    audit = catalog_contract_audit((invalid,))
    assert not audit.complete
    assert any('recommended_code' in issue for issue in audit.issues)
    assert any('nonvisual_variant' in issue for issue in audit.issues)

"""Wave 77 source-only final release-candidate consolidation example.

This demonstrates the diagnostic boundary only. It deliberately does not claim
installed target runtime, browser, company, human or stable 3.0.0 evidence.
"""
from __future__ import annotations

from pathlib import Path

from nicegui_base.governance.final_candidate import audit_final_release_candidate, build_stable_qualification_handoff

ROOT = Path(__file__).resolve().parents[1]
audit = audit_final_release_candidate(ROOT, require_final_artifacts=False)
handoff = build_stable_qualification_handoff(ROOT, audit)

assert audit.status == 'PASS'
assert handoff['source_release_candidate_status'] == 'SOURCE_COMPLETE'
assert handoff['stable_qualification_status'] == 'PENDING'
assert handoff['stable_publication_status'] == 'NOT_PERFORMED'

print(f"Wave 77 source release-candidate audit: {audit.status}; target qualification: {handoff['stable_qualification_status']}")

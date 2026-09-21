# Candidate validation

- Candidate: `57ebdee2619d8b5152615450701ea286f3758f48`
- Candidate tree: `ceec2ea6ed2280dd97c964e62da7cf52e7b68940`
- Base: `aa0e7cf611a70e6a35122590d6cf41ded05e6779`
- Fabric job: `CF-55d9db070dbd940c06f2c64d`

## PASS

- `rtk env PYTHONPATH=source python -m pytest -q source/tests/test_workbench_data_table_lab.py source/tests/test_workbench_chg108.py source/tests/test_data_table_final_integrity.py` — 28 passed.
- `rtk env PYTHONPATH=source python tools/verify_data_lab_code_copy_a11y.py --output <evidence>/final-focused` — 24/24 passed across Grid, Actions, Edit, Visualize, Import, Detail, Server and States at desktop-1440x900, mobile-390x844 and mobile-narrow-360x800.
- `rtk env PYTHONPATH=source nicegui-base runtime-contract` — PASS; NiceGUI 3.15.0.
- `rtk env PYTHONPATH=source nicegui-base runtime-smoke --port 0` — PASS; all 23 routes.

## PASS with preserved unrelated findings

- `rtk env PYTHONPATH=source python tools/run_data_table_visual_audit.py --output <evidence>/visual-audit` — interaction smoke PASS; accessibility records 64/64 PASS; matrix 60/64. The four existing failures are `dark-theme-not-applied` for Visualize in the four dark matrix viewports and are outside this request.

## FAIL / pre-existing repository gates

- `rtk env PYTHONPATH=source nicegui-base agent-check .` — FAIL before this change’s authority check because agent scaffold is missing and the existing `tools/verify_development_D6H2_browser.py` has a syntax error; existing warnings remain.
- `rtk env PYTHONPATH=source nicegui-base gate .` — FAIL on missing scaffold/manifest, dependency pin, invalid entrypoint and the same existing D6H2 syntax error; tests PASS.
- `rtk env PYTHONPATH=source python -m nicegui_base.validate .` — FAIL on the same existing D6H2 syntax error; existing warnings remain.

The prescribed `.venv/bin/python` commands were NOT_RUN because this checkout has no `.venv`; the equivalent installed Python 3.11.7 runtime was used.

# NiceGUI Base Workbench Iteration 2.8 — Data Contract & Adapter Assembly

Baseline: `2cf9a896e9cf32ee880a07caaaa05da1b961d7df`

- Data Dock field types, semantic roles, nullability and source identity persist through project state schema v5.
- Generated applications receive one canonical data contract shared by single-page and multi-page output.
- Schema-only is the safe default: deterministic synthetic fixture rows are generated and original Data Dock values are excluded from the ZIP.
- Explicit include-development-rows mode remains available and is declared in machine-readable contract metadata.
- Generated services/app_data.py is the single provider replacement boundary and returns the existing NiceGUI Base DataSource authority.
- Generated DataTable surfaces use DataSourceTable; generated chart examples derive labels/values from the same development fixture instead of hard-coded R-001/R-002 rows.
- Generated ZIP smoke self-validates and cross-checks Workbench/data-contract signatures and modes; runtime proof starts both single-page and multi-page data-bound applications.
- Every generated project gets a data-contract regression test plus README instructions for the single services/app_data.py::build_source provider replacement boundary.
- Project history explicitly reports blueprint, schema, source-name and data-handoff-policy changes instead of hiding them inside an opaque signature change.
- Wheel synchronization remains offline and validates an extracted installation shape including visual/package data.

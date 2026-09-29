# Proposed FIX sequence (no fixes executed)

## 1. UI0-A11Y-001 — P2 — Add semantic page-title heading through shared PageHeader

**Leverage:** one public framework renderer used by the Workbench shell and canonical PatternPage surfaces.

**Task centrality:** names every current workspace and enables heading navigation on component, table, analytics, recipe, application-pattern and lab routes.

**Accessibility/trust:** current page identity is visible but absent from the accessibility heading outline.

**Smallest bounded change:** change only the title element/heading semantics in `PageHeader`; retain `cui-page-title` and existing tokens. Add focused semantic coverage for shell and nested PatternPage consumer routes.

**Dependencies:** decide heading level ownership where a PatternPage is inside a shell before editing.

**Regression risks:** browser heading default margins/weight and duplicate h1 outline entries.

**Closure evidence:** DOM heading outline on representative route families, no duplicate page-level h1, canonical desktop/mobile pixel comparison, keyboard/screen-reader heading navigation.

No other mandatory P0/P1/P2 finding was supported by this audit. Optional polish remains outside the repair sequence.

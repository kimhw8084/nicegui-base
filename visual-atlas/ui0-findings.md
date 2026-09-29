# Initial UI0 findings — VERIFY-6

Source `aa17a17524af0edc6231b2a4a44d783dbff9fa23` / tree `28fea2880de94174dbb1d741e5f91c7e14345aeb`. Initial finding set frozen before the formal 1536×864 and 414×896 holdouts. One P2 shared-authority finding is recorded; no product fix was executed.

## UI0-A11Y-001 — P2: Page titles are not semantic headings

Across nine representative page families, the visual page title is present inside the single main landmark, but the main landmark contains zero `h1`, `h2`, `h3`, or `[role=heading]` elements. This leaves the page identity outside assistive heading navigation and forces linear reading order. The common owner is `PageHeader.__init__` in `source/nicegui_base/integrations/nicegui_layout.py:363`, which renders `ui.label(title)` with the visual `cui-page-title` class.

**Smallest bounded fix:** render the title as a semantic level-one heading while preserving the existing visual token/style contract; verify PatternPage compositions do not duplicate the shell heading.

**Regression risks:** browser default heading styles can shift typography/geometry, and nested compositions can create duplicate level-one headings. Closure needs semantic DOM evidence and unchanged responsive pixels. Exact screenshot hashes and route/DOM evidence are in `ui0-findings.json`.

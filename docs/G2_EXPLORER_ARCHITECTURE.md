# NiceGUI Base — GPT-6 Low-Level Product & Architecture Design

## Status

**Design complete. Implementation not yet declared complete.**

Baseline authority:
- Golden baseline: `NGB-20260906-D6H.3`
- Product direction: department-standard NiceGUI reference platform for humans and AI agents
- Primary objective: developers focus on business/domain logic while NiceGUI Base owns ordinary UI architecture, design, exploration, interaction states, responsive behavior, visualization choice, and production conventions.

---

# 1. Product architecture

NiceGUI Base is organized around six user-facing authority groups plus one system group.

## 1.1 Navigation information architecture

### Discover
- Start Here
- Global Search / Command Palette
- Recent / Favorites

### Foundations
- Design System
- Components
- Data & Tables
- Visualizations

### Compose
- Layouts
- Application Patterns

### Semiconductor
- Recipes
- Full Applications

### Develop
- AI Development Guide
- Scaffolding / CLI / Public API

### System
- Diagnostics
- About / Build identity

The sidebar must visually group these sections instead of presenting one flat list.

### Navigation rules
- One action from anywhere to any primary section.
- Active group and active page clearly visible.
- Desktop: grouped sidebar.
- Tablet: compact navigation rail or collapsible sidebar.
- Phone: drawer/sheet.
- Navigation state persists.
- Detail pages retain contextual back navigation.
- Returning from a detail page restores prior search/filter/scroll position.

---

# 2. Full-width application canvas

The page canvas is governed by the shell.

## 2.1 Width formula

`usable_width = viewport_width - navigation_width - governed_page_gutters`

No ordinary dashboard/reference page should add a second narrow outer max-width.

### Governed gutters
Use existing design-token authority:
- desktop: semantic page gutter
- tablet: reduced semantic page gutter
- phone: mobile semantic page gutter

Exact values remain token-owned.

## 2.2 Width exceptions
Only intentionally narrow content may constrain width:
- long-form reading
- focused form
- confirmation flow
- compact settings subsection

## 2.3 Space-efficiency rules
Avoid:
- fixed-height empty tables
- huge blank chart frames
- duplicate title blocks
- repeated metadata before the useful example
- unnecessary nested cards
- unused right/left whitespace

Prefer:
- auto-fit responsive grids
- content-sized tables
- wide chart/table combinations
- side-by-side contract + live example on wide screens
- adaptive collapse on tablet/phone

---

# 3. Start Here — intent-first discovery

The landing page is not an inventory dashboard.

Primary question:

> **What are you building?**

Intent cards/search should include:
- Monitor a process
- Investigate an excursion
- Compare tools or populations
- Explore engineering data
- Build an operational dashboard
- Manage records
- Configure settings
- Review wafer / yield / defects
- Analyze SPC
- Review FDC / tool health
- Start from a canonical shell

Each intent result returns, on one screen:
- recommended application pattern
- recommended layout
- recommended recipe
- recommended visualizations
- recommended components/compositions
- relevant full application
- scaffold command
- alternatives

No deep drill-down is required to understand the recommendation.

---

# 4. Exploration architecture

Exploration must minimize repeated clicks.

## 4.1 Click budgets

| User goal | Target |
|---|---:|
| Reach primary section | 1 action |
| Find known component | search + 1 selection |
| Understand what a visualization looks like | 0 detail clicks |
| Compare visualizations in same family | 0 detail clicks |
| Open full interactive/config/code view | 1 click |
| Return to prior catalog context | 1 action |
| Scaffold from selected pattern/recipe | 1 action |

## 4.2 Catalog browsing state

Persistent browsing state includes:
- search query
- selected family
- active filters
- sort/group preference
- favorites
- comparison selection
- scroll position
- theme
- density
- expanded groups where useful

Storage:
- browser-local for non-sensitive exploration preferences
- never store user data/provider data in the same shared cache

---

# 5. Visual gallery system

## 5.1 Visualization gallery

The visualization index must show recognizable visual previews for multiple visualizations simultaneously.

Each card contains:
- visual thumbnail or lightweight live miniature
- name
- family
- one-line “best for”
- required data shorthand
- semantic tags
- favorite / compare action
- open detail action

### Preview strategy

Tier 1 — cheap:
- render live miniature

Tier 2 — moderate:
- lazy mount when visible

Tier 3 — expensive:
- use version-bound cached/pre-rendered thumbnail
- mount full live renderer only on detail

Preview identity key:
`build_id + capability_key + fixture_version + renderer_version + relevant_configuration`

A stale thumbnail must never be labeled as a current live preview.

## 5.2 Component gallery

Component index cards should show compact governed specimens when practical.

Card actions:
- Preview
- States
- Code
- Favorite
- Compare when comparison is meaningful

Important variants/states should be visible without opening several separate screens when space allows.

## 5.3 Layout gallery

Each layout card shows miniature governed compositions for:
- desktop
- tablet
- phone

Visible regions:
- navigation
- header
- content area
- filter/action region
- inspector/detail area
- responsive transformation

## 5.4 Pattern gallery

Each application-pattern card shows the actual defining anatomy.

Examples:
- Dashboard: KPI + trend + exceptions
- Monitoring: status + trend + alerts + records
- Comparison: aligned entities + deltas + visualization
- Analysis Workspace: filters + primary visual + table + inspector

## 5.5 Recipe / Full Application gallery

Cards show:
- domain-specific screenshot/miniature
- question answered
- pattern
- primary analytics
- data contract shorthand
- scaffold/open action

---

# 6. Detail-page anatomy

Every governed detail page follows one consistent structure.

## 6.1 Wide desktop

Two-column first viewport:

### Left / primary
- live governed example
- key variants / states
- direct interactions

### Right / contract
- best for
- avoid when
- required data
- alternatives
- complements
- production API
- scaffold / copy action

Secondary sections:
- advanced configuration
- states
- responsive behavior
- accessibility
- production code
- related references

## 6.2 Tablet
- primary example first
- contract becomes collapsible secondary panel

## 6.3 Phone
- useful example visible early
- filters/configuration behind compact disclosure
- code and advanced metadata below primary example

Debug/session information belongs in Diagnostics/developer mode, not normal reference flow.

---

# 7. Search architecture

## 7.1 Global search

One command palette searchable by:
- exact name
- alias
- family
- intent
- engineering question
- data shape
- domain
- related capability
- pattern/recipe
- public API name

## 7.2 Local catalog search

Local catalog filtering is client-fast or in-process-fast and must not rebuild the registry.

Typical target:
- <=100 ms search response on local Golden install

## 7.3 Search result ranking

Ranking inputs:
1. exact title/key
2. aliases/public names
3. best_for
4. domain tags
5. intent tags
6. data requirements
7. related capabilities
8. description

Search must return the canonical authority only, not duplicate aliases as separate results.

---

# 8. Comparison system

Comparison is available for:
- visualizations
- components where useful
- layouts
- patterns
- recipes

Maximum normal comparison:
- 3 items

Comparison surface shows:
- visual miniatures
- best_for
- avoid_for
- required data
- interaction support
- responsive behavior
- alternatives
- complexity
- scaffold/public API

Goal:
the user should not need to open/back/open/back repeatedly.

---

# 9. Favorites and recents

## 9.1 Favorites
Store non-sensitive capability IDs locally.

Use for:
- favorite visualizations
- favorite components
- favorite recipes/patterns

## 9.2 Recents
Track recent reference items and recently used scaffold authorities.

Do not mix with user application data.

---

# 10. Catalog and cache authority

## 10.1 Canonical registry projection

Reuse the existing canonical registry projection.

No second catalog.

Static projection:
- constructed once per process/build
- immutable
- cached

## 10.2 Cache classes

### Reference metadata cache
Key:
`build_id`

Contains:
- normalized catalog projection
- families
- search terms
- relationships
- public API metadata

### Preview fixture cache
Key:
`build_id + capability + fixture_version`

Contains:
- canonical synthetic sample preparation
- never user data

### Preview render cache
Key:
`build_id + capability + renderer_version + fixture_version + preview_variant`

Contains:
- thumbnail/precomputed presentation if applicable

### Provider/query cache
Separate from reference caches.
Must include:
- user/authorization scope
- provider identity
- normalized query
- version/TTL

No cross-user shared user-data cache.

---

# 11. Performance design

## 11.1 Performance budgets

- shell usable quickly after server readiness: target <=2 s
- warm primary navigation: perceived <=300 ms
- local catalog search: typical <=100 ms
- >300 ms operation gets immediate progress/skeleton
- filter changes never block browser main interaction
- preview gallery must use bounded live rendering

## 11.2 Gallery loading

Initial page:
- metadata
- above-the-fold thumbnails
- visible-card previews only

Then:
- intersection/lazy loading
- bounded concurrency
- cancel previews that leave viewport if expensive

Do not mount 58 heavy charts simultaneously.

---

# 12. Responsive navigation design

## Desktop
- full grouped sidebar
- section headings
- active page indicator
- optional collapse to compact rail

## Tablet
- compact rail by default or easily collapsible sidebar
- main canvas gets priority

## Phone
- one navigation button
- grouped drawer/sheet
- no desktop shortcut hints consuming width
- search accessible from header

Navigation groups must help users understand the product taxonomy.

---

# 13. Design-system consumption

Normal application code uses:
- semantic spacing/gap
- semantic typography
- semantic radius
- semantic surfaces
- governed density
- governed breakpoints
- standard states

Application code should not normally contain:
- arbitrary padding/margin
- arbitrary border radius
- arbitrary colors
- arbitrary typography
- local breakpoints
- ad-hoc z-index

Validator flags governed-code violations.

---

# 14. Component coverage model

Before adding a component:
1. search existing canonical component
2. check supported variants
3. check composition primitives
4. prove recurring behavior gap
5. only then add a canonical authority

A new canonical component must include:
- public API
- Preview
- States
- Code
- responsive behavior
- accessibility
- tests
- catalog metadata

Styling-only differences become variants.

---

# 15. Production-state system

Canonical application states:
- loading
- skeleton
- empty
- empty filtered result
- error
- retry
- invalid input
- permission denied
- read-only
- disabled
- stale
- partial
- delayed operation
- cancellation
- latest-response-wins
- destructive confirmation
- success
- warning
- unavailable

Patterns/full applications must demonstrate relevant states.

---

# 16. Data-heavy UX design

Canonical DataTable/query behavior covers:
- server pagination
- sorting
- filtering
- selection
- editing
- schema
- engineering units
- master/detail
- drill-down
- large result sets
- cancellation
- debounce
- auto refresh
- stale status
- import validation
- export
- provider abstraction

No silent truncation.

---

# 17. Visualization semantic contract

Every visualization must satisfy:

`name → data contract → canonical fixture → geometry → axes → legend → statistics → domain meaning`

Semantic browser tests remain required.

Gallery thumbnails must reflect the same governed renderer semantics.

---

# 18. Application pattern authority

Patterns are reusable composition authorities, not renamed demos.

Canonical patterns:
- Dashboard
- Monitoring
- Analysis Workspace
- Comparison
- Data Explorer
- Master Detail
- CRUD
- Search
- Settings
- Wizard
- additional pattern only if recurring need is proven

---

# 19. Semiconductor recipe authority

Recipes combine:
- engineering question
- required data
- layout/pattern
- visualizations
- components
- states
- sample
- scaffold
- caveats

No recipe should invent causal conclusions.

---

# 20. Golden full-application expansion

Keep the set small and high-quality.

Recommended final families:
1. SPC Control Center
2. FDC Tool Health Center
3. Excursion Investigation
4. Wafer & Yield Explorer
5. Lot Genealogy Explorer
6. Tool Matching Workspace
7. Recipe Comparison Lab
8. Engineering Data Explorer
9. Operations Dashboard
10. Managed Records / Admin

Only add missing families needed for coverage.

---

# 21. AI-agent interface

Machine-readable commands remain the primary agent interface.

Required capabilities:
- catalog search
- pattern recommendation
- visualization recommendation
- scaffold plan
- create pattern
- create recipe
- validate
- agent check
- runtime contract
- runtime smoke

Agent workflow:
1. parse business requirement
2. resolve data/domain
3. recommend pattern
4. recommend visualization
5. select components
6. scaffold
7. implement app-owned logic
8. validate

---

# 22. Public API vs Reference Explorer internals

Reference Explorer may use internal harness modules.

Production examples must prefer:
`from nicegui_base import ...`

Do not teach developers to copy internal Workbench/Reference Explorer helpers unless they are intentionally public.

---

# 23. Diagnostics model

Diagnostics reports separate states:
- registered
- discoverable
- preview-backed
- sample-backed
- semantically verified
- responsive
- code-backed
- production-ready
- Golden-promoted

The UI must never collapse these into one misleading readiness percentage.

---

# 24. Testability and telemetry

Local Reference Explorer should expose performance diagnostics for maintainers:
- catalog build time
- search latency
- preview preparation latency
- thumbnail cache hit/miss
- live preview mount count
- active preview count

No user-sensitive data in diagnostics.

---

# 25. Qualification design

A new candidate must prove:

## Correctness
- complete source suite
- root suite
- validator
- semantic analytics
- pattern anatomy
- component evidence

## Packaging
- fresh wheel
- source/wheel exact match
- isolated install
- pip check
- site-packages provenance

## Runtime
- healthy readiness
- route smoke
- graceful shutdown

## Exploration
- grouped navigation
- full-width canvas
- visual galleries
- click budget
- state restore
- comparison
- favorites
- search latency
- cache behavior

## Visual
- desktop/tablet/phone
- light/dark
- index/gallery screenshots
- detail screenshots
- human review

No Golden promotion from DOM/page-load checks alone.

---

# 26. Proposed implementation module boundaries

Reuse current authorities; add only bounded Explorer modules.

Suggested internal modules:

`workbench/explorer_state.py`
- browsing state model
- serialization
- local storage contract
- scroll/filter restoration

`workbench/explorer_gallery.py`
- generic visual gallery model
- cards
- comparison selection
- favorites

`workbench/preview_catalog.py`
- preview metadata projection
- preview type: live/lazy/thumbnail
- immutable preview identity

`workbench/preview_cache.py`
- build-bound preview cache
- safe cache keys/invalidation
- no user-data caching

`workbench/explorer_search.py`
- UI search adapter over existing canonical catalog search
- ranking/explanation presentation
- no new registry

`workbench/explorer_compare.py`
- bounded 2–3 item comparison model/UI

Existing modules remain authorities:
- `catalog.py`
- `registry_adapters.py`
- `component_specimens.py`
- `analytic_specimens.py`
- `pattern_specimens.py`
- `full_applications.py`
- `design/tokens.py`
- `ai/discovery.py`

No parallel component/analytics registry is introduced.

---

# 27. Migration strategy

1. Freeze D6H.3 as rollback baseline.
2. Add new Explorer internals behind existing routes.
3. Preserve existing detail URLs.
4. Convert flat nav into grouped presentation without changing route semantics.
5. Replace text-only indexes with visual galleries.
6. Add state preservation.
7. Add preview cache/thumbnails.
8. Add compare/favorites.
9. Add missing production states/data compositions.
10. Add only proven missing full-app families/components.
11. qualify a new candidate identity.

---

# 28. Final user experience

A user opening NiceGUI Base should be able to:

1. understand the product immediately;
2. choose what they are building;
3. see the recommended application anatomy;
4. visually compare candidate charts/components without drilling into each;
5. open one detail when deeper inspection is needed;
6. copy/scaffold the canonical solution;
7. return to the same browsing context;
8. focus on domain logic.

That is the completed low-level design target.

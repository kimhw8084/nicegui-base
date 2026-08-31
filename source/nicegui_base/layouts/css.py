from __future__ import annotations

from nicegui_base.design import build_design_system


def build_layout_css() -> str:
    s = build_design_system()
    phone = s.breakpoints['phone']
    tablet = s.breakpoints['tablet']
    laptop = s.breakpoints['laptop']
    return f"""
:root {{
  --cui-page-reading-width: 760px;
  --cui-page-standard-width: 1120px;
  --cui-page-wide-width: 1440px;
  --cui-drawer-small: 320px;
  --cui-drawer-medium: 420px;
  --cui-drawer-large: 560px;
  --cui-drawer-xlarge: 720px;
}}

.nicegui-content.cui-nicegui-content {{ padding: 0 !important; gap: 0 !important; }}
.cui-app-header {{
  min-height: var(--cui-shell-header-height); background: color-mix(in srgb, var(--cui-surface) 92%, transparent);
  color: var(--cui-text-primary); border-bottom: 1px solid var(--cui-border-subtle);
  box-shadow: none; backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
}}
.cui-app-sidebar {{
  background: var(--cui-surface); color: var(--cui-text-primary);
  border-right: 1px solid var(--cui-border-subtle); box-shadow: none;
}}
.cui-skip-link {{ position:fixed; left:var(--cui-space-3); top:var(--cui-space-3); z-index:var(--cui-skip-link-z); transform:translateY(-180%); padding:var(--cui-space-2) var(--cui-space-3); border-radius:var(--cui-radius-control); background:var(--cui-accent); color:var(--cui-on-accent); font-weight:var(--cui-font-weight-600); text-decoration:none; }}
.cui-skip-link:focus {{ transform:translateY(0); outline:2px solid var(--cui-focus-ring); outline-offset:2px; }}
.cui-app-main {{ width: 100%; min-width: 0; gap: 0; align-items: stretch; }}
.cui-shell-title {{ font-size: var(--cui-type-subheading-size); line-height: var(--cui-type-subheading-line); font-weight: var(--cui-type-subheading-weight); letter-spacing: var(--cui-type-subheading-tracking); }}
.cui-shell-menu {{ color: var(--cui-text-secondary); }}
.cui-environment-badge {{ background: var(--cui-surface-secondary); color: var(--cui-text-secondary); border: 1px solid var(--cui-border-default); }}
.cui-nav-section-label {{ padding: var(--cui-space-4) var(--cui-space-3) var(--cui-space-2); color: var(--cui-text-tertiary); font-size: var(--cui-type-caption-size); line-height: var(--cui-type-caption-line); font-weight: var(--cui-font-weight-600); text-transform: uppercase; letter-spacing: .08em; }}
.cui-nav-item {{ min-height: 36px; margin: 2px var(--cui-space-2); border-radius: var(--cui-radius-sm); color: var(--cui-text-secondary); transition: background var(--cui-motion-fast) var(--cui-ease-standard), color var(--cui-motion-fast) var(--cui-ease-standard); }}
.cui-nav-item:hover {{ background: var(--cui-surface-hover); color: var(--cui-text-primary); }}
.cui-nav-item--active {{ background: var(--cui-accent-soft); color: var(--cui-accent); font-weight: var(--cui-font-weight-600); }}
.cui-nav-expansion {{ margin: 2px var(--cui-space-2); border-radius: var(--cui-radius-sm); color: var(--cui-text-secondary); }}
.cui-page-title {{ font-size: var(--cui-type-page_title-size); line-height: var(--cui-type-page_title-line); font-weight: var(--cui-type-page_title-weight); letter-spacing: var(--cui-type-page_title-tracking); color: var(--cui-text-primary); }}
.cui-page-description {{ max-width: 760px; font-size: var(--cui-type-body-size); line-height: var(--cui-type-body-line); color: var(--cui-text-secondary); }}
.cui-breadcrumbs {{ gap: var(--cui-space-1); color: var(--cui-text-tertiary); font-size: var(--cui-type-caption-size); line-height: var(--cui-type-caption-line); }}
.cui-breadcrumb {{ color: inherit; text-decoration: none; }}
.cui-breadcrumb-separator {{ color: var(--cui-border-strong); }}

.cui-page {{ width: 100%; min-width: 0; padding: var(--cui-space-6); gap: var(--cui-space-6); }}
.cui-page--reading {{ max-width: var(--cui-page-reading-width); margin-inline: auto; }}
.cui-page--standard {{ max-width: var(--cui-page-standard-width); margin-inline: auto; }}
.cui-page--wide {{ max-width: var(--cui-page-wide-width); margin-inline: auto; }}
.cui-page--full {{ max-width: none; }}
.cui-page-header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: var(--cui-space-4); width: 100%; }}
.cui-page-header__copy {{ min-width: 0; display: flex; flex-direction: column; gap: var(--cui-space-1); }}
.cui-page-header__actions {{ display: flex; flex-wrap: wrap; justify-content: flex-end; gap: var(--cui-space-2); }}
.cui-section {{ width: 100%; min-width: 0; display: flex; flex-direction: column; gap: var(--cui-space-3); }}
.cui-stack {{ display: flex; min-width: 0; }}
.cui-stack--vertical {{ flex-direction: column; }}
.cui-stack--horizontal {{ flex-direction: row; }}
.cui-stack--responsive {{ flex-direction: row; }}
.cui-gap--none {{ gap: 0; }} .cui-gap--xs {{ gap: var(--cui-space-2); }} .cui-gap--sm {{ gap: var(--cui-space-3); }}
.cui-gap--md {{ gap: var(--cui-space-4); }} .cui-gap--lg {{ gap: var(--cui-space-6); }} .cui-gap--xl {{ gap: var(--cui-space-8); }}
.cui-align--start {{ align-items: flex-start; }} .cui-align--center {{ align-items: center; }} .cui-align--end {{ align-items: flex-end; }} .cui-align--stretch {{ align-items: stretch; }}
.cui-grid {{ display: grid; width: 100%; min-width: 0; gap: var(--cui-space-4); }}
.cui-grid--metrics {{ grid-template-columns: repeat(4, minmax(0,1fr)); }}
.cui-grid--halves {{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
.cui-grid--thirds {{ grid-template-columns: repeat(3, minmax(0,1fr)); }}
.cui-grid--fourths {{ grid-template-columns: repeat(4, minmax(0,1fr)); }}
.cui-grid--sidebar_content {{ grid-template-columns: minmax(220px, 280px) minmax(0,1fr); }}
.cui-grid--content_inspector {{ grid-template-columns: minmax(0,1fr) minmax(280px, 380px); }}
.cui-grid--main_aside {{ grid-template-columns: minmax(0,2fr) minmax(280px,1fr); }}
.cui-grid--auto {{ grid-template-columns: repeat(auto-fit, minmax(220px,1fr)); }}
.cui-scrollable {{ min-height: 0; overflow: auto; overscroll-behavior: contain; }}
.cui-sticky {{ position: sticky; top: calc(var(--cui-shell-header-height) + var(--cui-space-3)); z-index: var(--cui-layer-sticky); }}
.cui-workspace {{ width: 100%; min-width: 0; min-height: calc(100dvh - var(--cui-shell-header-height)); padding: var(--cui-space-3); }}
.cui-tabs-region {{ min-width: 0; width: 100%; }}
.cui-splitter {{ min-width: 0; min-height: 0; width: 100%; }}
.cui-resizable-panel {{ min-width: 0; min-height: 0; width: 100%; height: 100%; overflow: auto; }}
.cui-drawer--small {{ width: var(--cui-drawer-small); }}
.cui-drawer--medium {{ width: var(--cui-drawer-medium); }}
.cui-drawer--large {{ width: var(--cui-drawer-large); }}
.cui-drawer--xlarge {{ width: var(--cui-drawer-xlarge); }}
.cui-pattern-slot {{ width: 100%; min-width: 0; }}
.cui-page-navigation {{ width: 100%; }}
.cui-segmented-control {{ border-radius: var(--cui-radius-sm); }}
.cui-user-menu-trigger {{ color: var(--cui-text-secondary); }}

.cui-app-info-dialog {{ min-width:min(420px,calc(100vw - 32px)); }}
.cui-pattern {{
  --cui-pattern-gap:20px;
  display:grid !important; grid-template-columns:repeat(12,minmax(0,1fr));
  align-items:start; grid-auto-flow:row; gap:var(--cui-pattern-gap);
}}
.cui-pattern > .cui-page-header,.cui-pattern-slot--header {{ grid-column:1 / -1; }}
.cui-pattern-slot {{ width:100%; min-width:0; display:flex; flex-direction:column; gap:var(--cui-space-3); }}
.cui-pattern-slot--plain {{ min-width:0; }}
.cui-pattern-slot--subtle {{ padding:12px 14px; border-radius:var(--cui-radius-surface); background:var(--cui-surface-secondary); box-shadow:inset 0 0 0 1px var(--cui-border-subtle); }}
.cui-pattern-slot--surface {{ padding:16px; border-radius:var(--cui-radius-surface); background:var(--cui-surface); box-shadow:inset 0 0 0 1px var(--cui-border-subtle),var(--cui-shadow-1); }}
.cui-pattern-slot--inspector {{ padding:16px; border-radius:var(--cui-radius-surface); background:var(--cui-surface-secondary); box-shadow:inset 0 0 0 1px var(--cui-border-default); }}
.cui-pattern-slot.is-sticky {{ position:sticky; top:calc(var(--cui-shell-header-height) + var(--cui-page-gutter)); z-index:var(--cui-layer-sticky); }}
.cui-pattern-slot--actions {{ display:flex; flex-direction:row; align-items:center; justify-content:flex-end; flex-wrap:wrap; gap:var(--cui-space-2); }}
.cui-pattern-slot--metrics:has(> .cui-metric-card) {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:var(--cui-space-3); }}
.cui-pattern-filter-controls {{ display:flex; align-items:flex-end; flex-wrap:wrap; gap:10px; min-width:0; }}
.cui-pattern-filter-controls > * {{ flex:0 1 auto; min-width:0; }}
.cui-pattern-section-title {{ margin:0; color:var(--cui-text-primary); font-size:var(--cui-font-size-15); line-height:var(--cui-line-height-20); font-weight:var(--cui-font-weight-680); letter-spacing:-.015em; }}
.cui-settings-navigation {{ display:flex; flex-direction:column; gap:4px; width:100%; }}
.cui-settings-navigation .cui-button {{ width:100%; justify-content:flex-start; text-align:left; }}
.cui-settings-navigation .cui-button__label {{ flex:1; text-align:left; }}
.cui-pattern--master_detail .cui-pattern-slot--details .cui-chart-panel {{ min-height:260px; }}
.cui-pattern--search .cui-search-results {{ gap:8px; }}
.cui-pattern--analysis_workspace .cui-pattern-slot--details {{ gap:14px; }}

/* Canonical 12-column application compositions. Missing optional slots do not leave empty grid areas. */
.cui-pattern--dashboard .cui-pattern-slot--filters,.cui-pattern--dashboard .cui-pattern-slot--metrics,.cui-pattern--dashboard .cui-pattern-slot--data,.cui-pattern--dashboard .cui-pattern-slot--actions {{ grid-column:1 / -1; }}
.cui-pattern--dashboard .cui-pattern-slot--primary {{ grid-column:1 / 9; }}
.cui-pattern--dashboard .cui-pattern-slot--secondary {{ grid-column:9 / -1; }}

.cui-pattern--monitoring .cui-pattern-slot--filters,.cui-pattern--monitoring .cui-pattern-slot--metrics,.cui-pattern--monitoring .cui-pattern-slot--data,.cui-pattern--monitoring .cui-pattern-slot--actions {{ grid-column:1 / -1; }}
.cui-pattern--monitoring .cui-pattern-slot--primary {{ grid-column:1 / 9; }}
.cui-pattern--monitoring .cui-pattern-slot--secondary {{ grid-column:9 / -1; }}
.cui-pattern--monitoring .cui-pattern-slot--details {{ grid-column:1 / -1; }}

.cui-pattern--data_explorer .cui-pattern-slot--filters,.cui-pattern--data_explorer .cui-pattern-slot--metrics,.cui-pattern--data_explorer .cui-pattern-slot--data,.cui-pattern--data_explorer .cui-pattern-slot--details,.cui-pattern--data_explorer .cui-pattern-slot--actions {{ grid-column:1 / -1; }}
.cui-pattern--data_explorer .cui-pattern-slot--primary {{ grid-column:1 / 9; }}
.cui-pattern--data_explorer .cui-pattern-slot--secondary {{ grid-column:9 / -1; }}

.cui-pattern--master_detail .cui-pattern-slot--filters,.cui-pattern--master_detail .cui-pattern-slot--actions {{ grid-column:1 / -1; }}
.cui-pattern--master_detail .cui-pattern-slot--data {{ grid-column:1 / 8; }}
.cui-pattern--master_detail .cui-pattern-slot--details {{ grid-column:8 / -1; }}

.cui-pattern--crud .cui-pattern-slot--filters {{ grid-column:1 / 9; }}
.cui-pattern--crud .cui-pattern-slot--actions {{ grid-column:9 / -1; }}
.cui-pattern--crud .cui-pattern-slot--data,.cui-pattern--crud .cui-pattern-slot--details {{ grid-column:1 / -1; }}

.cui-pattern--search .cui-pattern-slot--filters {{ grid-column:1 / 4; }}
.cui-pattern--search .cui-pattern-slot--data,.cui-pattern--search .cui-pattern-slot--details {{ grid-column:4 / -1; }}
.cui-pattern--search .cui-pattern-slot--actions {{ grid-column:1 / -1; }}

.cui-pattern--settings .cui-pattern-slot--navigation {{ grid-column:1 / 4; }}
.cui-pattern--settings .cui-pattern-slot--content,.cui-pattern--settings .cui-pattern-slot--actions {{ grid-column:4 / -1; }}

.cui-pattern--wizard .cui-pattern-slot--navigation,.cui-pattern--wizard .cui-pattern-slot--content,.cui-pattern--wizard .cui-pattern-slot--actions {{ grid-column:3 / 11; }}

.cui-pattern--comparison .cui-pattern-slot--filters,.cui-pattern--comparison .cui-pattern-slot--metrics,.cui-pattern--comparison .cui-pattern-slot--primary,.cui-pattern--comparison .cui-pattern-slot--secondary,.cui-pattern--comparison .cui-pattern-slot--data,.cui-pattern--comparison .cui-pattern-slot--details {{ grid-column:1 / -1; }}

.cui-pattern--analysis_workspace .cui-pattern-slot--filters,.cui-pattern--analysis_workspace .cui-pattern-slot--data,.cui-pattern--analysis_workspace .cui-pattern-slot--actions {{ grid-column:1 / -1; }}
.cui-pattern--analysis_workspace .cui-pattern-slot--primary,.cui-pattern--analysis_workspace .cui-pattern-slot--secondary {{ grid-column:1 / 9; }}
.cui-pattern--analysis_workspace .cui-pattern-slot--details {{ grid-column:9 / -1; grid-row:2 / span 2; }}

@media (max-width: {laptop - 1}px) {{
  .cui-pattern-slot--metrics:has(> .cui-metric-card) {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
  .cui-grid--metrics, .cui-grid--fourths {{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
  .cui-grid--thirds {{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
}}
@media (max-width: {tablet - 1}px) {{
  .cui-pattern {{ grid-template-columns:1fr; gap:16px; }}
  .cui-pattern > .cui-page-header,.cui-pattern-slot,.cui-pattern--wizard .cui-pattern-slot--navigation,.cui-pattern--wizard .cui-pattern-slot--content,.cui-pattern--wizard .cui-pattern-slot--actions {{ grid-column:1 / -1 !important; grid-row:auto !important; }}
  .cui-pattern-slot.is-sticky {{ position:static; }}
  .cui-page {{ padding: var(--cui-space-4); gap: var(--cui-space-5); }}
  .cui-page-header {{ flex-direction: column; }}
  .cui-page-header__actions {{ justify-content: flex-start; }}
  .cui-stack--responsive {{ flex-direction: column; }}
  .cui-grid--sidebar_content, .cui-grid--content_inspector, .cui-grid--main_aside {{ grid-template-columns: 1fr; }}
}}
@media (max-width: {phone - 1}px) {{
  .cui-pattern-slot--metrics:has(> .cui-metric-card) {{ grid-template-columns:1fr; }}
  .cui-pattern-slot--filters {{ padding:var(--cui-space-2); }}
  .cui-pattern-slot--actions {{ justify-content:stretch; flex-wrap:wrap; }}
  .cui-pattern-slot--actions > * {{ flex:1 1 auto; }}
  .cui-page {{ padding: var(--cui-space-3); gap: var(--cui-space-4); }}
  .cui-grid--metrics, .cui-grid--halves, .cui-grid--thirds, .cui-grid--fourths {{ grid-template-columns: 1fr; }}
  .cui-workspace {{ padding: var(--cui-space-2); }}
}}
""".strip() + "\n"

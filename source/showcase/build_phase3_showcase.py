from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nicegui_base.design.css import build_css
from nicegui_base.layouts.css import build_layout_css
from nicegui_base.components.css import build_component_css

base_css = build_css() + '\n' + build_layout_css() + '\n' + build_component_css()

extra_css = r'''
*{box-sizing:border-box} html{scroll-behavior:smooth} body{margin:0}
button,input,select,textarea{font:inherit}
.demo-shell{display:grid;grid-template-columns:248px minmax(0,1fr);min-height:100vh;background:var(--cui-page)}
.demo-sidebar{position:sticky;top:0;height:100vh;background:var(--cui-surface);border-right:1px solid var(--cui-border-subtle);padding:12px;overflow:auto}
.demo-brand{display:flex;align-items:center;gap:10px;padding:10px 8px 16px}
.demo-mark{width:34px;height:34px;border-radius:10px;background:var(--cui-accent);color:var(--cui-text-inverse);display:grid;place-items:center;font-weight:700}
.demo-brand-title{font-size:13px;font-weight:650}.demo-caption{font-size:var(--cui-type-caption-size);color:var(--cui-text-tertiary)}
.demo-nav-label{padding:14px 10px 6px;font-size:10px;text-transform:uppercase;letter-spacing:.09em;color:var(--cui-text-tertiary)}
.demo-nav{display:flex;flex-direction:column;gap:2px}.demo-nav a{padding:8px 10px;border-radius:var(--cui-radius-sm);font-size:12px;color:var(--cui-text-secondary);text-decoration:none}.demo-nav a:hover{background:var(--cui-surface-hover);color:var(--cui-text-primary)}.demo-nav a.active{background:var(--cui-accent-soft);color:var(--cui-accent);font-weight:600}
.demo-main{min-width:0}.demo-topbar{height:56px;position:sticky;top:0;z-index:10;display:flex;align-items:center;justify-content:space-between;padding:0 24px;border-bottom:1px solid var(--cui-border-subtle);background:color-mix(in srgb,var(--cui-surface) 90%,transparent);backdrop-filter:blur(16px)}
.demo-top-title{font-size:13px;font-weight:600}.demo-top-actions{display:flex;align-items:center;gap:8px}.demo-page{max-width:1320px;margin:0 auto;padding:24px;display:flex;flex-direction:column;gap:24px}
.demo-page-head{display:flex;align-items:flex-start;justify-content:space-between;gap:20px}.demo-page-title{font-size:var(--cui-type-page_title-size);line-height:var(--cui-type-page_title-line);font-weight:var(--cui-type-page_title-weight);letter-spacing:var(--cui-type-page_title-tracking)}.demo-page-sub{font-size:13px;color:var(--cui-text-secondary);max-width:760px;margin-top:3px}
.demo-section{display:flex;flex-direction:column;gap:10px}.demo-section-head{display:flex;align-items:end;justify-content:space-between;gap:20px}.demo-section-title{font-size:16px;font-weight:650}.demo-section-note{font-size:11px;color:var(--cui-text-tertiary)}
.demo-panel{padding:16px}.demo-card{padding:16px}.demo-toolbar{display:flex;flex-wrap:wrap;align-items:end;gap:10px}.demo-toolbar .cui-field{min-width:180px;flex:1 1 180px}.demo-toolbar .search{flex:2 1 300px}.demo-toolbar .cui-button{height:var(--cui-control-medium)}
.demo-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.metric{padding:14px}.metric-label{font-size:11px;color:var(--cui-text-tertiary)}.metric-value{font-size:24px;line-height:30px;font-weight:680;letter-spacing:-.025em;font-variant-numeric:tabular-nums}.metric-foot{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:6px;font-size:11px;color:var(--cui-text-secondary)}
.demo-grid{display:grid;grid-template-columns:1.2fr .8fr;gap:14px}.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.full{grid-column:1/-1}
.demo-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:4px;padding-top:12px;border-top:1px solid var(--cui-border-subtle)}
.demo-matrix{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.matrix-panel{padding:16px}.row{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.stack{display:flex;flex-direction:column;gap:10px}.label{font-size:11px;color:var(--cui-text-tertiary);margin-bottom:6px}.spacer{height:4px}
.demo-input{border:0;outline:0;width:100%;background:transparent;color:var(--cui-text-primary)}
.demo-select{appearance:none}.demo-field-wrap{min-width:0}.demo-field-wrap .cui-field-control{height:var(--cui-control-medium)}
.choice-demo{display:flex;align-items:flex-start;gap:8px;cursor:pointer}.choice-demo input{margin-top:3px;accent-color:var(--cui-accent)}.choice-copy{font-size:13px}.choice-help{font-size:11px;color:var(--cui-text-tertiary)}
.switch-demo{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:10px 0}.switch-control{border:0;padding:0;background:transparent;cursor:pointer}.switch-control .cui-switch-track{display:block}.switch-control[aria-checked=true] .cui-switch-track{background:var(--cui-accent)}.switch-control[aria-checked=true] .cui-switch-thumb{transform:translateX(14px)}
.upload-demo{cursor:pointer}.upload-demo input{display:none}.upload-icon{width:28px;height:28px;border-radius:8px;background:var(--cui-accent-soft);color:var(--cui-accent);display:grid;place-items:center;margin:0 auto 7px;font-weight:700}
.state-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.state-cell{padding:12px;border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-md);background:var(--cui-surface-secondary)}
.preview-table{width:100%;border-collapse:collapse;font-size:12px}.preview-table th{text-align:left;color:var(--cui-text-tertiary);font-size:10px;text-transform:uppercase;letter-spacing:.06em;padding:9px 10px;border-bottom:1px solid var(--cui-border-default)}.preview-table td{padding:10px;border-bottom:1px solid var(--cui-border-subtle)}.preview-table tr:last-child td{border-bottom:0}
.theme-control,.density-control{display:inline-flex;padding:2px;background:var(--cui-surface-secondary);border:1px solid var(--cui-border-default);border-radius:var(--cui-radius-sm)}.theme-control button,.density-control button{border:0;background:transparent;color:var(--cui-text-secondary);border-radius:6px;padding:5px 8px;font-size:11px;cursor:pointer}.theme-control button.active,.density-control button.active{background:var(--cui-surface);color:var(--cui-text-primary);box-shadow:var(--cui-shadow-1)}
.kbd{padding:2px 5px;border:1px solid var(--cui-border-default);border-bottom-color:var(--cui-border-strong);border-radius:5px;background:var(--cui-surface-secondary);font-size:10px;color:var(--cui-text-secondary)}
.collapse-body{display:none}.collapse.open .collapse-body{display:block}.collapse .chev{transition:transform var(--cui-motion-fast) var(--cui-ease-standard)}.collapse.open .chev{transform:rotate(90deg)}
@media(max-width:980px){.demo-shell{grid-template-columns:72px minmax(0,1fr)}.demo-brand>div:last-child,.demo-nav span,.demo-nav-label{display:none}.demo-brand{justify-content:center}.demo-nav a{font-size:0;text-align:center}.demo-nav a::first-letter{font-size:12px}.demo-grid,.demo-matrix{grid-template-columns:1fr}.demo-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:650px){.demo-shell{display:block}.demo-sidebar{display:none}.demo-topbar{padding:0 12px}.demo-page{padding:14px}.demo-page-head{flex-direction:column}.demo-metrics,.form-grid,.state-grid{grid-template-columns:1fr}.demo-toolbar{display:grid;grid-template-columns:1fr}.demo-toolbar .cui-field{min-width:0}.demo-top-actions .density-control{display:none}}
'''

html = '''<!doctype html>
<html lang="en" data-theme="light" data-density="compact">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Phase 3 — Core Component System</title><style>__BASE_CSS__\n__EXTRA_CSS__</style></head>
<body>
<div class="demo-shell">
<aside class="demo-sidebar">
  <div class="demo-brand"><div class="demo-mark">UI</div><div><div class="demo-brand-title">NiceGUI Base</div><div class="demo-caption">Phase 3 · v0.4.0</div></div></div>
  <div class="demo-nav-label">Review</div><nav class="demo-nav">
    <a href="#application" class="active">A <span>Real-world application</span></a>
    <a href="#forms">F <span>Forms & inputs</span></a>
    <a href="#states">S <span>Status & surfaces</span></a>
    <a href="#matrix">M <span>Component matrix</span></a>
  </nav>
</aside>
<main class="demo-main">
  <header class="demo-topbar"><div class="demo-top-title">Equipment Intelligence <span class="cui-badge cui-badge--neutral cui-badge--subtle" style="margin-left:8px">PROD</span></div>
    <div class="demo-top-actions">
      <div class="density-control" aria-label="Density"><button data-density-btn="comfortable">Comfort</button><button data-density-btn="compact" class="active">Compact</button><button data-density-btn="dense">Dense</button></div>
      <div class="theme-control" aria-label="Theme"><button data-theme-btn="light" class="active">Light</button><button data-theme-btn="dark">Dark</button><button data-theme-btn="system">System</button></div>
    </div>
  </header>
  <div class="demo-page">
    <section id="application" class="demo-page-head">
      <div><div class="demo-page-title">Core Component System</div><div class="demo-page-sub">A realistic equipment-health screen assembled from the approved design kernel, layout grammar, and Phase 3 component contracts. Tables/charts remain placeholders until their dedicated phases.</div></div>
      <div class="row"><button class="cui-button cui-button--secondary cui-control--medium">Export</button><button class="cui-button cui-button--primary cui-control--medium">Run analysis</button></div>
    </section>

    <section class="demo-section">
      <div class="demo-section-head"><div class="demo-section-title">Search & filter toolbar</div><div class="demo-section-note">Inputs share one field anatomy and density system</div></div>
      <div class="cui-surface cui-surface--panel demo-panel demo-toolbar">
        <div class="cui-field search"><div class="cui-field-label">Search</div><div class="cui-field-control cui-control--medium"><span class="cui-field-leading">⌕</span><input class="demo-input" placeholder="Tool, chamber, lot, recipe…"><span class="kbd">/</span></div></div>
        <div class="cui-field"><div class="cui-field-label">Area</div><div class="cui-field-control cui-control--medium"><select class="demo-input demo-select"><option>ETCH</option><option>CVD</option><option>DIFF</option></select></div></div>
        <div class="cui-field"><div class="cui-field-label">Status</div><div class="cui-field-control cui-control--medium"><select class="demo-input demo-select"><option>All active</option><option>Watch</option><option>Critical</option></select></div></div>
        <div><button class="cui-button cui-button--secondary cui-control--medium">Clear</button></div>
        <div><button class="cui-button cui-button--primary cui-control--medium">Apply</button></div>
      </div>
    </section>

    <section class="demo-section">
      <div class="demo-section-head"><div class="demo-section-title">Operational overview</div><div class="demo-section-note">Semantic status, no decorative color dependence</div></div>
      <div class="demo-metrics">
        <div class="cui-surface cui-surface--panel metric"><div class="metric-label">Active tools</div><div class="metric-value">184</div><div class="metric-foot"><span class="cui-semantic-indicator cui-semantic-indicator--success">Nominal</span><span>99.2%</span></div></div>
        <div class="cui-surface cui-surface--panel metric"><div class="metric-label">Watch</div><div class="metric-value">12</div><div class="metric-foot"><span class="cui-badge cui-badge--warning cui-badge--subtle">Watch</span><span>+3 today</span></div></div>
        <div class="cui-surface cui-surface--panel metric"><div class="metric-label">Critical</div><div class="metric-value">3</div><div class="metric-foot"><span class="cui-badge cui-badge--danger cui-badge--subtle">Critical</span><span>Needs review</span></div></div>
        <div class="cui-surface cui-surface--panel metric"><div class="metric-label">Data freshness</div><div class="metric-value">42s</div><div class="metric-foot"><span class="cui-semantic-indicator cui-semantic-indicator--neutral">Updated 42 sec ago</span><span class="cui-badge cui-badge--success cui-badge--subtle">Complete</span></div></div>
      </div>
    </section>

    <section class="demo-grid">
      <div class="cui-surface cui-surface--panel demo-panel"><div class="demo-section-title">Affected equipment</div><div class="demo-caption" style="margin:2px 0 10px">Table appearance is intentionally placeholder-only until Phase 5.</div>
        <table class="preview-table"><thead><tr><th>Tool</th><th>Chamber</th><th>State</th><th>Signal</th></tr></thead><tbody>
          <tr><td>ETCH-021</td><td>B</td><td><span class="cui-badge cui-badge--danger cui-badge--subtle">Critical</span></td><td>CD drift</td></tr>
          <tr><td>ETCH-087</td><td>A</td><td><span class="cui-badge cui-badge--warning cui-badge--subtle">Watch</span></td><td>APC variance</td></tr>
          <tr><td>ETCH-043</td><td>D</td><td><span class="cui-badge cui-badge--info cui-badge--subtle">Review</span></td><td>Pressure</td></tr>
        </tbody></table>
      </div>
      <div class="stack">
        <div class="cui-surface cui-surface--interactive is-interactive demo-card"><div class="row" style="justify-content:space-between"><b style="font-size:13px">ETCH-021 · Chamber B</b><span class="cui-badge cui-badge--danger cui-badge--subtle">Critical</span></div><div class="demo-caption" style="margin-top:6px">Highest excursion contribution in current context.</div><div class="row" style="margin-top:10px"><span class="cui-chip is-selected">CD drift</span><span class="cui-chip">Recipe R913</span><span class="cui-chip">18 lots</span></div></div>
        <div class="cui-collapsible collapse open"><button class="cui-collapsible__header" onclick="toggleCollapse(this)"><span>Advanced context</span><span class="chev">›</span></button><div class="cui-collapsible__body collapse-body"><div class="demo-caption">Expandable surfaces use the same border, radius, hover, and motion language as the rest of the system.</div></div></div>
      </div>
    </section>

    <section id="forms" class="demo-section">
      <div class="demo-section-head"><div class="demo-section-title">Record creation & engineering inputs</div><div class="demo-section-note">Representative form using standard field anatomy</div></div>
      <div class="cui-surface cui-surface--card demo-panel">
        <div class="form-grid">
          <div class="cui-field"><div class="cui-field-label">Investigation title <span class="cui-field-required">*</span></div><div class="cui-field-control cui-control--medium"><input class="demo-input" value="ETCH chamber excursion review"></div><div class="cui-field-description">Use a concise, searchable description.</div></div>
          <div class="cui-field"><div class="cui-field-label">Owner</div><div class="cui-field-control cui-control--medium"><select class="demo-input demo-select"><option>Process Engineering</option><option>Equipment Engineering</option></select></div></div>
          <div class="cui-field"><div class="cui-field-label">Trigger threshold</div><div class="cui-field-control cui-control--medium"><input class="demo-input" type="number" value="2.5"><span class="cui-field-unit">σ</span></div><div class="cui-field-description">Normalized standard-deviation threshold.</div></div>
          <div class="cui-field"><div class="cui-field-label">Analysis period</div><div class="row"><div class="cui-field-control cui-control--medium"><input class="demo-input" type="date" value="2026-08-18"></div><span class="demo-caption">to</span><div class="cui-field-control cui-control--medium"><input class="demo-input" type="date" value="2026-08-25"></div></div></div>
          <div class="cui-field full"><div class="cui-field-label">Notes</div><div class="cui-field-control"><textarea class="demo-input" rows="4" placeholder="Context, suspected mechanism, follow-up…"></textarea></div></div>
          <div class="cui-field"><div class="cui-field-label">Required example</div><div class="cui-field-control cui-field-control--error cui-control--medium"><input class="demo-input" placeholder="Required value"></div><div class="cui-field-error">A value is required before saving.</div></div>
          <div class="cui-field"><div class="cui-field-label">Read-only example</div><div class="cui-field-control cui-field-control--readonly cui-control--medium"><input class="demo-input" value="Automatically assigned" readonly></div><div class="cui-field-description">Read-only is visually distinct from disabled.</div></div>
          <div class="full"><div class="cui-upload upload-demo" onclick="document.getElementById('file').click()"><input id="file" type="file"><div><div class="upload-icon">↑</div><div class="cui-upload__title">Attach supporting file</div><div class="cui-upload__help">Local validated upload · size/type limits belong to the component contract</div></div></div></div>
        </div>
        <div class="demo-actions"><button class="cui-button cui-button--ghost cui-control--medium">Cancel</button><button class="cui-button cui-button--secondary cui-control--medium">Save draft</button><button class="cui-button cui-button--primary cui-control--medium">Create investigation</button></div>
      </div>
    </section>

    <section id="states" class="demo-section">
      <div class="demo-section-head"><div class="demo-section-title">Settings, choices & control states</div><div class="demo-section-note">Immediate settings use switches; mutually exclusive modes use radio</div></div>
      <div class="demo-grid">
        <div class="cui-surface cui-surface--panel demo-panel stack">
          <div class="switch-demo"><div><div style="font-size:13px;font-weight:600">Automatic refresh</div><div class="choice-help">Update monitoring data every minute.</div></div><button class="switch-control" aria-checked="true" onclick="toggleSwitch(this)"><span class="cui-switch-track"><span class="cui-switch-thumb"></span></span></button></div>
          <hr class="cui-divider">
          <label class="choice-demo"><input type="checkbox" checked><div><div class="choice-copy">Include inactive chambers</div><div class="choice-help">Use in analysis results and filters.</div></div></label>
          <label class="choice-demo"><input type="checkbox"><div><div class="choice-copy">Show experimental metrics</div><div class="choice-help">Metrics may have partial historical coverage.</div></div></label>
          <hr class="cui-divider">
          <div class="label">Default workspace</div>
          <label class="choice-demo"><input type="radio" name="workspace" checked><div class="choice-copy">Analysis</div></label>
          <label class="choice-demo"><input type="radio" name="workspace"><div class="choice-copy">Monitoring</div></label>
        </div>
        <div class="cui-surface cui-surface--panel demo-panel stack">
          <div class="cui-field"><div class="cui-field-label">Excursion sensitivity</div><input class="cui-slider" type="range" min="1" max="5" step=".1" value="2.5"><div class="cui-slider-meta"><span>1.0σ</span><span>2.5σ</span><span>5.0σ</span></div></div>
          <div><div class="label">Data quality</div><div class="row"><span class="cui-badge cui-badge--success cui-badge--subtle">Complete</span><span class="cui-badge cui-badge--warning cui-badge--subtle">Partial</span><span class="cui-badge cui-badge--info cui-badge--subtle">Estimated</span><span class="cui-badge cui-badge--danger cui-badge--subtle">Unavailable</span></div></div>
          <div><div class="label">Filter chips</div><div class="row"><button class="cui-chip is-selected" onclick="this.classList.toggle('is-selected')">ETCH</button><button class="cui-chip" onclick="this.classList.toggle('is-selected')">Watch</button><button class="cui-chip" onclick="this.classList.toggle('is-selected')">7 days</button><span class="cui-count-badge">12</span></div></div>
        </div>
      </div>
    </section>

    <section id="matrix" class="demo-section">
      <div class="demo-section-head"><div class="demo-section-title">All-state component matrix</div><div class="demo-section-note">Use this to judge visual consistency, not business content</div></div>
      <div class="demo-matrix">
        <div class="cui-surface cui-surface--panel matrix-panel stack"><div><div class="label">Button hierarchy</div><div class="row"><button class="cui-button cui-button--primary cui-control--medium">Primary</button><button class="cui-button cui-button--secondary cui-control--medium">Secondary</button><button class="cui-button cui-button--tertiary cui-control--medium">Tertiary</button><button class="cui-button cui-button--ghost cui-control--medium">Ghost</button><button class="cui-button cui-button--danger cui-control--medium">Danger</button></div></div><hr class="cui-divider"><div><div class="label">States</div><div class="row"><button class="cui-button cui-button--primary cui-control--medium is-loading">Running</button><button class="cui-button cui-button--secondary cui-control--medium" disabled>Disabled</button><button class="cui-icon-button cui-icon-button--secondary" aria-label="Icon action">•••</button><button class="cui-icon-button cui-icon-button--ghost is-selected" aria-label="Selected icon action">★</button></div></div></div>
        <div class="cui-surface cui-surface--panel matrix-panel stack"><div><div class="label">Semantic badges</div><div class="row"><span class="cui-badge cui-badge--neutral cui-badge--subtle">Neutral</span><span class="cui-badge cui-badge--info cui-badge--subtle">Info</span><span class="cui-badge cui-badge--success cui-badge--subtle">Success</span><span class="cui-badge cui-badge--warning cui-badge--subtle">Warning</span><span class="cui-badge cui-badge--danger cui-badge--subtle">Critical</span></div></div><hr class="cui-divider"><div><div class="label">Semantic indicators</div><div class="row"><span class="cui-semantic-indicator cui-semantic-indicator--success">Nominal</span><span class="cui-semantic-indicator cui-semantic-indicator--warning">Stale</span><span class="cui-semantic-indicator cui-semantic-indicator--danger">Critical</span></div></div></div>
        <div class="cui-surface cui-surface--panel matrix-panel"><div class="label">Surface hierarchy</div><div class="state-grid"><div class="cui-surface cui-surface--panel state-cell">Panel</div><div class="cui-surface cui-surface--card state-cell">Card</div><div class="cui-surface cui-surface--well state-cell">Well</div><div class="cui-surface cui-surface--interactive is-interactive state-cell">Interactive</div><div class="cui-surface cui-surface--interactive is-interactive is-selected state-cell">Selected</div><div class="cui-surface cui-surface--outlined state-cell">Outlined</div></div></div>
        <div class="cui-surface cui-surface--panel matrix-panel stack"><div class="label">Field states</div><div class="cui-field"><div class="cui-field-label">Default</div><div class="cui-field-control cui-control--medium"><input class="demo-input" value="ETCH-021"></div></div><div class="cui-field"><div class="cui-field-label">Error</div><div class="cui-field-control cui-field-control--error cui-control--medium"><input class="demo-input" value=""></div><div class="cui-field-error">This field is required.</div></div><div class="cui-field"><div class="cui-field-label">Disabled</div><div class="cui-field-control is-disabled cui-control--medium"><input class="demo-input" value="Unavailable" disabled></div></div></div>
      </div>
    </section>

    <section class="cui-surface cui-surface--well demo-panel"><div class="demo-section-title">Phase 3 approval focus</div><div class="demo-caption" style="margin-top:5px">Judge component anatomy, control height, hierarchy, field spacing, focus/error/disabled states, surfaces, semantic status language, density behavior, and light/dark consistency. Table and chart internals are deliberately not finalized in this phase.</div></section>
  </div>
</main>
</div>
<script>
const root=document.documentElement;
function applyTheme(mode){root.dataset.theme=mode;document.querySelectorAll('[data-theme-btn]').forEach(b=>b.classList.toggle('active',b.dataset.themeBtn===mode));localStorage.setItem('cui-p3-theme',mode)}
function applyDensity(mode){root.dataset.density=mode;document.querySelectorAll('[data-density-btn]').forEach(b=>b.classList.toggle('active',b.dataset.densityBtn===mode));localStorage.setItem('cui-p3-density',mode)}
document.querySelectorAll('[data-theme-btn]').forEach(b=>b.onclick=()=>applyTheme(b.dataset.themeBtn));document.querySelectorAll('[data-density-btn]').forEach(b=>b.onclick=()=>applyDensity(b.dataset.densityBtn));
applyTheme(localStorage.getItem('cui-p3-theme')||'light');applyDensity(localStorage.getItem('cui-p3-density')||'compact');
function toggleSwitch(b){const v=b.getAttribute('aria-checked')!=='true';b.setAttribute('aria-checked',String(v))}
function toggleCollapse(b){b.closest('.collapse').classList.toggle('open')}
</script></body></html>'''

html = html.replace('__BASE_CSS__', base_css).replace('__EXTRA_CSS__', extra_css)
out = ROOT / 'showcase' / 'phase_3_components_showcase.html'
out.write_text(html, encoding='utf-8')
print(out)

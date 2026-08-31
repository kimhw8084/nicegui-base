def build_visualization_css() -> str:
    return r'''
.cui-chart-panel {
  position: relative; min-width: 0; overflow: hidden;
  background: var(--cui-surface); border: 1px solid var(--cui-border-subtle);
  border-radius: var(--cui-radius-lg); color: var(--cui-text-primary);
}
.cui-chart-panel__header { display:flex; align-items:flex-start; justify-content:space-between; gap:var(--cui-space-3); padding:var(--cui-space-4) var(--cui-space-4) var(--cui-space-2); }
.cui-chart-panel__title { font-size:var(--cui-type-subheading-size); line-height:var(--cui-type-subheading-line); font-weight:var(--cui-type-subheading-weight); }
.cui-chart-panel__description { margin-top:2px; color:var(--cui-text-tertiary); font-size:var(--cui-type-caption-size); line-height:var(--cui-type-caption-line); }
.cui-chart-panel__body { min-width:0; padding:0 var(--cui-space-2) var(--cui-space-3); }
.cui-chart-a11y{position:absolute!important;width:1px!important;height:1px!important;padding:0!important;margin:-1px!important;overflow:hidden!important;clip:rect(0,0,0,0)!important;white-space:normal!important;border:0!important}
.cui-chart-panel--compact .cui-chart-canvas { height:220px; }
.cui-chart-panel--standard .cui-chart-canvas { height:320px; }
.cui-chart-panel--large .cui-chart-canvas { height:440px; }
.cui-chart-panel--workspace .cui-chart-canvas { height:min(68vh,720px); min-height:420px; }
.cui-chart-toolbar { display:flex; align-items:center; gap:var(--cui-space-1); color:var(--cui-text-secondary); }
.cui-chart-toolbar-host { margin-left:auto; flex:0 0 auto; }
.cui-chart-range-menu { width:min(330px,calc(100vw - 32px)); padding:10px !important; }
.cui-chart-range-menu__title { padding:3px 6px 0; font-size:var(--cui-font-size-12); line-height:var(--cui-line-height-18); font-weight:var(--cui-font-weight-720); color:var(--cui-text-primary); }
.cui-chart-range-menu__help { padding:2px 6px 9px; font-size:var(--cui-font-size-10); line-height:var(--cui-line-height-15); color:var(--cui-text-tertiary); }
.cui-chart-range-row { min-height:38px; display:grid; grid-template-columns:minmax(0,1fr) 30px 30px 30px; align-items:center; column-gap:4px; padding:3px 5px; border-radius:var(--cui-radius-control); }
.cui-chart-range-row + .cui-chart-range-row { margin-top:2px; }
.cui-chart-range-row:hover { background:var(--cui-surface-secondary); }
.cui-chart-range-row__label { font-size:var(--cui-font-size-11); color:var(--cui-text-secondary); font-weight:var(--cui-font-weight-600); }
.cui-chart-range-row__button { width:30px !important; min-width:30px !important; height:30px !important; min-height:30px !important; }
.cui-chart-scale-band { display:grid; grid-template-columns:auto minmax(140px,1fr); gap:12px; align-items:center; margin:2px 14px 8px; min-height:32px; padding:6px 10px; border-radius:var(--cui-radius-control); background:var(--cui-surface-secondary); color:var(--cui-text-secondary); }
.cui-chart-scale-band__title { font-size:var(--cui-font-size-10); line-height:var(--cui-line-height-16); font-weight:var(--cui-font-weight-650); white-space:nowrap; }
.cui-chart-scale-band__scale { display:grid; grid-template-columns:auto minmax(96px,210px) auto; align-items:center; justify-content:end; gap:8px; }
.cui-chart-scale-band__gradient { height:8px; border-radius:var(--cui-radius-pill); background:linear-gradient(90deg,#E9F2FF 0%,#A9CFFF 25%,#5B9EFF 50%,#246DCE 75%,#183E76 100%); box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--cui-border-default) 58%,transparent); }
.cui-chart-scale-band__value { font:var(--cui-font-weight-600) var(--cui-font-size-10)/var(--cui-line-height-14) ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; color:var(--cui-text-tertiary); font-variant-numeric:tabular-nums; }
.cui-chart-data-dialog { width:min(820px,92vw); max-height:82vh; }
.cui-chart-data-table-wrap { max-height:58vh; overflow:auto; border:1px solid var(--cui-border-subtle); border-radius:var(--cui-radius-md); }
.cui-chart-data-table { width:100%; border-collapse:collapse; font-size:var(--cui-type-body-size); }
.cui-chart-data-table th,.cui-chart-data-table td { padding:var(--cui-space-2) var(--cui-space-3); border-bottom:1px solid var(--cui-border-subtle); text-align:left; vertical-align:top; }
.cui-chart-data-table th { position:sticky; top:0; z-index:1; background:var(--cui-surface-secondary); color:var(--cui-text-secondary); font-weight:var(--cui-font-weight-600); }
.cui-chart-state { min-height:220px; display:grid; place-items:center; padding:var(--cui-space-6); color:var(--cui-text-secondary); text-align:center; }
.cui-chart-legend { display:flex; flex-wrap:wrap; gap:var(--cui-space-3); color:var(--cui-text-secondary); font-size:var(--cui-type-caption-size); }
.cui-chart-legend__item { display:inline-flex; gap:var(--cui-space-1); align-items:center; }
.cui-chart-legend__marker { width:8px; height:8px; border-radius:var(--cui-radius-pill); }
.cui-chart-selected { box-shadow: inset 0 0 0 2px var(--cui-accent); }
.cui-wafer-frame { aspect-ratio:1; border-radius:var(--cui-radius-circle); border:1px solid var(--cui-border-default); background:var(--cui-surface-secondary); overflow:hidden; }
.cui-chart-panel:focus-within { border-color:color-mix(in srgb,var(--cui-accent) 45%,var(--cui-border-default)); }
@media (max-width: 600px) {
  .cui-chart-panel__header { padding:var(--cui-space-3); }
  .cui-chart-panel__body { padding:0 var(--cui-space-1) var(--cui-space-2); }
  .cui-chart-panel--standard .cui-chart-canvas, .cui-chart-panel--large .cui-chart-canvas { height:280px; }
  .cui-chart-panel--workspace .cui-chart-canvas { height:58vh; min-height:320px; }
  .cui-chart-scale-band { grid-template-columns:1fr; gap:3px; margin-inline:6px; }
  .cui-chart-scale-band__scale { justify-content:stretch; grid-template-columns:auto 1fr auto; }
}
'''.strip() + '\n'

__all__=['build_visualization_css']

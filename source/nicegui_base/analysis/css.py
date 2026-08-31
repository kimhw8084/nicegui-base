def build_analysis_css() -> str:
    return r'''
.cui-analytical-panel{display:flex;flex-direction:column;min-width:0;min-height:0;border:1px solid var(--cui-border-default);border-radius:var(--cui-radius-lg);background:var(--cui-surface);overflow:hidden}
.cui-analytical-panel__header{display:flex;align-items:center;gap:var(--cui-space-2);padding:var(--cui-space-3) var(--cui-space-4);border-bottom:1px solid var(--cui-border-subtle);min-height:48px}
.cui-analytical-panel__title{font-weight:var(--cui-font-weight-650);min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cui-analytical-panel__status{font-size:var(--cui-type-caption-size);color:var(--cui-text-secondary);margin-left:auto}
.cui-analytical-panel__actions{display:flex;align-items:center;gap:var(--cui-space-1)}
.cui-analytical-panel__body{position:relative;flex:1;min-height:120px;padding:var(--cui-space-4);overflow:auto}
.cui-analytical-panel[data-status="loading"] .cui-analytical-panel__body{opacity:.62;pointer-events:none}
.cui-analytical-panel[data-status="error"]{border-color:var(--cui-danger)}
.cui-analytical-panel[data-status="stale"] .cui-analytical-panel__status{font-weight:var(--cui-font-weight-650)}
.cui-workspace-grid{--cui-workspace-columns:12;display:grid;grid-template-columns:repeat(var(--cui-workspace-columns,12),minmax(0,1fr));grid-auto-rows:44px;gap:var(--cui-space-3);align-items:stretch}
.cui-workspace-panel{min-width:0;min-height:0;overflow:hidden;border:1px solid var(--cui-border-default);border-radius:var(--cui-radius-lg);background:var(--cui-surface);display:flex;flex-direction:column}
.cui-workspace-panel[hidden]{display:none!important}
.cui-workspace-panel__chrome{display:flex;align-items:center;gap:var(--cui-space-1);padding:var(--cui-space-2) var(--cui-space-3);border-bottom:1px solid var(--cui-border-subtle);cursor:grab;user-select:none}
.cui-workspace-panel__chrome:active{cursor:grabbing}
.cui-workspace-panel__title{font-weight:var(--cui-font-weight-650);min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cui-workspace-panel__spacer{flex:1}
.cui-workspace-panel__body{flex:1;min-height:0;overflow:auto;padding:var(--cui-space-3)}
.cui-workspace-panel[data-collapsed="true"] .cui-workspace-panel__body{display:none}
.cui-workspace-panel[data-collapsed="true"]{min-height:44px}
.cui-workspace-panel[data-locked="true"] .cui-workspace-panel__chrome{cursor:default}
.cui-workspace-panel.is-drag-over{outline:2px solid var(--cui-accent);outline-offset:2px}
'''

__all__=['build_analysis_css']

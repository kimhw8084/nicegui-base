from __future__ import annotations

WORKBENCH_CSS = r'''
.cui-workbench-page{
  --cui-wb-surface:var(--cui-surface);
  --cui-wb-surface-subtle:var(--cui-surface-secondary);
  --cui-wb-border:var(--cui-border-default);
  --cui-wb-text:var(--cui-text-primary);
  --cui-wb-muted:var(--cui-text-secondary);
  --cui-wb-preview:var(--cui-page);
  color:var(--cui-wb-text);
  color-scheme:inherit;
}
body.body--dark .cui-workbench-page,.q-dark .cui-workbench-page{
  --cui-wb-surface:var(--cui-surface);
  --cui-wb-surface-subtle:var(--cui-surface-secondary);
  --cui-wb-border:var(--cui-border-default);
  --cui-wb-text:var(--cui-text-primary);
  --cui-wb-muted:var(--cui-text-secondary);
  --cui-wb-preview:var(--cui-page);
  color:var(--cui-wb-text);
  color-scheme:inherit;
}
.cui-workbench-page{max-width:1600px;margin:0 auto;padding:28px 30px 56px;width:100%;}
.cui-workbench-hero{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(280px,.7fr);gap:24px;padding:28px;border:1px solid var(--cui-wb-border);border-radius:var(--cui-radius-overlay);background:var(--cui-wb-surface);}
.cui-workbench-eyebrow{font-size:var(--cui-font-size-12);font-weight:var(--cui-font-weight-700);letter-spacing:.08em;text-transform:uppercase;opacity:.68;}
.cui-workbench-title{font-size:var(--cui-font-size-34);font-weight:var(--cui-font-weight-750);line-height:var(--cui-line-height-ratio-1_12);letter-spacing:-.025em;margin-top:6px;}
.cui-workbench-subtitle{font-size:var(--cui-font-size-15);line-height:var(--cui-line-height-ratio-1_5);max-width:780px;opacity:.76;margin-top:8px;}
.cui-workbench-search{margin-top:20px;max-width:760px;width:100%;}
.cui-workbench-kpis{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;align-content:start;}
.cui-workbench-kpi{padding:14px 16px;border-radius:var(--cui-radius-control);border:1px solid var(--cui-wb-border);background:var(--cui-wb-surface-subtle);}
.cui-workbench-kpi strong{display:block;font-size:var(--cui-font-size-24);line-height:var(--cui-line-height-ratio-1_12)}.cui-workbench-kpi span{font-size:var(--cui-font-size-12);opacity:.68}
.cui-workbench-section{margin-top:30px}.cui-workbench-section-head{display:flex;align-items:end;justify-content:space-between;gap:16px;margin-bottom:12px}
.cui-workbench-section-title{font-size:var(--cui-font-size-20);font-weight:var(--cui-font-weight-720)}.cui-workbench-section-copy{font-size:var(--cui-font-size-13);opacity:.68;max-width:760px}
.cui-workbench-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.cui-workbench-grid--3{grid-template-columns:repeat(3,minmax(0,1fr))}
.cui-workbench-card{display:flex;flex-direction:column;gap:8px;min-height:150px;padding:16px;border:1px solid var(--cui-wb-border);border-radius:var(--cui-radius-surface);background:var(--cui-wb-surface);transition:border-color var(--cui-duration-fast) var(--cui-easing-native),transform var(--cui-duration-fast) var(--cui-easing-native);cursor:pointer}
.cui-workbench-card:hover{transform:translateY(-1px);border-color:var(--cui-accent)}
.cui-workbench-card:focus-visible{outline:var(--cui-state-focus-width) solid var(--cui-accent);outline-offset:var(--cui-state-focus-offset);border-color:var(--cui-accent)}
.cui-workbench-card__meta{display:flex;align-items:center;gap:7px;flex-wrap:wrap;font-size:var(--cui-font-size-11);font-weight:var(--cui-font-weight-650);text-transform:uppercase;letter-spacing:.04em;opacity:.64}
.cui-workbench-card__title{font-size:var(--cui-font-size-15);font-weight:var(--cui-font-weight-700);line-height:var(--cui-line-height-ratio-1_3)}.cui-workbench-card__body{font-size:var(--cui-font-size-13);line-height:var(--cui-line-height-ratio-1_5);opacity:.75}
.cui-workbench-chiprow{display:flex;gap:6px;flex-wrap:wrap;margin-top:auto}.cui-workbench-chip{font-size:var(--cui-font-size-11);padding:3px 7px;border:1px solid var(--cui-wb-border);border-radius:var(--cui-radius-pill);background:var(--cui-wb-surface-subtle);color:var(--cui-wb-text);line-height:var(--cui-line-height-ratio-1_35);}
.cui-workbench-catalog-results{display:flex;flex-direction:column;gap:4px}.cui-workbench-toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px}.cui-workbench-toolbar .q-field{min-width:240px}
.cui-workbench-command-trigger{align-self:flex-start;margin:4px 0 8px}.cui-workbench-command-shortcut{font-size:var(--cui-font-size-10);opacity:.62;margin-left:6px}
.cui-workbench-display-controls{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:4px 0 10px;padding:8px 10px;border:1px solid var(--cui-wb-border);border-radius:var(--cui-radius-control);background:var(--cui-wb-surface-subtle)}.cui-workbench-display-controls__label{font-size:var(--cui-font-size-11);font-weight:var(--cui-font-weight-700);letter-spacing:.03em;opacity:.68}.cui-workbench-display-controls__label:not(:first-child){margin-left:4px}
.cui-workbench-preview{padding:18px;border:1px solid var(--cui-wb-border);border-radius:var(--cui-radius-surface);background:var(--cui-wb-surface);min-height:300px}
.cui-workbench-two{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(280px,.7fr);gap:18px}
.cui-workbench-list{display:flex;flex-direction:column;gap:12px}.cui-workbench-search-group{display:flex;flex-direction:column;gap:8px}.cui-workbench-search-group__title{font-size:var(--cui-font-size-11);font-weight:var(--cui-font-weight-750);text-transform:uppercase;letter-spacing:.06em;opacity:.62}.cui-workbench-note{font-size:var(--cui-font-size-12);line-height:var(--cui-line-height-ratio-1_5);opacity:.7}
.cui-workbench-preview-title{font-size:var(--cui-font-size-14);font-weight:var(--cui-font-weight-700);margin-bottom:8px}.cui-workbench-preview-caption{font-size:var(--cui-font-size-11);line-height:var(--cui-line-height-ratio-1_45);opacity:.65;margin-top:10px}.cui-workbench-preview-empty{display:flex;align-items:center;justify-content:center;min-height:110px;border:1px dashed var(--cui-wb-border);border-radius:var(--cui-radius-control);font-size:var(--cui-font-size-12);opacity:.62}.cui-workbench-mini-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.cui-workbench-mini-grid--strip{grid-template-columns:repeat(5,minmax(110px,1fr));overflow-x:auto}.cui-workbench-mini-panel{min-width:0;overflow:hidden}.cui-workbench-flow{display:flex;align-items:stretch;gap:8px;overflow-x:auto;padding:8px 2px}.cui-workbench-flow__node{min-width:128px;flex:1;padding:12px;border:1px solid var(--cui-wb-border);border-radius:var(--cui-radius-control);background:var(--cui-wb-surface-subtle)}.cui-workbench-flow__title{font-size:var(--cui-font-size-13);font-weight:var(--cui-font-weight-700)}.cui-workbench-flow__arrow{display:flex;align-items:center;font-size:var(--cui-font-size-20);opacity:.5}.cui-workbench-tree{display:flex;flex-direction:column;gap:10px}.cui-workbench-tree__root{align-self:flex-start;padding:8px 12px;border-radius:var(--cui-radius-control);background:var(--cui-wb-surface-subtle);font-size:var(--cui-font-size-13);font-weight:var(--cui-font-weight-700)}.cui-workbench-tree__branches{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.cui-workbench-tree__branch{padding:10px;border-left:2px solid var(--cui-wb-border);background:var(--cui-wb-surface-subtle);border-radius:0 var(--cui-radius-control) var(--cui-radius-control) 0}.cui-workbench-tree__branch-title{font-size:var(--cui-font-size-12);font-weight:var(--cui-font-weight-700);margin-bottom:5px}.cui-workbench-tree__leaf{font-size:var(--cui-font-size-11);line-height:var(--cui-line-height-ratio-1_45);opacity:.72}.cui-workbench-recipe-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:12px}.cui-workbench-recipe-panel{display:flex;flex-direction:column;gap:8px;min-width:0;padding:14px;border:1px solid var(--cui-wb-border);border-radius:var(--cui-radius-control);background:var(--cui-wb-surface)}.cui-workbench-panel-preview{min-height:128px;min-width:0;overflow:hidden}.cui-workbench-panel-actions{display:flex;gap:6px;flex-wrap:wrap;margin-top:auto}.cui-workbench-records{display:flex;flex-direction:column;border:1px solid var(--cui-wb-border);border-radius:var(--cui-radius-control);overflow:hidden}.cui-workbench-records__row{display:grid;grid-template-columns:.8fr .6fr 1.4fr .7fr .7fr;gap:6px;padding:7px 9px;border-top:1px solid var(--cui-wb-border);font-size:var(--cui-font-size-10)}.cui-workbench-records__row:first-child{border-top:0}.cui-workbench-records__head{font-weight:var(--cui-font-weight-700);background:var(--cui-wb-surface-subtle)}.cui-workbench-property-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.cui-workbench-property-grid__item{padding:10px;border:1px solid var(--cui-wb-border);border-radius:var(--cui-radius-control);background:var(--cui-wb-surface-subtle)}
.cui-workbench-not-found{display:flex;flex-direction:column;align-items:flex-start;gap:12px;min-height:180px}.cui-workbench-quality-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.cui-workbench-quality-card{padding:16px;border:1px solid var(--cui-wb-border);border-radius:var(--cui-radius-control);background:var(--cui-wb-surface)}.cui-workbench-quality-row{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:9px}

.cui-studio-header{display:flex;flex-direction:column;gap:8px;padding:18px;margin-bottom:14px;border:1px solid var(--cui-wb-border);border-radius:var(--cui-radius-surface);background:var(--cui-wb-surface)}
.cui-studio-preview-frame{width:100%;margin:12px auto;padding:14px;border:1px solid var(--cui-wb-border);border-radius:var(--cui-radius-control);background:var(--cui-wb-surface);transition:max-width var(--cui-duration-fast) var(--cui-easing-native)}
.cui-studio-preview-controls{align-items:flex-end}.cui-studio-iframe{display:block;width:100%;height:560px;border:1px solid var(--cui-wb-border);border-radius:var(--cui-radius-control);background:var(--cui-wb-surface)}
.cui-studio-event-log{margin-top:12px;padding:9px 11px;border:1px solid var(--cui-wb-border);border-radius:var(--cui-radius-control);background:var(--cui-wb-surface-subtle)}.cui-studio-event-log summary{cursor:pointer;font-weight:var(--cui-font-weight-700)}.cui-studio-event-log__events{display:flex;flex-direction:column;gap:3px;padding-top:8px}
.cui-data-dock-content{display:flex;flex-direction:column;gap:12px;margin-top:12px}.cui-data-dock-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.cui-data-dock-issues{display:flex;flex-direction:column;gap:4px;padding:10px;border-left:3px solid var(--cui-warning,#d18b00);background:var(--cui-wb-surface-subtle)}
.cui-data-dock-column{display:grid;grid-template-columns:minmax(150px,.7fr) minmax(0,1.8fr);gap:8px 14px;padding:12px;border:1px solid var(--cui-wb-border);border-radius:var(--cui-radius-control)}.cui-data-dock-column__controls{grid-column:1/-1;display:grid;grid-template-columns:1.4fr 1fr 1fr auto;gap:8px;align-items:end}
.cui-recipe-mapping{display:flex;flex-direction:column;gap:10px}.cui-recipe-mapping__row{display:grid;grid-template-columns:minmax(150px,.7fr) minmax(0,1.2fr) minmax(220px,1fr);gap:8px 14px;align-items:end;padding:10px;border-bottom:1px solid var(--cui-wb-border)}.cui-recipe-panel-status{padding:10px 12px;border:1px solid var(--cui-wb-border);border-radius:var(--cui-radius-control)}.cui-recipe-panel-status.is-unavailable,.cui-workbench-recipe-panel.is-unavailable{opacity:.58;background:var(--cui-wb-surface-subtle)}
.cui-builder{display:flex;flex-direction:column;gap:16px}.cui-builder>.cui-segmented-control{align-self:flex-start}.cui-builder .cui-workbench-card{min-height:auto;cursor:default}.cui-workbench-disabled-state{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:14px;border:1px dashed var(--cui-wb-border);border-radius:var(--cui-radius-control)}
.cui-builder-review-data{min-width:0}.cui-builder-review-data>summary{cursor:pointer}.cui-builder-review-data__host{max-width:100%;max-height:360px;overflow:auto;margin-top:12px}.cui-provider-capability{min-width:0;max-width:100%;overflow:hidden}.cui-provider-capability .cui-catalog-specimen{min-width:0;max-width:100%}

.cui-workbench-kpi,.cui-workbench-card,.cui-workbench-quality-card,.cui-studio-header,.cui-studio-preview-frame{color:var(--cui-wb-text)}
.cui-workbench-subtitle,.cui-workbench-section-copy,.cui-workbench-card__meta,.cui-workbench-card__body,.cui-workbench-note,.cui-workbench-preview-caption,.cui-workbench-preview-empty{color:var(--cui-wb-muted);opacity:1}
.cui-studio-preview-frame[data-theme="light"]{
  --cui-wb-surface:#ffffff;
  --cui-wb-surface-subtle:#f5f7fa;
  --cui-wb-border:#d5dbe5;
  --cui-wb-text:#172033;
  --cui-wb-muted:#5d6878;
  --cui-wb-preview:#f8fafc;
  background:var(--cui-wb-preview);
  color:var(--cui-wb-text);
  color-scheme:light;
}
.cui-studio-preview-frame[data-theme="dark"]{
  --cui-wb-surface:#171c24;
  --cui-wb-surface-subtle:#202733;
  --cui-wb-border:#3a4555;
  --cui-wb-text:#f1f5f9;
  --cui-wb-muted:#aab5c5;
  --cui-wb-preview:#121720;
  background:var(--cui-wb-preview);
  color:var(--cui-wb-text);
  color-scheme:dark;
}
.cui-studio-preview-frame[data-theme="system"]{background:var(--cui-wb-preview)}
.cui-studio-preview-frame[data-specimen="runtime"],.cui-studio-preview-frame[data-specimen="security"],.cui-studio-preview-frame[data-specimen="performance"],.cui-studio-preview-frame[data-specimen="data"],.cui-studio-preview-frame[data-specimen="recipe"]{min-height:0}
.cui-studio-contract-specimen{display:flex;flex-direction:column;gap:8px;max-width:760px;padding:14px;border:1px solid var(--cui-wb-border);border-radius:var(--cui-radius-control);background:var(--cui-wb-surface)}
.cui-studio-contract-specimen__meta{display:flex;gap:6px;flex-wrap:wrap}
@media(max-width:1100px){.cui-workbench-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.cui-workbench-grid--3{grid-template-columns:repeat(2,minmax(0,1fr))}.cui-workbench-hero,.cui-workbench-two{grid-template-columns:1fr}.cui-workbench-not-found{display:flex;flex-direction:column;align-items:flex-start;gap:12px;min-height:180px}.cui-workbench-quality-grid{grid-template-columns:1fr}.cui-workbench-mini-grid{grid-template-columns:1fr}.cui-workbench-tree__branches{grid-template-columns:1fr}}
@media(max-width:820px){.cui-data-dock-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.cui-data-dock-column,.cui-recipe-mapping__row{grid-template-columns:1fr}.cui-data-dock-column__controls{grid-template-columns:1fr 1fr}.cui-studio-iframe{height:460px}}
@media(max-width:680px){.cui-workbench-display-controls{align-items:flex-start}.cui-workbench-page{padding:18px 14px 40px}.cui-workbench-grid,.cui-workbench-grid--3,.cui-workbench-recipe-grid{grid-template-columns:1fr}.cui-workbench-title{font-size:var(--cui-font-size-28)}.cui-workbench-records__row{grid-template-columns:1fr 1fr}.cui-workbench-flow{flex-direction:column}.cui-workbench-flow__arrow{transform:rotate(90deg);align-self:center}.cui-workbench-command-shortcut{display:none}}

/* NICEGUI BASE ITERATION 3 VISUAL CLOSURE V6 — WORKBENCH */
/* Six Builder stages stay visible without horizontal clipping at tablet/phone widths. */
@media(max-width:1100px){
  .cui-builder .cui-progress-steps{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:12px 10px!important;overflow:visible!important;width:100%!important;padding:2px 0!important;}
  .cui-builder .cui-progress-step{display:grid!important;grid-template-columns:28px minmax(0,1fr)!important;align-items:start!important;gap:7px!important;min-width:0!important;flex:none!important;width:auto!important;}
  .cui-builder .cui-progress-step:not(:last-child)::after{display:none!important;}
  .cui-builder .cui-progress-step__rail{width:28px!important;min-width:28px!important;}
  .cui-builder .cui-progress-step__copy{min-width:0!important;width:100%!important;}
  .cui-builder .cui-progress-step__label,.cui-builder .cui-progress-step__state{white-space:normal!important;overflow-wrap:normal!important;word-break:normal!important;line-height:var(--cui-line-height-ratio-1_25)!important;}
}
/* Studio tabs stay distinct and horizontally scrollable instead of compressing into one text run. */
@media(max-width:680px){
  .cui-studio-preview-frame + .cui-tabs-region{overflow:hidden!important;max-width:100%!important;}
  .cui-studio-preview-frame + .cui-tabs-region .q-tabs__content{justify-content:flex-start!important;overflow-x:auto!important;overflow-y:hidden!important;flex-wrap:nowrap!important;scrollbar-width:thin!important;}
  .cui-studio-preview-frame + .cui-tabs-region .cui-tab{flex:0 0 auto!important;min-width:max-content!important;padding-inline:12px!important;}
  .cui-studio-preview-frame + .cui-tabs-region .q-tab__label{white-space:nowrap!important;}
  /* Capability Studio renders the configured title and recipe title as adjacent direct-child section titles. */
  .cui-studio-preview-frame > .cui-workbench-section-title:first-child{margin:0 0 8px!important;line-height:var(--cui-line-height-ratio-1_35)!important;}
  .cui-studio-preview-frame > .cui-workbench-section-title:first-child + .cui-workbench-section-title{margin-top:0!important;}
}

/* NICEGUI BASE COMPONENT PREVIEW CLOSURE V1 */
.cui-component-specimen{display:grid;gap:12px;min-height:220px;width:100%}
.cui-component-specimen__intro{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.cui-component-specimen__stage{display:flex;align-items:center;justify-content:flex-start;min-height:150px;width:100%;padding:22px;border:1px dashed var(--cui-wb-border);border-radius:var(--cui-radius-control);background:var(--cui-wb-preview)}
.cui-component-specimen__demo{display:flex;flex-direction:column;align-items:flex-start;gap:14px;width:min(100%,760px)}
.cui-component-specimen__demo>.cui-field,.cui-component-specimen__demo>.cui-slider-field,.cui-component-specimen__demo>.cui-upload-shell,.cui-component-specimen__demo>.cui-choice-group{width:min(100%,620px)}
.cui-component-specimen__row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.cui-component-specimen__surface-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;width:100%}
.cui-component-specimen__surface-grid>section{min-width:0}
@media(max-width:680px){.cui-component-specimen__stage{padding:16px;min-height:130px}.cui-component-specimen__surface-grid{grid-template-columns:1fr}}

/* NiceGUI Base development D1 catalog specimens */
.cui-catalog-specimen{display:grid;gap:12px;width:100%;min-width:0;overflow-wrap:anywhere}
.cui-catalog-specimen>.cui-chart-panel,.cui-catalog-specimen>.cui-data-table{width:100%;min-width:0}
.cui-framework-specimen{display:grid;gap:12px;width:100%;min-width:0}
.cui-framework-specimen__stage,.cui-framework-specimen__demo{width:100%;min-width:0}
.cui-studio-preview-frame{min-height:160px!important;height:auto!important;overflow:hidden}
.cui-studio-code{min-width:0;max-width:100%;overflow-x:auto}
.cui-build-id{margin-inline-start:auto;font-variant-numeric:tabular-nums}
.cui-studio-preview-controls{flex-wrap:wrap}
@media(max-width:680px){.cui-build-id{margin-inline-start:0}.cui-catalog-specimen{max-width:100%}}

/* D6H.1 visual token teaching: the contract and its use stay together. */
.cui-d6c-token-family__body{display:grid;grid-template-columns:minmax(0,1fr);gap:var(--cui-gap-stack);align-items:start;min-width:0}
.cui-d6c-token-contract{min-width:0}
.cui-d6c-live-specimen{display:flex;flex-direction:column;gap:var(--cui-gap-cluster);min-width:0;padding:var(--cui-gap-content);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:var(--cui-surface-secondary)}
.cui-d6c-live-specimen__title,.cui-d6c-guidance-label{font-size:var(--cui-font-size-11);font-weight:var(--cui-font-weight-700);letter-spacing:.04em;text-transform:uppercase;color:var(--cui-text-secondary)}
.cui-d6c-api-row{display:flex;align-items:center;gap:var(--cui-gap-cluster);flex-wrap:wrap;min-width:0;padding-top:var(--cui-gap-control-content);border-top:1px solid var(--cui-border-subtle)}
.cui-d6c-api{flex:1 1 180px;min-width:0;padding:var(--cui-gap-control-content);border-radius:var(--cui-radius-control);background:var(--cui-surface);color:var(--cui-text-primary);font-size:var(--cui-font-size-11);overflow-wrap:anywhere}
.cui-d6c-guidance-row{display:flex;flex-direction:column;gap:var(--cui-gap-control-content)}
.cui-d6c-dont{font-size:var(--cui-font-size-11);color:var(--cui-text-secondary);opacity:.8}
.cui-d6c-spacing-demo,.cui-d6c-gap-demo,.cui-d6c-radius-demo,.cui-d6c-type-demo,.cui-d6c-border-demo,.cui-d6c-elevation-demo,.cui-d6c-density-demo,.cui-d6c-responsive-canvas,.cui-d6c-motion-demo,.cui-d6c-z-demo,.cui-d6c-state-demo{min-width:0}
.cui-d6c-spacing-demo{display:flex;flex-direction:column;gap:var(--cui-gap-section)}
.cui-d6c-spacing-block{padding:var(--cui-gap-control-content) var(--cui-gap-content);border-left:var(--cui-border-width-strong) solid var(--cui-accent);border-radius:var(--cui-radius-control);background:var(--cui-surface);color:var(--cui-text-primary)}
.cui-d6c-gap-demo{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--cui-gap-stack)}
.cui-d6c-gap-node{padding:var(--cui-gap-content);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:var(--cui-surface);color:var(--cui-text-primary)}
.cui-d6c-radius-demo{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--cui-gap-cluster)}
.cui-d6c-radius-sample{display:grid;place-items:center;min-height:var(--cui-control-height);padding:var(--cui-gap-control-content);border:1px solid var(--cui-border-subtle);background:var(--cui-surface);color:var(--cui-text-primary)}
.cui-d6c-type-demo{display:flex;flex-direction:column;gap:var(--cui-gap-control-content);padding:var(--cui-gap-content);border-left:var(--cui-border-width-strong) solid var(--cui-accent);background:var(--cui-surface);color:var(--cui-text-primary)}
.cui-d6c-type-display{font-size:var(--cui-font-size-24);font-weight:var(--cui-font-weight-750);line-height:var(--cui-line-height-ratio-1_12)}
.cui-d6c-type-heading{font-size:var(--cui-font-size-18);font-weight:var(--cui-font-weight-700)}
.cui-d6c-type-body{font-size:var(--cui-type-body-size);line-height:var(--cui-type-body-line)}
.cui-d6c-type-meta{font-size:var(--cui-font-size-11);color:var(--cui-text-secondary)}
.cui-d6c-border-demo{display:flex;flex-direction:column;gap:var(--cui-gap-stack)}
.cui-d6c-border-subtle,.cui-d6c-border-strong{padding:var(--cui-gap-content);background:var(--cui-surface);color:var(--cui-text-primary)}
.cui-d6c-border-subtle{border:var(--cui-border-width-subtle) solid var(--cui-border-subtle)}
.cui-d6c-border-strong{border:var(--cui-border-width-strong) solid var(--cui-border-strong)}
.cui-d6c-elevation-demo{display:flex;flex-direction:column;gap:var(--cui-gap-stack)}
.cui-d6c-elevation-demo>*{padding:var(--cui-gap-content);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:var(--cui-surface);color:var(--cui-text-primary)}
.cui-d6c-elevation-flat{box-shadow:none}.cui-d6c-elevation-raised{box-shadow:var(--cui-shadow-1)}.cui-d6c-elevation-overlay{box-shadow:var(--cui-shadow-2)}
.cui-d6c-density-demo{display:flex;flex-direction:column;gap:var(--cui-gap-control-content)}
.cui-d6c-density-row{display:flex;align-items:center;justify-content:space-between;gap:var(--cui-gap-cluster);padding:var(--cui-gap-control-content) var(--cui-gap-content);border-radius:var(--cui-radius-control);background:var(--cui-surface);color:var(--cui-text-primary)}
.cui-d6c-density-row:nth-child(2){padding-block:var(--cui-gap-control-content)}
.cui-d6c-density-row:nth-child(3){padding-block:var(--cui-space-1)}
.cui-d6c-responsive-canvas{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--cui-gap-cluster)}
.cui-d6c-mini-canvas{display:flex;flex-direction:column;gap:var(--cui-gap-control-content);min-height:108px;padding:var(--cui-gap-control-content);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:var(--cui-surface);color:var(--cui-text-primary)}
.cui-d6c-mini-canvas__label{font-size:var(--cui-font-size-11);font-weight:var(--cui-font-weight-700)}
.cui-d6c-mini-canvas__content{display:flex;gap:var(--cui-gap-control-content);min-height:0;flex:1}.cui-d6c-mini-slot{display:grid;place-items:center;flex:1;min-width:0;border-radius:var(--cui-radius-control);background:var(--cui-accent-soft);font-size:var(--cui-font-size-11);overflow-wrap:anywhere}
.cui-d6c-canvas--tablet .cui-d6c-mini-slot:last-child{flex:.7}.cui-d6c-canvas--phone .cui-d6c-mini-canvas__content{flex-direction:column}.cui-d6c-canvas--phone .cui-d6c-mini-slot:last-child{flex:.7}
.cui-d6c-motion-sample{display:grid;place-items:center;min-height:var(--cui-control-height);padding:var(--cui-gap-content);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:var(--cui-surface);color:var(--cui-text-primary);transition:transform var(--cui-duration-feedback) var(--cui-easing-native),background-color var(--cui-duration-feedback) var(--cui-easing-native)}
.cui-d6c-motion-sample:hover,.cui-d6c-motion-sample:focus-visible{transform:translateY(-1px);background:var(--cui-surface-hover)}
.cui-d6c-z-demo{position:relative;min-height:148px}.cui-d6c-z-layer{position:absolute;display:grid;place-items:center;width:72%;min-height:var(--cui-control-height);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:var(--cui-surface);color:var(--cui-text-primary);box-shadow:var(--cui-shadow-1)}
.cui-d6c-z-page{inset-inline-start:0;inset-block-start:0;z-index:var(--cui-layer-sticky)}.cui-d6c-z-popover{inset-inline-start:var(--cui-gap-content);inset-block-start:var(--cui-gap-content);z-index:var(--cui-local-popup-z)}.cui-d6c-z-modal{inset-inline-start:calc(var(--cui-gap-content) * 2);inset-block-start:calc(var(--cui-gap-content) * 2);z-index:var(--cui-modal-z)}.cui-d6c-z-toast{inset-inline-start:calc(var(--cui-gap-content) * 3);inset-block-start:calc(var(--cui-gap-content) * 3);z-index:var(--cui-toast-z)}
.cui-d6c-state-demo{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--cui-gap-control-content)}
.cui-d6c-state-sample{padding:var(--cui-gap-content);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:var(--cui-surface);color:var(--cui-text-primary)}
.cui-d6c-state-sample.is-hover{background:var(--cui-surface-hover)}.cui-d6c-state-sample.is-selected{background:var(--cui-accent-soft);box-shadow:inset 0 0 0 1px var(--cui-accent)}.cui-d6c-state-sample.is-disabled{opacity:var(--cui-state-disabled-opacity)}
.cui-d6c-palette-specimen{display:flex;flex-direction:column;gap:var(--cui-gap-cluster);margin-top:var(--cui-gap-stack);padding-top:var(--cui-gap-stack);border-top:1px solid var(--cui-border-subtle)}
.cui-d6c-palette-cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--cui-gap-cluster)}
.cui-d6c-palette-card{display:flex;flex-direction:column;gap:var(--cui-gap-control-content);min-height:var(--cui-control-height);padding:var(--cui-gap-content);border-radius:var(--cui-radius-control);color:var(--cui-text-primary)}
.cui-d6c-palette-page{background:var(--cui-page)}.cui-d6c-palette-surface{background:var(--cui-surface);border:1px solid var(--cui-border-subtle)}.cui-d6c-palette-status{background:var(--cui-success-soft)}
.cui-catalog-refine{margin-bottom:var(--cui-gap-stack);padding:var(--cui-gap-control-content) var(--cui-gap-content);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:var(--cui-surface-secondary)}
.cui-catalog-refine__summary{cursor:pointer;font-size:var(--cui-font-size-13);font-weight:var(--cui-font-weight-700);color:var(--cui-text-primary)}
.cui-catalog-refine__controls{display:flex;align-items:end;gap:var(--cui-gap-cluster);flex-wrap:wrap;padding-top:var(--cui-gap-content)}
.cui-catalog-refine__controls .q-field{min-width:200px;flex:1 1 200px}
.cui-full-application{min-width:0}.cui-full-application__identity{display:flex;align-items:center;gap:var(--cui-gap-cluster);flex-wrap:wrap;padding:var(--cui-gap-control-content) 0;border-bottom:1px solid var(--cui-border-subtle)}
.cui-full-application__question{font-size:var(--cui-font-size-15);font-weight:var(--cui-font-weight-650);color:var(--cui-text-primary)}
.cui-layout-live-composition{display:grid;gap:var(--cui-gap-stack);padding:var(--cui-gap-content);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-surface);background:var(--cui-surface-secondary);overflow:hidden}
.cui-layout-live-composition>.cui-page{min-width:0;max-width:100%;padding:0!important}
.cui-layout-live-composition .cui-page__header{display:none}
.cui-layout-mini-frame{display:grid;gap:var(--cui-gap-control-content);min-height:150px;padding:var(--cui-gap-content);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:var(--cui-surface);color:var(--cui-text-primary)}
.cui-layout-mini-frame__header{display:flex;justify-content:space-between;gap:var(--cui-gap-cluster);padding-bottom:var(--cui-gap-control-content);border-bottom:1px solid var(--cui-border-subtle);min-width:0}
.cui-layout-mini-frame__title{font-size:var(--cui-font-size-12);font-weight:var(--cui-font-weight-700)}.cui-layout-mini-frame__meta,.cui-layout-mini-slot__meta{font-size:var(--cui-font-size-11);color:var(--cui-text-secondary)}
.cui-layout-mini-frame__slots{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--cui-gap-control-content);min-width:0}
.cui-layout-mini-slot{display:grid;align-content:center;gap:2px;min-width:0;min-height:70px;padding:var(--cui-gap-control-content);border:1px dashed var(--cui-border-strong);border-radius:var(--cui-radius-control);background:var(--cui-accent-soft);overflow-wrap:anywhere}
.cui-layout-mini-slot__label{font-size:var(--cui-font-size-11);font-weight:var(--cui-font-weight-650)}
.cui-layout-catalog-miniatures{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--cui-gap-control-content);min-width:0}
.cui-layout-catalog-miniatures .cui-layout-mini-frame{min-height:104px;padding:var(--cui-gap-control-content);gap:var(--cui-gap-control-content)}
.cui-layout-catalog-miniatures .cui-layout-mini-frame__header{padding-bottom:var(--cui-gap-control-content)}
.cui-layout-catalog-miniatures .cui-layout-mini-frame__slots{grid-template-columns:1fr!important;gap:2px}
.cui-layout-catalog-miniatures .cui-layout-mini-slot{min-height:22px;padding:2px 4px}
.cui-layout-catalog-miniatures .cui-layout-mini-slot__label{font-size:var(--cui-font-size-10)}
.cui-workbench-ai-workflow{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--cui-gap-control-content);min-width:0}
.cui-workbench-ai-step{display:grid;gap:var(--cui-gap-control-content);min-width:0;padding:var(--cui-gap-content);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:var(--cui-surface-secondary)}
.cui-workbench-ai-step .cui-workbench-card__body{overflow-wrap:anywhere}
.cui-visualization-thumbnail{min-height:96px;max-height:148px;overflow:hidden;padding:var(--cui-gap-control-content);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:var(--cui-surface-secondary)}
.cui-studio-header--compact{padding:var(--cui-gap-content);gap:var(--cui-gap-control-content);margin-bottom:var(--cui-gap-control-content)}.cui-studio-header--compact .cui-workbench-title{font-size:var(--cui-font-size-24);margin-top:0}.cui-studio-header--compact .cui-workbench-subtitle{margin-top:0}.cui-studio-first-example{display:block;min-width:0}
@media(max-width:900px){.cui-d6c-token-family__body,.cui-studio-first-example{grid-template-columns:1fr}.cui-d6c-palette-cards{grid-template-columns:1fr}.cui-d6c-live-specimen{order:-1}}
@media(max-width:680px){.cui-catalog-refine{padding:var(--cui-gap-control-content) var(--cui-gap-content)}.cui-catalog-refine:not([open]) .cui-catalog-refine__controls{display:none}.cui-catalog-refine__controls{display:grid;grid-template-columns:1fr;gap:var(--cui-gap-control-content)}.cui-catalog-refine__controls .q-field{min-width:0;width:100%}.cui-d6c-token-family__body{gap:var(--cui-gap-content)}.cui-d6c-live-specimen{padding:var(--cui-gap-control-content)}.cui-d6c-responsive-canvas{grid-template-columns:1fr}.cui-d6c-mini-canvas{min-height:84px}.cui-d6c-radius-demo{grid-template-columns:1fr}.cui-d6c-api-row .cui-button{width:100%}.cui-studio-header--compact .cui-workbench-title{font-size:var(--cui-font-size-20)}.cui-full-application__identity{display:grid;grid-template-columns:1fr}.cui-visualization-thumbnail{max-height:116px}}
.cui-layout-mini-frame--tablet .cui-layout-mini-frame__slots{grid-template-columns:repeat(2,minmax(0,1fr))}
.cui-layout-mini-frame--phone .cui-layout-mini-frame__slots{grid-template-columns:1fr}
@media(max-width:680px){.cui-workbench-ai-workflow{grid-template-columns:1fr}.cui-layout-live-composition{padding:var(--cui-gap-control-content)}.cui-layout-live-composition>.cui-page{overflow:hidden}.cui-layout-mini-frame{min-height:120px;padding:var(--cui-gap-control-content)}.cui-layout-catalog-miniatures .cui-layout-mini-frame{min-height:92px}}

/* G2.6 Reference Explorer presentation contract: content value before template geometry. */
.cui-explorer-card,.cui-explorer-authority-card{content-visibility:visible;contain-intrinsic-size:auto}
.cui-explorer-intent-card{min-height:0}
.cui-explorer-intent-card>.cui-button,.cui-explorer-authority-card>.cui-button,.cui-explorer-intent-match>.cui-button{margin-top:0}
.cui-explorer-card__actions{margin-top:0}
.cui-explorer-preview__badge{display:none}
.cui-explorer-intent-card__icon{display:grid;place-items:center;align-self:flex-start;width:var(--cui-control-height);height:var(--cui-control-height);border-radius:var(--cui-radius-control);background:var(--cui-accent-soft);color:var(--cui-accent)}
.cui-explorer-intent-card__icon svg{width:var(--cui-icon-size-md);height:var(--cui-icon-size-md)}
.cui-explorer-refine,.cui-explorer-refine__body{display:contents}.cui-explorer-refine>summary{display:none}
.cui-full-app-showcase .cui-explorer-preview{aspect-ratio:16/7}
.cui-full-app-showcase__facets{display:flex;flex-wrap:wrap;gap:var(--cui-space-1)}
.cui-full-app-showcase__architecture{margin-top:var(--cui-gap-control-content);padding-top:var(--cui-gap-control-content);border-top:1px solid var(--cui-border-subtle)}
.cui-full-app-showcase__architecture summary{cursor:pointer}
.cui-studio-decision-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--cui-gap-control-content)}
.cui-studio-decision-card{min-width:0;padding:var(--cui-gap-control-content) var(--cui-gap-stack);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:var(--cui-surface-secondary)}
.cui-d6c-token-details{margin-top:var(--cui-gap-control-content);padding-top:var(--cui-gap-control-content);border-top:1px solid var(--cui-border-subtle)}
.cui-d6c-token-details summary{cursor:pointer;color:var(--cui-text-secondary)}
.cui-d6c-color-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--cui-gap-control-content)}
.cui-d6c-type-role{display:grid;grid-template-columns:minmax(72px,.35fr) minmax(0,1fr);gap:var(--cui-gap-cluster);align-items:baseline;padding-bottom:var(--cui-gap-control-content);border-bottom:1px solid var(--cui-border-subtle)}
.cui-d6c-type-role__label{font-size:var(--cui-font-size-10);font-weight:var(--cui-font-weight-700);color:var(--cui-text-secondary)}
.cui-d6c-type-page-title{font-size:var(--cui-font-size-20);font-weight:var(--cui-font-weight-700);line-height:var(--cui-line-height-ratio-1_2)}
.cui-d6c-type-card-title{font-size:var(--cui-font-size-15);font-weight:var(--cui-font-weight-650)}
.cui-d6c-type-label{font-size:var(--cui-font-size-12);font-weight:var(--cui-font-weight-650)}
.cui-d6c-type-code{font-family:var(--cui-font-family-mono);font-size:var(--cui-font-size-12);color:var(--cui-text-secondary);overflow-wrap:anywhere}
.cui-d6c-canvas--desktop .cui-d6c-mini-slot{flex:1}
.cui-d6c-canvas--tablet .cui-d6c-mini-slot--wide{grid-column:1/-1}
.cui-d6c-canvas--tablet,.cui-d6c-canvas--phone{flex-wrap:wrap}
.cui-data-dock-capability-map{display:grid;gap:var(--cui-gap-stack);margin-bottom:var(--cui-gap-content);padding:var(--cui-gap-content);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-surface);background:var(--cui-surface)}
.cui-data-dock-capability-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:var(--cui-gap-control-content)}
.cui-data-dock-capability-card{display:grid;align-content:start;gap:var(--cui-gap-control-content);min-width:0;padding:var(--cui-gap-stack);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:var(--cui-surface-secondary)}
.cui-data-dock-unsupported{padding-top:var(--cui-gap-control-content);border-top:1px solid var(--cui-border-subtle)}
.cui-data-dock-unsupported summary{cursor:pointer}
.cui-workbench-build-footer{display:none;padding-top:var(--cui-gap-stack);margin-top:var(--cui-gap-section);border-top:1px solid var(--cui-border-subtle)}
@media(max-width:1100px){.cui-data-dock-capability-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:900px){.cui-studio-decision-grid{grid-template-columns:1fr}.cui-d6c-color-grid{grid-template-columns:1fr}}
@media(max-width:680px){
  .cui-explorer-intent-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .cui-explorer-intent-card{padding:var(--cui-gap-stack)}
  .cui-explorer-intent-card__icon{width:var(--cui-control-height-compact);height:var(--cui-control-height-compact)}
  .cui-explorer-intent-card>.cui-button{width:100%}
  .cui-full-app-showcase .cui-explorer-preview{aspect-ratio:16/9}
  .cui-d6c-type-role{grid-template-columns:1fr;gap:var(--cui-space-1)}
  .cui-data-dock-capability-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .cui-workbench-build-footer{display:block}
  .cui-explorer-refine{display:block}
  .cui-explorer-refine>summary{display:block;cursor:pointer;padding:var(--cui-gap-control-content);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:var(--cui-surface)}
  .cui-explorer-refine__body{display:none;padding-top:var(--cui-gap-control-content)}
  .cui-explorer-refine[open] .cui-explorer-refine__body{display:grid;gap:var(--cui-gap-control-content)}
}

/* G2.1 Explorer completion — visual discovery, click-efficiency, full-width canvas */
.cui-workbench-page{
  max-width:none!important;
  margin:0!important;
  padding:var(--cui-gap-content) var(--cui-gap-page,20px) calc(var(--cui-gap-section) * 2)!important;
  width:100%!important;
}
.cui-workbench-page>.cui-page-header{margin-bottom:var(--cui-gap-cluster)}
.cui-workbench-global-tools{position:sticky;top:calc(var(--cui-shell-header-height,60px) + var(--cui-space-1));z-index:var(--cui-layer-sticky);padding:var(--cui-gap-control-content);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:color-mix(in srgb,var(--cui-page) 92%,transparent);backdrop-filter:blur(8px)}
.cui-nav-section{padding:0 var(--cui-space-2)}
.cui-nav-section+.cui-nav-section{margin-top:var(--cui-space-4);padding-top:var(--cui-space-3);border-top:1px solid var(--cui-border-subtle)}
.cui-nav-section-label{padding-inline:var(--cui-space-2);font-size:var(--cui-font-size-10);font-weight:var(--cui-font-weight-700);letter-spacing:.08em;color:var(--cui-text-secondary)}
.cui-explorer-start-hero{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(260px,.5fr);gap:var(--cui-gap-content);padding:var(--cui-gap-content);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-surface);background:var(--cui-surface)}
.cui-explorer-start-hero__copy{display:flex;flex-direction:column;justify-content:center;min-width:0}
.cui-explorer-start-hero__metrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--cui-gap-cluster);align-content:start}
.cui-explorer-intent-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:var(--cui-gap-cluster);margin-top:var(--cui-gap-stack);margin-bottom:var(--cui-gap-section)}
.cui-explorer-intent-card{display:flex;flex-direction:column;gap:var(--cui-gap-control-content);min-height:168px;padding:var(--cui-gap-content);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-surface);background:var(--cui-surface)}
.cui-explorer-intent-card>.cui-button{margin-top:auto;align-self:flex-start}
.cui-explorer-authority-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:var(--cui-gap-cluster);margin-top:var(--cui-gap-stack)}
.cui-explorer-authority-card{display:flex;flex-direction:column;gap:var(--cui-gap-control-content);min-width:0;padding:var(--cui-gap-stack);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-surface);background:var(--cui-surface);content-visibility:auto;contain-intrinsic-size:360px}
.cui-explorer-authority-card>.cui-button{align-self:flex-start;margin-top:auto}
.cui-explorer-controls{display:grid;grid-template-columns:minmax(260px,1.4fr) minmax(190px,.5fr) auto;gap:var(--cui-gap-cluster);align-items:end;margin-bottom:var(--cui-gap-stack);padding:var(--cui-gap-stack);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-surface);background:var(--cui-surface-secondary)}
.cui-explorer-controls>.cui-field{min-width:0}.cui-explorer-controls__hint{grid-column:1/-1;font-size:var(--cui-font-size-11);color:var(--cui-text-secondary)}
.cui-explorer-gallery-host{min-width:0}
.cui-explorer-gallery-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:var(--cui-gap-cluster);align-items:start}
.cui-explorer-gallery-grid--apps{grid-template-columns:repeat(auto-fit,minmax(340px,1fr))}
.cui-explorer-card{display:flex;flex-direction:column;min-width:0;overflow:hidden;border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-surface);background:var(--cui-surface);content-visibility:auto;contain-intrinsic-size:440px;transition:border-color var(--cui-duration-fast) var(--cui-easing-native),transform var(--cui-duration-fast) var(--cui-easing-native)}
.cui-explorer-card:hover{border-color:var(--cui-accent);transform:translateY(-1px)}
/* Static preview assets are bounded evidence, not expensive live mounts. Keep
   them paintable in full-page screenshots and assistive review after scrolling. */
.cui-explorer-authority-card,.cui-explorer-card{content-visibility:visible;contain-intrinsic-size:auto}
.cui-explorer-card__open{display:flex;flex-direction:column;gap:var(--cui-gap-control-content);min-width:0;cursor:pointer;outline:none}
.cui-explorer-card__open:focus-visible{box-shadow:inset 0 0 0 var(--cui-state-focus-width) var(--cui-accent)}
.cui-explorer-card__copy{display:flex;flex-direction:column;gap:var(--cui-gap-control-content);min-width:0;padding:0 var(--cui-gap-stack) var(--cui-gap-stack)}
.cui-explorer-card__actions{display:flex;gap:var(--cui-gap-control-content);flex-wrap:wrap;margin-top:auto;padding:var(--cui-gap-control-content) var(--cui-gap-stack) var(--cui-gap-stack);border-top:1px solid var(--cui-border-subtle)}
.cui-explorer-card__actions>.cui-button{min-width:0}
.cui-explorer-preview{position:relative;width:100%;aspect-ratio:16/9;overflow:hidden;background:var(--cui-surface-secondary);border-bottom:1px solid var(--cui-border-subtle)}
.cui-explorer-preview__image{display:block;width:100%;height:100%!important;object-fit:cover;object-position:center 38%}
.cui-explorer-preview__image img{width:100%;height:100%;object-fit:cover;object-position:center 38%}
.cui-explorer-preview__placeholder{display:grid;place-items:center;width:100%;height:100%;padding:var(--cui-gap-content)}
.cui-explorer-preview__badge{position:absolute;inset-inline-start:var(--cui-gap-control-content);inset-block-end:var(--cui-gap-control-content);padding:3px 7px;border:1px solid color-mix(in srgb,var(--cui-border-strong) 70%,transparent);border-radius:var(--cui-radius-pill);background:color-mix(in srgb,var(--cui-surface) 88%,transparent);font-size:var(--cui-font-size-10);font-weight:var(--cui-font-weight-650);color:var(--cui-text-primary);backdrop-filter:blur(6px)}
.cui-explorer-compare{display:flex;flex-direction:column;gap:var(--cui-gap-stack);margin-bottom:var(--cui-gap-content);padding:var(--cui-gap-stack);border:1px solid var(--cui-accent);border-radius:var(--cui-radius-surface);background:var(--cui-accent-soft)}
.cui-explorer-compare__head{display:flex;justify-content:space-between;gap:var(--cui-gap-cluster);align-items:start;flex-wrap:wrap}
.cui-explorer-compare__grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--cui-gap-cluster)}
.cui-explorer-compare-card{display:flex;flex-direction:column;gap:var(--cui-gap-control-content);min-width:0;padding:var(--cui-gap-stack);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:var(--cui-surface)}
.cui-explorer-compare-card .cui-explorer-preview{border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control)}
.cui-explorer-compare-card__label{font-size:var(--cui-font-size-10);font-weight:var(--cui-font-weight-700);text-transform:uppercase;letter-spacing:.06em;color:var(--cui-text-secondary)}
.cui-explorer-recent-row{display:flex;gap:var(--cui-gap-control-content);flex-wrap:wrap;margin-top:var(--cui-gap-cluster)}
.cui-explorer-gallery-grid .cui-workbench-card__body,.cui-explorer-authority-card .cui-workbench-card__body{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
@media(max-width:1100px){
  .cui-explorer-gallery-grid{grid-template-columns:repeat(auto-fill,minmax(250px,1fr))}
  .cui-explorer-compare__grid{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media(max-width:900px){
  .cui-workbench-page{padding-inline:var(--cui-space-4)!important}
  .cui-explorer-start-hero{grid-template-columns:1fr}
  .cui-explorer-controls{grid-template-columns:minmax(0,1fr) minmax(170px,.45fr)}
  .cui-explorer-controls>.cui-button{grid-column:1/-1;justify-self:start}
  .cui-explorer-gallery-grid{grid-template-columns:repeat(auto-fill,minmax(240px,1fr))}
}
@media(max-width:680px){
  .cui-workbench-page{padding:var(--cui-space-3) var(--cui-space-4) var(--cui-space-8)!important}
  .cui-workbench-global-tools{position:static;padding:var(--cui-space-2)}
  .cui-workbench-command-shortcut{display:none!important}
  .cui-explorer-start-hero{padding:var(--cui-gap-stack)}
  .cui-explorer-start-hero__metrics{grid-template-columns:repeat(4,minmax(0,1fr));gap:var(--cui-space-1)}
  .cui-explorer-start-hero__metrics .cui-workbench-kpi{padding:var(--cui-space-2);text-align:center}
  .cui-explorer-intent-grid,.cui-explorer-authority-grid,.cui-explorer-gallery-grid,.cui-explorer-gallery-grid--apps,.cui-explorer-compare__grid{grid-template-columns:1fr}
  .cui-explorer-intent-card{min-height:0}
  .cui-explorer-controls{display:grid;grid-template-columns:1fr;padding:var(--cui-gap-control-content)}
  .cui-explorer-controls__hint{display:none}
  .cui-explorer-preview{aspect-ratio:16/8.7}
  .cui-explorer-card__actions{gap:var(--cui-space-1)}
}
.cui-explorer-intent-recommendation-host{margin:var(--cui-gap-stack) 0 var(--cui-gap-section)}
.cui-explorer-intent-recommendation{display:flex;flex-direction:column;gap:var(--cui-gap-stack);padding:var(--cui-gap-content);border:1px solid var(--cui-accent);border-radius:var(--cui-radius-surface);background:var(--cui-accent-soft)}
.cui-explorer-intent-recommendation__head{display:flex;align-items:flex-start;justify-content:space-between;gap:var(--cui-gap-cluster);flex-wrap:wrap}
.cui-explorer-intent-recommendation__body{display:grid;grid-template-columns:minmax(260px,.8fr) minmax(0,1.7fr);gap:var(--cui-gap-cluster)}
.cui-explorer-intent-plan{display:flex;flex-direction:column;gap:var(--cui-gap-control-content);padding:var(--cui-gap-stack);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:var(--cui-surface)}
.cui-explorer-command{padding:var(--cui-gap-control-content);border-radius:var(--cui-radius-control);background:var(--cui-surface-secondary);font-family:var(--cui-font-mono,monospace);font-size:var(--cui-font-size-11);overflow-wrap:anywhere}
.cui-explorer-intent-matches{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--cui-gap-control-content)}
.cui-explorer-intent-match{display:flex;flex-direction:column;gap:var(--cui-gap-control-content);min-width:0;padding:var(--cui-gap-stack);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:var(--cui-surface)}
.cui-explorer-intent-match>.cui-button{margin-top:auto;align-self:flex-start}
@media(max-width:1000px){.cui-explorer-intent-recommendation__body{grid-template-columns:1fr}.cui-explorer-intent-matches{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:680px){.cui-explorer-intent-matches{grid-template-columns:1fr}.cui-explorer-intent-recommendation{padding:var(--cui-gap-stack)}}


/* G2.2 Human Visual Closure ------------------------------------------------ */
.cui-explorer-preview__badge{
  inset-inline-start:auto!important;inset-inline-end:var(--cui-gap-control-content)!important;
  inset-block-start:var(--cui-gap-control-content)!important;inset-block-end:auto!important;
  padding:2px 6px!important;font-size:var(--cui-font-size-9_5)!important;
  letter-spacing:.05em;text-transform:uppercase;pointer-events:none;
}
body.body--dark .cui-explorer-preview,.q-dark .cui-explorer-preview{
  background:var(--cui-surface-secondary);padding:var(--cui-space-2);
}
body.body--dark .cui-explorer-preview__image,.q-dark .cui-explorer-preview__image{
  border-radius:var(--cui-radius-control);box-shadow:0 0 0 1px var(--cui-border-subtle);opacity:.92;
}
.cui-explorer-intent-recommendation-host:empty{display:none!important;margin:0!important}
.cui-state-atlas{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:var(--cui-gap-control-content);margin-bottom:var(--cui-gap-stack)}
.cui-state-atlas__item{display:flex;flex-direction:column;gap:var(--cui-space-1);min-width:0;padding:var(--cui-gap-control-content);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:var(--cui-surface-secondary)}
.cui-state-atlas__label{font-size:var(--cui-font-size-11);font-weight:var(--cui-font-weight-700);color:var(--cui-text-primary)}
.cui-state-atlas__description{font-size:var(--cui-font-size-10);line-height:var(--cui-line-height-ratio-1_4);color:var(--cui-text-secondary)}
.cui-studio-public-code{display:flex;flex-direction:column;gap:var(--cui-gap-control-content);padding:var(--cui-gap-stack);border:1px solid var(--cui-accent);border-radius:var(--cui-radius-surface);background:var(--cui-accent-soft);margin-bottom:var(--cui-gap-stack)}
.cui-studio-harness-details{margin-top:var(--cui-gap-stack);padding:var(--cui-gap-control-content) var(--cui-gap-stack);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:var(--cui-surface-secondary)}
.cui-studio-harness-details>summary{cursor:pointer;font-size:var(--cui-font-size-12);font-weight:var(--cui-font-weight-700)}
.cui-layout-gallery-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:var(--cui-gap-stack);margin:var(--cui-gap-stack) 0 var(--cui-gap-section)}
.cui-layout-gallery-card{padding:var(--cui-gap-stack)}
.cui-layout-gallery-card .cui-layout-catalog-miniatures{margin-top:var(--cui-gap-control-content)}
.cui-layout-inspector-host{margin-top:var(--cui-gap-stack)}
@media(max-width:680px){
  .cui-explorer-start-hero__metrics{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:var(--cui-space-2)!important}
  .cui-explorer-start-hero__metrics .cui-workbench-kpi{padding:var(--cui-space-3)!important}
  .cui-layout-gallery-grid{grid-template-columns:1fr}
  .cui-state-atlas{grid-template-columns:repeat(2,minmax(0,1fr))}
  .cui-explorer-preview__badge{inset-inline-end:var(--cui-space-2)!important;inset-block-start:var(--cui-space-2)!important}
}

/* G2.3 final visual polish ------------------------------------------------ */
.cui-studio-status-row{
  display:flex;align-items:center;gap:var(--cui-gap-cluster);flex-wrap:wrap;
  width:100%;margin:0 0 var(--cui-gap-control-content);
}
.cui-studio-status-row>.cui-workbench-note{margin:0!important}
.cui-tab-panels,.cui-tab-panels .q-tab-panel,.cui-studio-state-host{width:100%;min-width:0}
.cui-state-atlas{
  width:100%!important;
  grid-template-columns:repeat(3,minmax(0,1fr))!important;
  align-items:stretch;
}
.cui-state-atlas__item{min-height:70px;justify-content:center}
.cui-studio-harness-details{
  width:100%;
}
.cui-studio-harness-details:not([open]){padding-block:var(--cui-gap-stack)}
.cui-studio-harness-details>summary{display:flex;align-items:center;min-height:var(--cui-control-height)}
.cui-layout-gallery-grid{order:0}
.cui-layout-inspector-host{order:1}
@media(max-width:900px){
  .cui-state-atlas{grid-template-columns:repeat(2,minmax(0,1fr))!important}
}
@media(max-width:520px){
  .cui-state-atlas{grid-template-columns:1fr!important}
  .cui-studio-status-row{display:grid;grid-template-columns:1fr}
}

/* G2.6 usability reconstruction: shared authorities, compact discovery, and
   deliberate responsive geometry.  These rules are intentionally attached to
   reusable Explorer anatomy rather than individual routes. */
.cui-workbench-page{max-width:none!important;margin:0!important}
.cui-workbench-section{margin-top:var(--cui-gap-section)}
.cui-workbench-section-head{margin-bottom:var(--cui-gap-cluster)}
.cui-workbench-card{min-height:0}
.cui-workbench-chiprow{margin-top:0}
.cui-explorer-gallery-grid,.cui-workbench-grid,.cui-explorer-authority-grid{align-items:stretch}
.cui-explorer-card,.cui-explorer-authority-card,.cui-workbench-card{height:100%}
.cui-explorer-intent-card{min-height:0;display:grid;grid-template-rows:auto auto 1fr auto;align-content:start}
.cui-explorer-intent-card>.cui-button{margin-top:var(--cui-gap-control-content);white-space:nowrap;min-width:max-content}
.cui-explorer-intent-recommendation-host{margin-block:var(--cui-gap-stack)}
.cui-explorer-intent-recommendation{gap:var(--cui-gap-cluster);padding:var(--cui-gap-stack)}
.cui-explorer-intent-recommendation__head{align-items:center}
.cui-explorer-intent-recommendation__head>.cui-button{margin-inline-start:auto}
.cui-workbench-kpi[tabindex]{cursor:help}
.cui-workbench-kpi[tabindex]:focus-visible{outline:var(--cui-state-focus-width) solid var(--cui-accent);outline-offset:var(--cui-state-focus-offset)}
.cui-catalog-refine{min-width:0}
.cui-explorer-refine__body{display:flex;align-items:end;gap:var(--cui-gap-cluster);flex-wrap:wrap}
.cui-explorer-refine__body>*{min-width:0;flex:1 1 200px}
.cui-explorer-card__actions{align-items:center}
.cui-explorer-card__actions>.cui-button{white-space:nowrap}
.cui-d6c-token-family{padding:var(--cui-gap-content)}
.cui-d6c-token-family__head{display:grid;gap:var(--cui-gap-control-content);margin-bottom:var(--cui-gap-stack)}
.cui-d6c-spacing-demo{display:grid;gap:var(--cui-gap-control-content)}
.cui-d6c-spacing-block{display:flex;align-items:center;gap:var(--cui-gap-cluster);border:1px solid var(--cui-border-subtle);border-left:0;padding:var(--cui-gap-control-content) var(--cui-gap-stack);border-radius:var(--cui-radius-control);background:var(--cui-surface)}
.cui-d6c-spacing-block::before{content:'';display:block;width:var(--cui-spacing-demo,16px);height:var(--cui-space-2);border-radius:var(--cui-radius-pill);background:var(--cui-accent)}
.cui-d6c-spacing-block:nth-child(1)::before{--cui-spacing-demo:var(--cui-space-1)}
.cui-d6c-spacing-block:nth-child(2)::before{--cui-spacing-demo:var(--cui-space-2)}
.cui-d6c-spacing-block:nth-child(3)::before{--cui-spacing-demo:var(--cui-space-4)}
.cui-d6c-spacing-block:nth-child(4)::before{--cui-spacing-demo:var(--cui-space-6)}
.cui-d6c-spacing-block:nth-child(5)::before{--cui-spacing-demo:var(--cui-space-10)}
.cui-d6c-spacing-block:nth-child(6)::before{--cui-spacing-demo:var(--cui-space-16)}
.cui-d6c-spacing-block__label{font-weight:var(--cui-font-weight-650);min-width:70px}
.cui-d6c-spacing-block__value{color:var(--cui-text-secondary);font-size:var(--cui-font-size-11)}
.cui-d6c-token-list{display:grid;grid-template-columns:minmax(100px,.7fr) minmax(180px,1.5fr) minmax(100px,.6fr);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);overflow:auto}
.cui-d6c-token-row{display:contents}
.cui-d6c-token-row>*{min-width:0;padding:var(--cui-gap-control-content) var(--cui-gap-stack);border-bottom:1px solid var(--cui-border-subtle);overflow-wrap:anywhere}
.cui-d6c-token-row:nth-last-child(-n+3)>*{border-bottom:0}
.cui-d6c-token-row--head>*{font-size:var(--cui-font-size-11);font-weight:var(--cui-font-weight-700);color:var(--cui-text-secondary);background:var(--cui-surface-secondary)}
.cui-d6c-token-meaning{color:var(--cui-text-secondary);font-size:var(--cui-font-size-11)}
.cui-d6c-type-demo{border-left:0;padding:0}
.cui-studio-reference-contract>summary{display:flex;align-items:center;gap:var(--cui-gap-control-content);min-height:var(--cui-control-height);padding:0 var(--cui-gap-control-content);border-radius:var(--cui-radius-control);cursor:pointer}
.cui-studio-reference-contract>summary::before{content:'›';font-size:var(--cui-font-size-20);color:var(--cui-accent);transition:transform var(--cui-duration-fast) var(--cui-easing-native)}
.cui-studio-reference-contract[open]>summary::before{transform:rotate(90deg)}
.cui-studio-reference-contract>summary:hover,.cui-studio-reference-contract>summary:focus-visible{background:var(--cui-surface-hover);outline:var(--cui-state-focus-width) solid var(--cui-accent);outline-offset:var(--cui-state-focus-offset)}
.cui-studio-code,.cui-studio-public-code{width:100%;max-width:none}
.cui-studio-public-code pre,.cui-studio-code pre{max-width:none;white-space:pre;overflow:auto}
.cui-tabs-region{min-width:0;overflow:visible}
.cui-tabs-region .q-tabs__content{min-width:0;overflow-x:auto;scrollbar-width:thin}
.cui-tab{flex:0 0 auto}
.cui-tab-panels{min-width:0;overflow:visible}
.cui-settings-page{display:grid;gap:var(--cui-gap-stack);max-width:1120px}
.cui-settings-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--cui-gap-stack);align-items:start}
.cui-settings-card{display:grid;gap:var(--cui-gap-content);min-width:0;padding:var(--cui-gap-content);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-surface);background:var(--cui-surface)}
.cui-settings-card:first-child{grid-column:span 2}
.cui-settings-row{display:flex;align-items:center;justify-content:space-between;gap:var(--cui-gap-content);min-height:var(--cui-control-height);padding-block:var(--cui-gap-control-content);border-bottom:1px solid var(--cui-border-subtle)}
.cui-settings-row:last-child{border-bottom:0}
.cui-settings-row__copy{display:grid;gap:var(--cui-space-1);min-width:0}
.cui-settings-row__label{font-weight:var(--cui-font-weight-650)}
.cui-settings-row__description,.cui-settings-row__value{font-size:var(--cui-font-size-12);color:var(--cui-text-secondary);overflow-wrap:anywhere}
.cui-settings-row__value{text-align:end}
.cui-settings-facts{display:flex;flex-wrap:wrap;gap:var(--cui-gap-control-content)}
.cui-settings-fact{padding:var(--cui-gap-control-content) var(--cui-gap-stack);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-pill);background:var(--cui-surface-secondary);font-size:var(--cui-font-size-12)}
.cui-settings-diagnostics{padding-top:var(--cui-gap-content);border-top:1px solid var(--cui-border-subtle)}
.cui-unified-patterns{display:grid;grid-template-columns:260px minmax(0,1fr);gap:var(--cui-gap-stack);align-items:start}
.cui-unified-pattern-rail{display:grid;gap:var(--cui-space-1);position:sticky;top:calc(var(--cui-shell-header-height,60px) + var(--cui-space-3))}
.cui-unified-pattern-option{display:flex;align-items:center;justify-content:space-between;gap:var(--cui-gap-control-content);width:100%;padding:var(--cui-gap-control-content) var(--cui-gap-stack);border:1px solid transparent;border-radius:var(--cui-radius-control);background:transparent;color:var(--cui-text-primary);text-align:start;cursor:pointer}
.cui-unified-pattern-option:hover,.cui-unified-pattern-option:focus-visible,.cui-unified-pattern-option.is-active{border-color:var(--cui-border-default);background:var(--cui-accent-soft);outline:none}
.cui-unified-pattern-live{min-width:0;padding:var(--cui-gap-stack);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-surface);background:var(--cui-surface-secondary)}
.cui-debugger-filterbar{display:flex;align-items:end;gap:var(--cui-gap-control-content);flex-wrap:wrap;padding:var(--cui-gap-control-content) 0;border-bottom:1px solid var(--cui-border-subtle)}
.cui-debugger-filterbar>.cui-field{min-width:160px;flex:1 1 180px}
.cui-buganizer-trigger{position:relative}
.cui-buganizer-count{position:absolute;inset-inline-end:-2px;inset-block-start:-2px;min-width:16px;height:16px;padding-inline:3px;border-radius:var(--cui-radius-pill);background:var(--cui-danger);color:var(--cui-text-inverse);font-size:var(--cui-font-size-9);line-height:var(--cui-line-height-16);text-align:center}
.cui-data-lab{display:grid;gap:var(--cui-gap-section);width:100%;min-width:0}
.cui-data-lab-intro,.cui-data-lab-active-head{display:flex;align-items:flex-start;justify-content:space-between;gap:var(--cui-gap-stack);min-width:0}
.cui-data-lab-intro{padding-bottom:var(--cui-gap-stack);border-bottom:1px solid var(--cui-border-subtle)}
.cui-data-lab-intro>.cui-workbench-title,.cui-data-lab-intro>.cui-workbench-subtitle,.cui-data-lab-active-head .cui-workbench-section-title,.cui-data-lab-active-head .cui-workbench-note{min-width:0;word-break:normal;overflow-wrap:normal}
.cui-data-lab-switcher{min-width:0;overflow-x:auto;scrollbar-width:thin}
.cui-data-lab-switcher .cui-segmented-control{min-width:max-content}
.cui-data-lab .cui-segmented-control.q-btn-toggle>.q-btn,.cui-data-lab .cui-segmented-control.q-btn-toggle>.q-btn .q-btn__content{flex:0 0 auto;white-space:nowrap!important;word-break:normal!important;overflow-wrap:normal!important}
.cui-data-lab-active{display:grid;gap:var(--cui-gap-stack);min-width:0}
.cui-data-lab-active-head{align-items:center;padding:var(--cui-gap-content) 0 0}
.cui-data-lab-active-head>.cui-chip-row{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:var(--cui-gap-control-content)}
.cui-data-lab-toolbar{display:flex;align-items:center;justify-content:flex-end;flex-wrap:wrap;gap:var(--cui-gap-control-content);min-width:0}
.cui-data-lab-toolbar .cui-table-view-button{margin-inline-start:auto}
.cui-data-lab-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:var(--cui-gap-stack);min-width:0}
.cui-data-lab-summary--visual{grid-template-columns:repeat(5,minmax(0,1fr))}
.cui-data-lab-summary .cui-workbench-kpi{min-height:0;padding:var(--cui-gap-content);background:var(--cui-surface);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-surface)}
.cui-data-lab-table-frame{display:grid;gap:var(--cui-gap-control-content);width:100%;min-width:0;padding:var(--cui-gap-content);background:var(--cui-surface);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-surface)}
.cui-data-lab-table-frame>.cui-table-shell{min-width:0;width:100%}
.cui-data-lab-reference{display:grid;gap:var(--cui-gap-control-content);padding-top:var(--cui-gap-stack);border-top:1px solid var(--cui-border-subtle)}
.cui-data-lab-reference>summary{display:flex;align-items:center;min-height:var(--cui-control-height);cursor:pointer}
.cui-data-lab-reference .cui-code-viewer{width:100%;max-height:360px;overflow:auto}
.cui-data-lab-detail-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--cui-gap-stack)}
.cui-data-lab-visual-controls{display:grid;grid-template-columns:minmax(220px,1fr) minmax(0,2fr) auto;align-items:end;gap:var(--cui-gap-content);min-width:0}
.cui-data-lab-visual-control-group{display:grid;gap:var(--cui-gap-control-content);min-width:0}
.cui-data-lab-visual-mapping-controls{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--cui-gap-control-content);min-width:0}
.cui-data-lab-visual-controls .q-field{width:100%;min-width:0}
.cui-data-lab-visual-host{display:grid;gap:var(--cui-gap-stack);min-width:0}
.cui-data-lab-visual-grid{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(360px,.9fr);gap:var(--cui-gap-stack);align-items:start;min-width:0}
.cui-data-lab-visual-table,.cui-data-lab-visual-chart{display:grid;gap:var(--cui-gap-control-content);min-width:0;padding:var(--cui-gap-content);background:var(--cui-surface);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-surface)}
.cui-data-lab-visual-chart .cui-chart-panel{min-width:0}
.cui-data-lab-chart-switcher{min-width:0;max-width:100%;overflow-x:auto}
.cui-data-lab-state-selector{min-width:0;max-width:100%;overflow-x:auto;scrollbar-width:thin}
.cui-data-lab-state-selector .cui-segmented-control{width:max-content;min-width:max-content}
.cui-data-lab-state-host{display:grid;gap:var(--cui-gap-stack);min-width:0}
@media(max-width:1100px){
  .cui-data-lab-intro,.cui-data-lab-active-head{display:grid;grid-template-columns:1fr}
  .cui-data-lab-active-head>.cui-chip-row{justify-content:flex-start}
  .cui-data-lab-visual-controls{grid-template-columns:1fr}
  .cui-data-lab-visual-grid{grid-template-columns:1fr}
  .cui-data-lab-summary--visual{grid-template-columns:repeat(3,minmax(0,1fr))}
}
@media(max-width:600px){
  .cui-data-lab-summary{grid-template-columns:repeat(2,minmax(0,1fr))}
  .cui-data-lab-summary--visual{grid-template-columns:repeat(2,minmax(0,1fr))}
  .cui-data-lab-toolbar{justify-content:flex-start}
  .cui-data-lab-toolbar .cui-table-view-button{margin-inline-start:0}
  .cui-data-lab-detail-grid{grid-template-columns:1fr}
  .cui-data-lab-table-frame{padding:var(--cui-gap-control-content)}
  .cui-data-lab-visual-mapping-controls{grid-template-columns:1fr}
  .cui-data-lab-chart-switcher{max-width:100%}
}
@media(max-width:900px){.cui-settings-grid{grid-template-columns:1fr}.cui-settings-card:first-child{grid-column:auto}.cui-unified-patterns{grid-template-columns:1fr}.cui-unified-pattern-rail{position:static;display:flex;overflow-x:auto;scrollbar-width:thin}.cui-unified-pattern-option{min-width:max-content}}
@media(max-width:680px){.cui-explorer-refine{display:block}.cui-explorer-refine>summary{display:flex;align-items:center;min-height:var(--cui-control-height);padding:0 var(--cui-gap-control-content);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:var(--cui-surface);cursor:pointer}.cui-explorer-refine__body{display:none;padding-top:var(--cui-gap-control-content)}.cui-explorer-refine[open] .cui-explorer-refine__body{display:grid}.cui-explorer-controls{display:block}.cui-explorer-controls>.cui-explorer-controls__hint{display:none}.cui-settings-row{align-items:flex-start;flex-direction:column}.cui-settings-row__value{text-align:start}.cui-d6c-token-list{grid-template-columns:minmax(88px,.6fr) minmax(150px,1.3fr) minmax(80px,.5fr)}}

/* Analytical summaries use metric anatomy, not five full-width chips. */
.cui-analytics-metric-strip{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:var(--cui-gap-control-content);width:100%;margin-top:var(--cui-gap-control-content)}
.cui-analytics-metric{display:grid;gap:var(--cui-space-1);min-width:0;padding:var(--cui-gap-control-content) var(--cui-gap-stack);border:1px solid var(--cui-border-subtle);border-radius:var(--cui-radius-control);background:var(--cui-surface-secondary)}
.cui-analytics-metric__label{font-size:var(--cui-font-size-11);font-weight:var(--cui-font-weight-650);color:var(--cui-text-secondary);letter-spacing:.03em}
.cui-analytics-metric__value{font-size:var(--cui-font-size-16);font-weight:var(--cui-font-weight-720);color:var(--cui-text-primary);font-variant-numeric:tabular-nums;white-space:nowrap}
.cui-workbench-mini-grid--wafer-multiples{grid-template-columns:repeat(4,minmax(0,1fr));gap:var(--cui-gap-control-content)}
.cui-workbench-mini-grid--wafer-multiples .cui-workbench-mini-panel{min-width:0}
@media(max-width:1100px){.cui-analytics-metric-strip{grid-template-columns:repeat(3,minmax(0,1fr))}.cui-workbench-mini-grid--wafer-multiples{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:600px){.cui-analytics-metric-strip{grid-template-columns:repeat(2,minmax(0,1fr))}.cui-workbench-mini-grid--wafer-multiples{grid-template-columns:1fr}}
'''


def install_workbench_css() -> None:
    from nicegui import ui
    ui.add_css(WORKBENCH_CSS, shared=True)

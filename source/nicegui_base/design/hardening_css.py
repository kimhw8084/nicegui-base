from __future__ import annotations


def build_hardening_css() -> str:
    """v1.6 rendered-product hardening layer.

    Loaded last. These rules encode the live acceptance contract discovered from
    real Linux browser review: deterministic shell geometry, mandatory spacing,
    optical centering, overlay visibility, field/select normalization and dense
    data ergonomics.
    """
    return r'''
/* ================================================================
   COMPANY UI v1.6 RENDERED PRODUCT HARDENING
   ================================================================ */
/* The framework, not the page author, owns primary geometry. */
.cui-page{display:flex!important;flex-direction:column!important;align-items:stretch!important;gap:var(--cui-section-gap)!important;width:100%!important;max-width:100%!important;min-width:0!important;}
.cui-page>*{min-width:0!important;max-width:100%;}
.cui-page>.cui-page-header,.cui-page>.cui-lab-controlbar,.cui-page>.cui-lab-section,.cui-page>.cui-pattern{margin:0!important;}
.cui-section,.cui-lab-section,.cui-form-section,.cui-content-column,.cui-alert-stack,.cui-form-stack{display:flex!important;flex-direction:column!important;gap:var(--cui-stack-gap)!important;min-width:0;width:100%;}
.cui-section>*+*,.cui-lab-section>*+*,.cui-form-section>*+*,.cui-content-column>*+*,.cui-form-stack>*+*,.cui-alert-stack>*+*{margin-block-start:0!important;}
.cui-panel,.cui-card,.cui-well,.cui-surface--panel,.cui-surface--card,.cui-surface--well,.cui-lab-sample{
  display:flex!important;flex-direction:column!important;align-items:stretch!important;gap:var(--cui-stack-gap)!important;
  min-width:0!important;max-width:100%!important;
}
.cui-lab-sample__title{margin:0!important;}
.cui-lab-section+.cui-lab-section{margin-top:0!important;}
.cui-lab-grid,.cui-surface-grid,.cui-grid,.cui-metric-strip{gap:var(--cui-stack-gap)!important;}
.cui-lab-inline,.cui-action-row,.cui-button-cluster,.cui-toolbar-group,.cui-inline-group,.cui-form-actions,.cui-page-navigation{
  gap:var(--cui-cluster-gap)!important;align-items:center!important;
}
.cui-button-cluster>.q-btn+.q-btn,.cui-action-row>.q-btn+.q-btn,.cui-toolbar-group>.q-btn+.q-btn{margin-left:0!important;}

/* Application header = application identity. Current view lives below in PageHeader. */
.cui-app-header.q-header,.cui-app-header{z-index:var(--cui-app-header-z)!important;display:flex!important;align-items:center!important;gap:16px!important;}
.cui-shell-brand{flex:1 1 auto!important;min-width:0!important;}
.cui-shell-title-block{min-width:0!important;}
.cui-shell-title--animated{animation:cui-v16-app-title var(--cui-duration-title-lux) var(--cui-easing-enter) both!important;}
@keyframes cui-v16-app-title{0%{opacity:0;transform:translateY(7px);filter:blur(3px)}55%{filter:blur(0)}100%{opacity:1;transform:none;filter:none}}
.cui-page-header{display:flex!important;align-items:flex-end!important;justify-content:space-between!important;gap:20px!important;width:100%!important;padding:2px 0 18px!important;border-bottom:1px solid var(--cui-border-subtle)!important;}
.cui-page-header__copy{display:flex!important;flex-direction:column!important;gap:5px!important;}
.cui-page-title{margin:0!important;}
.cui-page-description{margin:0!important;}

/* Desktop navigation is Company-owned fixed geometry, not a Quasar drawer. */
.cui-app-sidebar:not(.q-drawer){
  position:fixed!important;left:0!important;top:var(--cui-shell-header-height)!important;bottom:0!important;z-index:var(--cui-sidebar-z)!important;
  width:var(--cui-shell-sidebar-width)!important;display:flex!important;flex-direction:column!important;min-width:0!important;
  padding:10px 8px 10px!important;background:var(--cui-surface)!important;border-right:1px solid var(--cui-border-subtle)!important;
  overflow:hidden!important;transition:width var(--cui-duration-shell) var(--cui-easing-standard)!important;
}
html[data-sidebar='compact'] .cui-app-sidebar:not(.q-drawer){width:var(--cui-shell-sidebar-compact-width)!important;}
.cui-sidebar-top{height:42px;display:flex;align-items:center;justify-content:flex-end;flex:0 0 auto;padding:0 2px 6px;}
html[data-sidebar='compact'] .cui-sidebar-top{justify-content:center;}
.cui-sidebar-collapse{flex:0 0 auto;}
.cui-sidebar-nav{flex:1 1 auto;min-height:0;overflow-y:auto;overflow-x:hidden;padding:2px 0 10px;scrollbar-width:thin;}
.cui-nav-section{display:flex;flex-direction:column;gap:4px;margin:0 0 12px;}
.cui-nav-section__items,.cui-nav-group__children{display:flex;flex-direction:column;gap:3px;}
.cui-nav-section-label{height:22px!important;padding:3px 12px!important;margin:0!important;white-space:nowrap;overflow:hidden;transition:opacity var(--cui-duration-micro) var(--cui-easing-native);}
.cui-nav-group{display:flex;flex-direction:column;gap:3px;}
.cui-nav-group__label{min-height:34px;display:flex;align-items:center;gap:9px;padding:0 10px;color:var(--cui-text-tertiary);font-size:var(--cui-font-size-11);font-weight:var(--cui-font-weight-700);}
.cui-nav-group__text{white-space:nowrap;}
.cui-nav-item.q-item,.cui-nav-item{min-height:var(--cui-nav-item-height)!important;height:var(--cui-nav-item-height)!important;padding:0 8px!important;margin:0!important;border-radius:var(--cui-radius-control)!important;display:flex!important;align-items:center!important;gap:4px!important;overflow:hidden!important;}
.cui-nav-item__icon.q-item__section--avatar,.cui-nav-item__icon{min-width:var(--cui-nav-icon-box)!important;width:var(--cui-nav-icon-box)!important;height:var(--cui-nav-icon-box)!important;padding:0!important;display:grid!important;place-items:center!important;}
.cui-nav-item__icon .cui-svg-icon-host{display:grid!important;place-items:center!important;width:20px!important;height:20px!important;line-height:0!important;}
.cui-nav-item__copy{min-width:0!important;white-space:nowrap;overflow:hidden;}
.cui-nav-item__copy .q-item__label{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.cui-nav-item__badge{padding-left:4px!important;}
html[data-sidebar='compact'] .cui-nav-section-label,html[data-sidebar='compact'] .cui-nav-group__text,html[data-sidebar='compact'] .cui-nav-item__copy,html[data-sidebar='compact'] .cui-nav-item__badge{display:none!important;}
html[data-sidebar='compact'] .cui-nav-group__label,html[data-sidebar='compact'] .cui-nav-item{justify-content:center!important;padding-inline:0!important;}
html[data-sidebar='compact'] .cui-nav-item__icon{margin:0!important;}
.cui-sidebar-footer{flex:0 0 auto;margin-top:auto;border-top:1px solid var(--cui-border-subtle);padding:10px 4px 2px;display:flex;flex-direction:column;gap:8px;background:var(--cui-surface);}
.cui-sidebar-owner{display:flex;align-items:center;gap:8px;padding:6px 7px;min-width:0;}
.cui-sidebar-owner>.cui-svg-icon-host{flex:0 0 auto;}
.cui-sidebar-owner__copy{min-width:0;display:flex;flex-direction:column;gap:1px;}
.cui-sidebar-owner__label{font-size:var(--cui-font-size-9);line-height:var(--cui-line-height-12);text-transform:uppercase;letter-spacing:.06em;color:var(--cui-text-tertiary);}
.cui-sidebar-owner__name{font-size:var(--cui-font-size-11);line-height:var(--cui-line-height-15);font-weight:var(--cui-font-weight-650);color:var(--cui-text-secondary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.cui-sidebar-footer__actions{display:flex;flex-direction:column;gap:3px;}
.cui-sidebar-footer__action.q-btn{min-height:34px!important;padding:0 8px!important;border-radius:var(--cui-radius-inner)!important;color:var(--cui-text-secondary)!important;justify-content:flex-start!important;}
.cui-sidebar-footer__action.q-btn .q-btn__content{justify-content:flex-start!important;gap:8px!important;width:100%;}
html[data-sidebar='compact'] .cui-sidebar-owner{justify-content:center;padding-inline:0;}
html[data-sidebar='compact'] .cui-sidebar-owner__copy,html[data-sidebar='compact'] .cui-sidebar-footer__action .q-btn__content>.q-label{display:none!important;}
html[data-sidebar='compact'] .cui-sidebar-footer__action.q-btn{width:100%;padding:0!important;justify-content:center!important;}
html[data-sidebar='compact'] .cui-sidebar-footer__action.q-btn .q-btn__content{justify-content:center!important;}
/* Main canvas invariant: occupy exactly the viewport area not owned by desktop navigation.
   Horizontal breathing room belongs to .cui-page padding, never to shell offset math. */
.cui-app-main{
  width:100%!important;max-width:none!important;min-width:0!important;
  margin-left:0!important;padding-left:0!important;padding-right:0!important;
  align-items:stretch!important;overflow-x:clip!important;
}
.cui-app-main--with-sidebar{
  margin-left:var(--cui-shell-sidebar-width)!important;
  width:calc(100% - var(--cui-shell-sidebar-width))!important;
  max-width:calc(100% - var(--cui-shell-sidebar-width))!important;
  padding-left:0!important;
  transition:margin-left var(--cui-duration-shell) var(--cui-easing-standard),width var(--cui-duration-shell) var(--cui-easing-standard),max-width var(--cui-duration-shell) var(--cui-easing-standard)!important;
}
html[data-sidebar='compact'] .cui-app-main--with-sidebar{
  margin-left:var(--cui-shell-sidebar-compact-width)!important;
  width:calc(100% - var(--cui-shell-sidebar-compact-width))!important;
  max-width:calc(100% - var(--cui-shell-sidebar-compact-width))!important;
}
/* Width variants describe preferred inner reading behavior, not the outer page canvas. */
.cui-page--reading,.cui-page--standard,.cui-page--wide,.cui-page--full{
  width:100%!important;max-width:none!important;margin-left:0!important;margin-right:0!important;
}
.cui-page{padding:var(--cui-page-gutter)!important;}
.cui-shell-mobile-menu.cui-icon-button{display:none!important;}
.cui-mobile-nav-drawer.q-drawer{z-index:calc(var(--cui-overlay-z) - 100)!important;padding:0!important;background:var(--cui-surface)!important;}
.cui-mobile-nav-head{height:58px;display:flex;align-items:center;justify-content:space-between;padding:0 14px;border-bottom:1px solid var(--cui-border-subtle);}
.cui-mobile-nav-title{font-weight:var(--cui-font-weight-700);font-size:var(--cui-font-size-15);}
.cui-mobile-nav-body{height:calc(100dvh - 58px - 132px);overflow:auto;padding:10px 8px;}
.cui-mobile-nav-drawer .cui-sidebar-footer{padding:10px 12px 14px;}

/* Environment metadata uses actual Foundation semantic colors. */
.cui-environment-badge{border:0!important;min-height:24px!important;padding:4px 9px!important;border-radius:var(--cui-radius-pill)!important;font-size:var(--cui-font-size-10)!important;font-weight:var(--cui-font-weight-700)!important;letter-spacing:.035em;display:inline-flex!important;align-items:center!important;}
.cui-environment-badge--development{background:var(--cui-info-soft)!important;color:var(--cui-info)!important;}
.cui-environment-badge--staging{background:var(--cui-warning-soft)!important;color:color-mix(in srgb,var(--cui-warning) 82%,black)!important;}
.cui-environment-badge--production{background:var(--cui-success-soft)!important;color:color-mix(in srgb,var(--cui-success) 82%,black)!important;}
.cui-environment-badge--neutral{background:var(--cui-surface-secondary)!important;color:var(--cui-text-secondary)!important;}

/* Optical centering contract. */
.cui-button.q-btn,.cui-icon-button.q-btn,.cui-menu-item.q-btn,.cui-sidebar-footer__action.q-btn,.cui-user-menu-trigger.q-btn{display:inline-flex!important;align-items:center!important;justify-content:center!important;vertical-align:middle!important;}
.cui-button.q-btn .q-btn__content,.cui-icon-button.q-btn .q-btn__content,.cui-menu-item.q-btn .q-btn__content,.cui-user-menu-trigger.q-btn .q-btn__content{display:flex!important;align-items:center!important;justify-content:center!important;line-height:var(--cui-line-height-ratio-1)!important;min-height:100%!important;}
.cui-button.q-btn .q-btn__content>.q-label,.cui-menu-item.q-btn .q-btn__content>.q-label{line-height:var(--cui-line-height-ratio-1_2)!important;}
.cui-svg-icon-host{display:inline-grid!important;place-items:center!important;line-height:0!important;vertical-align:middle!important;}
.cui-svg-icon-host svg{display:block!important;margin:auto!important;overflow:visible!important;}
.cui-badge,.cui-chip,.cui-count-badge,.cui-table-status,.cui-eng-status,.cui-semantic-indicator{display:inline-flex!important;align-items:center!important;justify-content:center!important;line-height:var(--cui-line-height-ratio-1)!important;vertical-align:middle!important;}
.cui-count-badge{min-width:24px!important;height:24px!important;padding:0 7px!important;}

/* Field label/required marker and inner control centering. */
.cui-field,.cui-form-field{display:flex!important;flex-direction:column!important;gap:7px!important;}
.cui-field-label-row{display:flex!important;align-items:center!important;justify-content:flex-start!important;gap:4px!important;min-height:20px!important;}
.cui-field-label,.cui-field-required{display:inline-flex!important;align-items:center!important;line-height:var(--cui-line-height-20)!important;margin:0!important;}
.cui-field-required{transform:translateY(-.5px);}
.cui-field-control.q-field{height:auto!important;min-height:var(--cui-control-height)!important;overflow:visible!important;}
.cui-field-control.q-field:not(.q-textarea) .q-field__inner,.cui-field-control.q-field:not(.q-textarea) .q-field__control{height:var(--cui-control-height)!important;min-height:var(--cui-control-height)!important;}
.cui-field-control.q-field .q-field__control-container,.cui-field-control.q-field .q-field__native,.cui-field-control.q-field .q-field__input{height:100%!important;min-height:0!important;display:flex!important;align-items:center!important;padding-block:0!important;line-height:var(--cui-line-height-ratio-1_25)!important;}
.cui-field-control.q-field .q-field__prepend,.cui-field-control.q-field .q-field__append{height:100%!important;min-height:0!important;display:flex!important;align-items:center!important;justify-content:center!important;padding:0 0 0 8px!important;}
.cui-field-control.q-field .q-field__append>*{display:grid!important;place-items:center!important;}
/* Replace the Material dropdown glyph with a crisp Company chevron mask. */
.cui-field-control.q-select .q-field__append .q-icon:not(.q-field__focusable-action){font-size:0!important;width:18px!important;height:18px!important;position:relative!important;color:var(--cui-text-tertiary)!important;}
.cui-field-control.q-select .q-field__append .q-icon:not(.q-field__focusable-action)::after{content:''!important;position:absolute!important;inset:3px!important;background:currentColor!important;mask:url("data:image/svg+xml,%3Csvg xmlns='http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg' viewBox='0 0 16 16'%3E%3Cpath fill='black' d='M3.2 5.6a.8.8 0 0 1 1.13 0L8 9.27l3.67-3.67a.8.8 0 1 1 1.13 1.13l-4.24 4.24a.8.8 0 0 1-1.12 0L3.2 6.73a.8.8 0 0 1 0-1.13Z'/%3E%3C/svg%3E") center/14px 14px no-repeat!important;transform:none!important;border:0!important;}
.cui-field-control.q-field .q-field__focusable-action{font-size:0!important;width:18px!important;height:18px!important;position:relative!important;}
.cui-field-control.q-field .q-field__focusable-action::after{content:'';position:absolute;inset:3px;background:currentColor;mask:url("data:image/svg+xml,%3Csvg xmlns='http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg' viewBox='0 0 16 16'%3E%3Cpath fill='black' d='M4.2 3.07 8 6.87l3.8-3.8 1.13 1.13L9.13 8l3.8 3.8-1.13 1.13L8 9.13l-3.8 3.8-1.13-1.13L6.87 8l-3.8-3.8L4.2 3.07Z'/%3E%3C/svg%3E") center/13px 13px no-repeat;}
.cui-field-control.q-textarea .q-field__control{height:auto!important;min-height:104px!important;align-items:flex-start!important;}
.cui-field-control.q-textarea .q-field__native{min-height:104px!important;height:auto!important;align-items:flex-start!important;padding:12px 0!important;resize:vertical!important;}

/* Choice controls: only the actual control gets state/focus, never the entire group. */
.cui-radio-group{display:flex!important;flex-direction:column!important;align-items:flex-start!important;gap:8px!important;border:0!important;box-shadow:none!important;outline:0!important;padding:0!important;}
.cui-radio-group>.q-radio{min-height:34px!important;display:flex!important;align-items:center!important;border-radius:var(--cui-radius-inner)!important;padding:3px 6px 3px 2px!important;}
.cui-radio-group>.q-radio:focus-within{background:var(--cui-surface-hover)!important;outline:0!important;box-shadow:none!important;}
.cui-choice.q-checkbox{display:flex!important;align-items:center!important;gap:8px!important;min-height:34px!important;}
.cui-choice.q-checkbox .q-checkbox__label{display:flex!important;align-items:center!important;line-height:var(--cui-line-height-ratio-1_25)!important;}
.cui-slider.q-slider{outline:0!important;border:0!important;box-shadow:none!important;}
.cui-slider.q-slider:focus-visible{outline:0!important;}
.cui-slider.q-slider .q-slider__focus-ring{width:30px!important;height:30px!important;border-radius:var(--cui-radius-circle)!important;background:color-mix(in srgb,var(--cui-accent) 14%,transparent)!important;color:transparent!important;}
.cui-slider.q-slider .q-slider__thumb{border-radius:var(--cui-radius-circle)!important;}

/* Select/list menus and every top-layer overlay must be visible above the header. */
.q-menu.cui-menu,.q-menu.cui-user-menu,.q-menu.cui-popover,.q-menu[role='listbox']{z-index:var(--cui-overlay-z)!important;background:var(--cui-surface-elevated)!important;color:var(--cui-text-primary)!important;border:1px solid var(--cui-border-subtle)!important;border-radius:var(--cui-radius-overlay)!important;box-shadow:0 18px 54px rgba(0,0,0,.18)!important;padding:7px!important;overflow:hidden!important;}
.q-menu[role='listbox']{padding:6px!important;min-width:180px!important;max-height:min(420px,calc(100dvh - 40px))!important;}
.q-menu[role='listbox'] .q-virtual-scroll__content{display:flex!important;flex-direction:column!important;gap:3px!important;}
.q-menu[role='listbox'] .q-item{min-height:38px!important;padding:7px 10px!important;border-radius:var(--cui-radius-control)!important;display:flex!important;align-items:center!important;}
.cui-menu-item.q-btn{min-height:38px!important;height:auto!important;padding:8px 10px!important;border-radius:var(--cui-radius-control)!important;margin:0!important;}
.cui-menu-item.q-btn+.cui-menu-item.q-btn{margin-top:3px!important;}
.cui-menu-item.q-btn .q-btn__content{justify-content:flex-start!important;gap:9px!important;}
.cui-menu-separator{margin:6px 4px!important;}
.cui-tooltip.q-tooltip,.q-tooltip.cui-tooltip{z-index:calc(var(--cui-overlay-z) + 100)!important;margin:0!important;padding:7px 9px!important;border-radius:var(--cui-radius-inner)!important;box-shadow:0 8px 24px rgba(0,0,0,.18)!important;}
.q-dialog{z-index:calc(var(--cui-overlay-z) - 50)!important;}
.q-dialog__inner{padding:var(--cui-overlay-edge-gap)!important;}
.cui-dialog{max-width:calc(100vw - (var(--cui-overlay-edge-gap)*2))!important;max-height:calc(100dvh - (var(--cui-overlay-edge-gap)*2))!important;}
.cui-dialog--full{width:calc(100vw - (var(--cui-overlay-edge-gap)*2))!important;height:calc(100dvh - (var(--cui-overlay-edge-gap)*2))!important;border-radius:var(--cui-radius-overlay)!important;}
.cui-dialog__head,.cui-drawer__header{display:flex!important;align-items:center!important;gap:14px!important;}
.cui-dialog__copy,.cui-drawer__header>div:first-child{flex:1 1 auto!important;min-width:0!important;}
.cui-dialog__title,.cui-drawer__title{line-height:var(--cui-line-height-ratio-1_25)!important;margin:0!important;}
.cui-dialog__head>.cui-icon-button,.cui-drawer__header>.cui-icon-button{flex:0 0 var(--cui-icon-button-size)!important;align-self:center!important;}
.cui-drawer{top:var(--cui-overlay-edge-gap)!important;bottom:var(--cui-overlay-edge-gap)!important;height:auto!important;border-radius:var(--cui-radius-overlay)!important;overflow:hidden!important;}
.cui-drawer--right{right:var(--cui-overlay-edge-gap)!important;}
.cui-drawer--left{left:var(--cui-overlay-edge-gap)!important;}

/* Toasts always clear the fixed application header. */
.cui-toast-stack{top:calc(var(--cui-shell-header-height) + 16px)!important;right:20px!important;z-index:var(--cui-toast-z)!important;gap:10px!important;}
.cui-toast{border-radius:var(--cui-radius-overlay)!important;}

/* Progress/loading optical hierarchy. */
.cui-progress.q-linear-progress,.cui-progress{height:10px!important;min-height:10px!important;border-radius:var(--cui-radius-pill)!important;}
.cui-progress-metric{display:flex!important;flex-direction:column!important;gap:8px!important;}
.cui-progress-metric__value{font-size:var(--cui-font-size-12)!important;line-height:var(--cui-line-height-16)!important;}

/* Modern interactive surfaces: cards remain cards, not elongated pills. */
.cui-surface--interactive,.cui-interactive-card{min-height:108px!important;border-radius:var(--cui-radius-surface)!important;background:var(--cui-surface)!important;padding:var(--cui-surface-padding)!important;box-shadow:inset 0 0 0 1px var(--cui-border-subtle)!important;transition:background var(--cui-duration-feedback) var(--cui-easing-native),box-shadow var(--cui-duration-feedback) var(--cui-easing-native),transform var(--cui-duration-micro) var(--cui-easing-native)!important;}
.cui-surface--interactive:hover,.cui-interactive-card:hover{background:var(--cui-surface-hover)!important;box-shadow:inset 0 0 0 1px var(--cui-border-default),0 6px 20px rgba(0,0,0,.06)!important;}

/* Engineering metadata: values live inside padded semantic cells; text never collides with rounded boundaries. */
.cui-eng-entity{gap:var(--cui-stack-gap)!important;padding:var(--cui-surface-padding)!important;border-radius:var(--cui-radius-surface)!important;border-color:var(--cui-border-subtle)!important;}
.cui-eng-entity__head{align-items:center!important;gap:14px!important;}
.cui-eng-property-grid{display:grid!important;grid-template-columns:repeat(auto-fit,minmax(148px,1fr))!important;gap:10px!important;}
.cui-eng-property{display:flex!important;flex-direction:column!important;gap:4px!important;min-width:0!important;padding:10px 12px!important;border-radius:var(--cui-radius-control)!important;background:var(--cui-surface-secondary)!important;box-shadow:inset 0 0 0 1px var(--cui-border-subtle)!important;}
.cui-eng-property__label{font-size:var(--cui-font-size-10)!important;line-height:var(--cui-line-height-14)!important;font-weight:var(--cui-font-weight-650)!important;text-transform:uppercase!important;letter-spacing:.045em!important;color:var(--cui-text-tertiary)!important;}
.cui-eng-property__value{font-size:var(--cui-font-size-13)!important;line-height:var(--cui-line-height-18)!important;font-weight:var(--cui-font-weight-650)!important;color:var(--cui-text-primary)!important;overflow-wrap:anywhere!important;}

/* Dense data ergonomics and action clarity. */
.cui-table-toolbar{display:flex!important;align-items:center!important;gap:10px!important;}
.cui-table-toolbar>.cui-icon-button{background:var(--cui-surface-secondary)!important;}
.cui-table-toolbar__actions{position:relative!important;z-index:auto!important;}
.cui-table-row-actions,.cui-table-context-actions{display:flex!important;align-items:center!important;gap:4px!important;}
.cui-data-table .ag-cell{display:flex!important;align-items:center!important;line-height:var(--cui-line-height-ratio-1_25)!important;}
.cui-data-table .ag-cell.is-numeric{justify-content:flex-end!important;}
.cui-data-table .ag-cell.is-center{justify-content:center!important;}
.cui-data-table .ag-header-cell-label{align-items:center!important;gap:6px!important;}
.cui-data-table .ag-menu,.ag-popup .ag-menu{border-radius:var(--cui-radius-overlay)!important;box-shadow:0 18px 54px rgba(0,0,0,.16)!important;}

/* Chart collision/interaction safety. */
.cui-chart-panel__header{display:flex!important;align-items:flex-start!important;justify-content:space-between!important;gap:16px!important;}
.cui-chart-toolbar-host{flex:0 0 auto!important;}
.cui-chart-toolbar{display:flex!important;align-items:center!important;gap:4px!important;flex-wrap:nowrap!important;}
.cui-spatial-viewport{box-shadow:none!important;}
.cui-spatial-grid-outline{stroke:var(--cui-border-default)!important;}

/* Workflow nodes: content is optically centered; long copy belongs outside. */
.cui-progress-steps{display:flex!important;align-items:flex-start!important;gap:12px!important;padding:4px 0 8px!important;}
.cui-progress-step{display:grid!important;grid-template-columns:30px minmax(0,1fr)!important;grid-template-rows:auto!important;column-gap:9px!important;row-gap:4px!important;align-items:center!important;min-width:138px!important;}
.cui-progress-step::after{grid-column:2!important;align-self:center!important;margin:0!important;}
.cui-progress-step__marker,.cui-stepper__marker,.cui-step-marker{width:30px!important;height:30px!important;min-width:30px!important;display:grid!important;place-items:center!important;text-align:center!important;line-height:var(--cui-line-height-ratio-1)!important;}
.cui-progress-step__marker .cui-svg-icon-host,.cui-progress-step__marker svg{display:block!important;margin:auto!important;}
.cui-progress-step__label{line-height:var(--cui-line-height-18)!important;align-self:center!important;margin:0!important;}

/* Analytical image viewer: explicit controls + inspectable pan/zoom viewport. */
.cui-image-viewer{display:flex!important;flex-direction:column!important;gap:10px!important;min-width:0!important;padding:0!important;overflow:hidden!important;border-radius:var(--cui-radius-surface)!important;background:var(--cui-surface)!important;box-shadow:inset 0 0 0 1px var(--cui-border-subtle)!important;}
.cui-image-viewer__toolbar{display:flex!important;align-items:center!important;justify-content:space-between!important;gap:12px!important;padding:10px 12px 0!important;}
.cui-image-viewer__caption{font-size:var(--cui-font-size-12)!important;line-height:var(--cui-line-height-18)!important;font-weight:var(--cui-font-weight-650)!important;color:var(--cui-text-secondary)!important;min-width:0!important;overflow:hidden!important;text-overflow:ellipsis!important;white-space:nowrap!important;}
.cui-image-viewer__actions{display:flex!important;align-items:center!important;gap:4px!important;flex:0 0 auto!important;}
.cui-image-viewer__viewport{height:320px!important;min-height:240px!important;margin:0 10px 10px!important;border-radius:var(--cui-radius-control)!important;overflow:hidden!important;display:grid!important;place-items:center!important;background:var(--cui-surface-secondary)!important;cursor:zoom-in!important;}
.cui-image-viewer__viewport.is-dragging{cursor:grabbing!important;}
.cui-image-viewer__image{display:block!important;max-width:100%!important;max-height:100%!important;width:auto!important;height:auto!important;object-fit:contain!important;transform-origin:center center!important;transition:transform var(--cui-duration-micro) var(--cui-easing-native)!important;user-select:none!important;pointer-events:none!important;}

@media(max-width:899px){
  .cui-app-sidebar:not(.q-drawer){display:none!important;}
  .cui-app-main--with-sidebar,html[data-sidebar='compact'] .cui-app-main--with-sidebar{margin-left:0!important;width:100%!important;max-width:100%!important;padding-left:0!important;}
  .cui-shell-mobile-menu.cui-icon-button{display:inline-flex!important;}
  .cui-page-header{padding-bottom:14px!important;}
}
@media(min-width:900px){
  .cui-mobile-nav-drawer.q-drawer{display:none!important;transform:translateX(-110%)!important;}
}
@media(max-width:599px){
  .q-dialog__inner{padding:12px!important;}
  .cui-dialog,.cui-dialog--full{width:calc(100vw - 24px)!important;height:auto;max-height:calc(100dvh - 24px)!important;border-radius:var(--cui-radius-overlay)!important;}
  .cui-dialog--full{height:calc(100dvh - 24px)!important;}
  .cui-drawer{top:8px!important;bottom:8px!important;right:8px!important;left:8px!important;width:auto!important;}
  .cui-shell-actions{gap:5px!important;}
  .cui-shell-user{padding:3px!important;background:transparent!important;}
}

/* v1.6 visual hierarchy: intent is carried by fill/tint, never arbitrary outlines. */
.cui-button--primary{background:var(--cui-accent)!important;color:#fff!important;box-shadow:0 1px 2px rgba(0,0,0,.08),0 6px 18px color-mix(in srgb,var(--cui-accent) 15%,transparent)!important;}
.cui-button--secondary{background:color-mix(in srgb,var(--cui-text-primary) 8%,var(--cui-surface))!important;color:var(--cui-text-primary)!important;}
.cui-button--tertiary{background:var(--cui-accent-soft)!important;color:var(--cui-accent)!important;}
.cui-button--ghost{background:transparent!important;color:var(--cui-text-secondary)!important;}
.cui-button--danger{background:var(--cui-danger)!important;color:#fff!important;box-shadow:0 1px 2px rgba(0,0,0,.08)!important;}
.cui-button--primary,.cui-button--secondary,.cui-button--tertiary,.cui-button--ghost,.cui-button--danger{border:0!important;}
.cui-icon-button--ghost{background:color-mix(in srgb,var(--cui-text-primary) 6%,var(--cui-surface))!important;color:var(--cui-text-secondary)!important;}
.cui-icon-button--tertiary{background:var(--cui-accent-soft)!important;color:var(--cui-accent)!important;}
.cui-icon-button:hover{background:var(--cui-surface-hover)!important;color:var(--cui-text-primary)!important;}

/* Field-label + control anatomy is one flow; helpers never create accidental rows. */
.cui-field{display:flex!important;flex-direction:column!important;align-items:stretch!important;gap:7px!important;min-width:0!important;}
.cui-field-label-row{display:flex!important;align-items:baseline!important;min-height:18px!important;gap:5px!important;}
.cui-field-label-row>div{display:inline-flex!important;align-items:baseline!important;gap:4px!important;min-width:0!important;}
.cui-field-label,.cui-field-required{line-height:var(--cui-line-height-18)!important;margin:0!important;}
.cui-field-required{color:var(--cui-danger)!important;font-weight:var(--cui-font-weight-650)!important;}
.cui-field-description,.cui-field-error{margin:0!important;line-height:var(--cui-line-height-18)!important;}
.cui-choice-field{display:flex!important;flex-direction:column!important;gap:3px!important;align-items:flex-start!important;min-width:0!important;}
.cui-choice-description{padding-left:2px!important;}

/* Clipboard-aware upload shell. */
.cui-upload-shell{display:flex!important;flex-direction:column!important;gap:10px!important;width:100%!important;padding:14px!important;border-radius:var(--cui-radius-surface)!important;background:var(--cui-surface-secondary)!important;box-shadow:inset 0 0 0 1px var(--cui-border-subtle)!important;outline:0!important;}
.cui-upload-shell:focus-visible{box-shadow:inset 0 0 0 1px var(--cui-accent),0 0 0 3px var(--cui-focus-ring)!important;}
.cui-upload-shell__copy{display:flex!important;flex-direction:column!important;gap:2px!important;}
.cui-upload.q-uploader{width:100%!important;max-width:none!important;border-radius:var(--cui-radius-control)!important;overflow:hidden!important;box-shadow:none!important;background:var(--cui-surface)!important;}
.cui-upload.q-uploader .q-uploader__header{min-height:44px!important;padding:8px 10px!important;background:transparent!important;color:var(--cui-text-primary)!important;}
.cui-upload.q-uploader .q-uploader__list{min-height:72px!important;padding:8px!important;background:var(--cui-surface)!important;}

/* Collapse/disclosure uses the same radius and a short, deliberate transition. */
.cui-collapsible.q-expansion-item{border-radius:var(--cui-radius-surface)!important;overflow:hidden!important;background:var(--cui-surface)!important;box-shadow:inset 0 0 0 1px var(--cui-border-subtle)!important;}
.cui-collapsible .q-item{min-height:var(--cui-control-height)!important;padding:0 12px!important;}

/* Motion replay is visually testable and includes the real application title. */
.cui-shell-title.is-replaying{animation:cui-v16-app-title var(--cui-duration-title-lux) var(--cui-easing-standard) both!important;}
.cui-motion-status{display:inline-flex!important;align-items:center!important;min-height:28px!important;padding:4px 9px!important;border-radius:var(--cui-radius-pill)!important;background:var(--cui-info-soft)!important;color:var(--cui-info)!important;font-size:var(--cui-font-size-12)!important;font-weight:var(--cui-font-weight-650)!important;}

/* Semantic icon gallery must render the actual local SVG, not a string placeholder. */
.cui-lab-icon-tile{display:flex!important;flex-direction:column!important;align-items:center!important;justify-content:center!important;gap:8px!important;min-width:86px!important;min-height:78px!important;padding:10px!important;border-radius:var(--cui-radius-surface)!important;background:var(--cui-surface-secondary)!important;text-align:center!important;}
.cui-lab-icon-tile .cui-svg-icon-host{width:22px!important;height:22px!important;color:var(--cui-text-primary)!important;}

/* Overlay anchor breathing room and uniformly rounded list surfaces. */
.q-menu.cui-menu,.q-menu.cui-user-menu,.q-menu.cui-popover{margin-top:8px!important;}
.cui-dialog__body,.cui-drawer__body{min-width:0!important;overflow:auto!important;}
.cui-dialog__footer{display:flex!important;align-items:center!important;justify-content:flex-end!important;gap:8px!important;padding-top:14px!important;}

/* Spatial visualization frame should fit the actual custom renderer. */
.cui-spatial-panel,.cui-wafer-map,.cui-spatial-map{min-width:0!important;overflow:hidden!important;}
.cui-spatial-viewport{width:100%!important;max-width:100%!important;border-radius:var(--cui-radius-surface)!important;overflow:hidden!important;}




/* Semiconductor-native comparison renderers. */
.cui-spatial-panel .cui-spatial-viewport{box-shadow:none!important;background:var(--cui-surface-secondary)!important;}
.cui-spatial-compare-title{fill:var(--cui-text-primary);font-size:var(--cui-font-size-12);font-weight:var(--cui-font-weight-750);letter-spacing:.07em;}
.cui-spatial-compare-subtitle{fill:var(--cui-text-tertiary);font-size:var(--cui-font-size-10);font-weight:var(--cui-font-weight-550);}
.cui-wafer-guide-ring{fill:none;stroke:var(--cui-border-subtle);stroke-width:1;stroke-dasharray:3 5;}
.cui-radial-grid{stroke:var(--cui-border-subtle);stroke-width:1;}
.cui-radial-axis{stroke:var(--cui-border-default);stroke-width:1.2;}
.cui-radial-profile{fill:none;stroke-width:2.6;stroke-linecap:round;stroke-linejoin:round;}
.cui-radial-profile--affected{stroke:var(--cui-danger);}
.cui-radial-profile--control{stroke:var(--cui-info);}
.cui-radial-point--affected{fill:var(--cui-danger);stroke:var(--cui-surface);stroke-width:1.5;}
.cui-radial-point--control{fill:var(--cui-info);stroke:var(--cui-surface);stroke-width:1.5;}


/* Canonical page patterns are grids inside the full-width page canvas.
   Normal pages remain vertical stacks; pattern geometry must not be flattened by .cui-page. */
.cui-page.cui-pattern{display:grid!important;width:100%!important;max-width:none!important;min-width:0!important;align-items:start!important;row-gap:var(--cui-content-gap)!important;column-gap:var(--cui-content-gap)!important;}
.cui-pattern-slot{width:100%!important;max-width:100%!important;min-width:0!important;align-self:start!important;}
.cui-pattern-slot--filters{padding:12px 14px!important;border:0!important;border-radius:var(--cui-radius-surface)!important;background:var(--cui-surface-secondary)!important;box-shadow:inset 0 0 0 1px var(--cui-border-subtle)!important;}
.cui-pattern-slot--actions{gap:var(--cui-cluster-gap)!important;}
.cui-pattern-slot--metrics:has(> .cui-metric-card),.cui-pattern-slot--metrics:has(> .cui-metric-strip){gap:var(--cui-stack-gap)!important;}
/* Reading-width is an inner content decision, never an outer-canvas decision. */
.cui-pattern--wizard .cui-pattern-slot--navigation,.cui-pattern--wizard .cui-pattern-slot--content,.cui-pattern--wizard .cui-pattern-slot--actions{width:min(100%,860px)!important;justify-self:center!important;}
.cui-pattern--settings .cui-pattern-slot--content,.cui-pattern--settings .cui-pattern-slot--actions{width:min(100%,980px)!important;}
.cui-pattern--data_explorer .cui-pattern-slot--data,.cui-pattern--crud .cui-pattern-slot--data,.cui-pattern--master_detail .cui-pattern-slot--data,.cui-pattern--analysis_workspace .cui-pattern-slot--data{width:100%!important;max-width:none!important;}

/* Full-width flagship data surfaces follow the shell canvas; never introduce a second outer centering width. */
.cui-table-shell,.cui-data-table,.cui-chart-panel,.cui-engineering-workspace{width:100%!important;max-width:100%!important;min-width:0!important;}
.cui-table-shell>.cui-data-table{width:100%!important;}

/* Overlays are portal surfaces: never clip under the fixed application header and always keep viewport breathing room. */
.cui-app-header{overflow:visible!important;}
.q-menu.cui-menu,.q-menu.cui-popover,.cui-tooltip{z-index:var(--cui-overlay-z)!important;max-width:min(420px,calc(100vw - 2 * var(--cui-overlay-edge-gap)))!important;}
.q-menu.cui-menu,.q-menu.cui-popover{max-height:calc(100vh - var(--cui-shell-header-height) - 2 * var(--cui-overlay-edge-gap))!important;overflow:auto!important;border-radius:var(--cui-radius-overlay)!important;}
.cui-toast-stack{top:calc(var(--cui-shell-header-height) + 16px)!important;right:20px!important;bottom:auto!important;}

/* Semantic state uses tinted surfaces and text rather than a rainbow of outlined rectangles. */
.cui-eng-status,.cui-status-badge,.cui-severity-badge,.cui-data-quality-badge{border:0!important;box-shadow:none!important;}

/* AG Grid action cells and filter editor are explicit Company controls. */
.cui-data-table .cui-table-action-cell{justify-content:center!important;padding-inline:5px!important;cursor:pointer!important;}
.cui-table-row-action{display:inline-flex!important;align-items:center!important;justify-content:center!important;gap:5px!important;min-height:28px!important;padding:4px 9px!important;border:1px solid var(--cui-border-subtle)!important;border-radius:var(--cui-radius-inner)!important;background:var(--cui-surface)!important;color:var(--cui-text-secondary)!important;font-size:var(--cui-font-size-11)!important;font-weight:var(--cui-font-weight-650)!important;line-height:var(--cui-line-height-16)!important;white-space:nowrap!important;transition:background var(--cui-duration-fast) var(--cui-easing-native),color var(--cui-duration-fast) var(--cui-easing-native),border-color var(--cui-duration-fast) var(--cui-easing-native)!important;}
.cui-table-row-action__icon{width:14px!important;height:14px!important;display:grid!important;place-items:center!important;}
.cui-table-row-action__icon .cui-svg-icon{width:14px!important;height:14px!important;}
.cui-table-action-cell:hover .cui-table-row-action{background:var(--cui-accent-soft)!important;color:var(--cui-accent)!important;border-color:color-mix(in srgb,var(--cui-accent) 20%,var(--cui-border-subtle))!important;}
.cui-table-context-menu{margin:6px!important;}
.ag-popup .ag-filter,.cui-data-table .ag-filter{padding:10px!important;min-width:220px!important;}
.ag-popup .ag-filter .ag-input-field,.cui-data-table .ag-filter .ag-input-field{display:flex!important;align-items:center!important;min-height:36px!important;border-radius:var(--cui-radius-control)!important;}
.ag-popup .ag-filter .ag-input-field-before,.cui-data-table .ag-filter .ag-input-field-before{display:none!important;}
.ag-popup .ag-filter .ag-input-field-input,.cui-data-table .ag-filter .ag-input-field-input{height:36px!important;padding:7px 10px!important;line-height:var(--cui-line-height-20)!important;border-radius:var(--cui-radius-control)!important;}
.ag-popup .ag-filter .ag-filter-body-wrapper,.cui-data-table .ag-filter .ag-filter-body-wrapper{display:flex!important;flex-direction:column!important;gap:8px!important;}


/* ================================================================
   COMPANY UI v1.7 PHASE 1 — PRODUCT SHELL CONSTITUTION
   Apple × Linear foundation: one shell geometry, one responsive nav.
   ================================================================ */
:root{
  --cui-shell-hairline:color-mix(in srgb,var(--cui-border-subtle) 82%,transparent);
}

/* Company owns the fixed header; no q-header/QLayout geometry participates. */
.cui-app-header{
  position:fixed!important;inset:0 0 auto 0!important;height:var(--cui-shell-header-height)!important;min-height:var(--cui-shell-header-height)!important;
  z-index:var(--cui-app-header-z)!important;display:flex!important;align-items:center!important;gap:14px!important;
  padding:0 18px!important;margin:0!important;
  background:color-mix(in srgb,var(--cui-surface) 94%,transparent)!important;
  border-bottom:1px solid var(--cui-shell-hairline)!important;
  box-shadow:none!important;backdrop-filter:saturate(145%) blur(16px);-webkit-backdrop-filter:saturate(145%) blur(16px);
}
.cui-shell-brand{display:flex!important;align-items:center!important;gap:0!important;flex:1 1 auto!important;min-width:0!important;}
.cui-shell-title-block{display:flex!important;flex-direction:column!important;justify-content:center!important;gap:1px!important;min-width:0!important;}
.cui-shell-title{font-size:var(--cui-font-size-14)!important;line-height:var(--cui-line-height-18)!important;font-weight:var(--cui-font-weight-720)!important;letter-spacing:-.012em!important;color:var(--cui-text-primary)!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important;}
.cui-shell-subtitle{font-size:var(--cui-font-size-10_5)!important;line-height:var(--cui-line-height-14)!important;color:var(--cui-text-tertiary)!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important;}
.cui-shell-actions{display:flex!important;align-items:center!important;justify-content:flex-end!important;gap:6px!important;flex:0 0 auto!important;margin-left:auto!important;}
.cui-shell-user{display:flex!important;align-items:center!important;gap:7px!important;padding:0!important;background:transparent!important;}
.cui-shell-greeting{display:flex!important;flex-direction:column!important;align-items:flex-end!important;justify-content:center!important;gap:0!important;}
.cui-shell-greeting__hello{font-size:var(--cui-font-size-9_5)!important;line-height:var(--cui-line-height-12)!important;color:var(--cui-text-tertiary)!important;}
.cui-shell-greeting__name{font-size:var(--cui-font-size-11)!important;line-height:var(--cui-line-height-14)!important;font-weight:var(--cui-font-weight-650)!important;color:var(--cui-text-secondary)!important;}
.cui-shell-mobile-menu.cui-icon-button{display:none!important;order:-1;}

/* View content begins exactly one page gutter below the header boundary. */
.cui-app-main{padding-top:var(--cui-shell-header-height)!important;min-height:100dvh!important;}
.cui-page{padding:var(--cui-page-gutter)!important;}
.cui-page-header{align-items:flex-start!important;padding:0 0 14px!important;gap:16px!important;}
.cui-page-header__copy{gap:3px!important;}
.cui-page-title{font-size:var(--cui-font-size-24)!important;line-height:var(--cui-line-height-29)!important;font-weight:var(--cui-font-weight-720)!important;letter-spacing:-.025em!important;}
.cui-page-description{font-size:var(--cui-font-size-12_5)!important;line-height:var(--cui-line-height-18)!important;color:var(--cui-text-secondary)!important;}

/* Desktop navigation: no extra shell/header trigger and no compressed footer text. */
.cui-app-sidebar:not(.q-drawer){top:var(--cui-shell-header-height)!important;width:var(--cui-shell-sidebar-width)!important;padding:8px 7px 8px!important;}
.cui-sidebar-top{height:38px!important;padding:0 2px 5px!important;justify-content:flex-end!important;}
.cui-sidebar-collapse.q-btn{width:34px!important;height:34px!important;min-width:34px!important;min-height:34px!important;border-radius:var(--cui-radius-control)!important;background:transparent!important;color:var(--cui-text-tertiary)!important;}
.cui-sidebar-collapse.q-btn:hover{background:var(--cui-surface-secondary)!important;color:var(--cui-text-primary)!important;}
.cui-sidebar-collapse__expanded,.cui-sidebar-collapse__compact{display:grid;place-items:center;width:18px;height:18px;}
.cui-sidebar-collapse__compact{display:none;}
html[data-sidebar='compact'] .cui-sidebar-collapse__expanded{display:none;}
html[data-sidebar='compact'] .cui-sidebar-collapse__compact{display:grid;}
.cui-nav-section{gap:3px!important;margin-bottom:10px!important;}
.cui-nav-section-label{height:20px!important;padding:2px 10px!important;font-size:var(--cui-font-size-9)!important;line-height:var(--cui-line-height-16)!important;letter-spacing:.07em!important;text-transform:uppercase!important;color:var(--cui-text-tertiary)!important;}
.cui-nav-item.q-item,.cui-nav-item{min-height:38px!important;height:38px!important;padding:0 7px!important;border-radius:var(--cui-radius-control)!important;}
.cui-nav-item__icon.q-item__section--avatar,.cui-nav-item__icon{min-width:32px!important;width:32px!important;height:32px!important;}
.cui-nav-item--active{background:var(--cui-accent-soft)!important;color:var(--cui-accent)!important;}
.cui-nav-item:not(.cui-nav-item--active):hover{background:var(--cui-surface-secondary)!important;}
.cui-sidebar-footer{padding:8px 2px 0!important;gap:6px!important;background:var(--cui-surface)!important;}
.cui-sidebar-owner{min-height:34px!important;padding:4px 6px!important;border-radius:var(--cui-radius-control)!important;}
.cui-sidebar-footer__actions{gap:2px!important;}
.cui-sidebar-footer__action.q-btn{width:100%!important;height:34px!important;min-height:34px!important;padding:0 7px!important;border-radius:var(--cui-radius-control)!important;}
html[data-sidebar='compact'] .cui-sidebar-owner{width:36px!important;height:36px!important;min-height:36px!important;margin-inline:auto!important;padding:0!important;display:grid!important;place-items:center!important;}
html[data-sidebar='compact'] .cui-sidebar-owner__copy{display:none!important;}
html[data-sidebar='compact'] .cui-sidebar-footer__actions{align-items:center!important;}
html[data-sidebar='compact'] .cui-sidebar-footer__action.q-btn{width:36px!important;height:36px!important;min-width:36px!important;min-height:36px!important;padding:0!important;}
html[data-sidebar='compact'] .cui-sidebar-footer__action.q-btn .q-btn__content{width:36px!important;height:36px!important;display:grid!important;place-items:center!important;}
html[data-sidebar='compact'] .cui-sidebar-footer__action.q-btn .q-btn__content>.q-label{display:none!important;}

/* Environment: neutral readable surface + semantic dot, including dark mode. */
.cui-environment-badge{position:relative!important;gap:6px!important;min-height:24px!important;padding:4px 9px 4px 8px!important;background:var(--cui-surface-secondary)!important;color:var(--cui-text-secondary)!important;box-shadow:inset 0 0 0 1px var(--cui-border-subtle)!important;}
.cui-environment-badge::before{content:'';display:block;width:6px;height:6px;border-radius:var(--cui-radius-circle);background:var(--cui-text-tertiary);box-shadow:0 0 0 2px color-mix(in srgb,var(--cui-text-tertiary) 12%,transparent);}
.cui-environment-badge--development::before{background:var(--cui-info);box-shadow:0 0 0 2px color-mix(in srgb,var(--cui-info) 14%,transparent);}
.cui-environment-badge--staging::before{background:var(--cui-warning);box-shadow:0 0 0 2px color-mix(in srgb,var(--cui-warning) 14%,transparent);}
.cui-environment-badge--production::before{background:var(--cui-success);box-shadow:0 0 0 2px color-mix(in srgb,var(--cui-success) 14%,transparent);}
.cui-environment-badge--neutral::before{background:var(--cui-text-tertiary);}
.cui-environment-badge--development,.cui-environment-badge--staging,.cui-environment-badge--production,.cui-environment-badge--neutral{color:var(--cui-text-secondary)!important;background:var(--cui-surface-secondary)!important;}

/* Real settings/profile popovers have structure even when actions are app callbacks. */
.cui-account-popover{width:min(320px,calc(100vw - 24px))!important;padding:8px!important;}
.cui-account-popover__head,.cui-account-popover__identity{display:flex!important;flex-direction:column!important;gap:2px!important;padding:8px 9px 10px!important;}
.cui-account-popover__identity{flex-direction:row!important;align-items:center!important;gap:10px!important;}
.cui-account-popover__identity-copy{display:flex!important;flex-direction:column!important;gap:1px!important;min-width:0!important;}
.cui-account-avatar{display:grid!important;place-items:center!important;width:34px!important;height:34px!important;min-width:34px!important;border-radius:var(--cui-radius-circle)!important;background:var(--cui-accent-soft)!important;color:var(--cui-accent)!important;font-size:var(--cui-font-size-11)!important;font-weight:var(--cui-font-weight-750)!important;}
.cui-account-popover__title{font-size:var(--cui-font-size-12)!important;line-height:var(--cui-line-height-16)!important;font-weight:var(--cui-font-weight-720)!important;color:var(--cui-text-primary)!important;}
.cui-account-popover__subtitle{font-size:var(--cui-font-size-10_5)!important;line-height:var(--cui-line-height-14)!important;color:var(--cui-text-tertiary)!important;}
.cui-account-popover__meta{display:flex!important;flex-direction:column!important;gap:1px!important;padding:6px!important;margin:0 2px 6px!important;border-radius:var(--cui-radius-control)!important;background:var(--cui-surface-secondary)!important;}
.cui-account-popover__meta-row{display:flex!important;align-items:center!important;justify-content:space-between!important;gap:12px!important;min-height:28px!important;padding:4px 6px!important;}
.cui-account-popover__key{font-size:var(--cui-font-size-10_5)!important;color:var(--cui-text-tertiary)!important;}
.cui-account-popover__value{font-size:var(--cui-font-size-10_5)!important;font-weight:var(--cui-font-weight-650)!important;color:var(--cui-text-secondary)!important;text-align:right!important;}
.cui-menu-item--with-icon.q-btn .q-btn__content{justify-content:flex-start!important;width:100%!important;gap:8px!important;}

/* Company-owned mobile overlay. Exactly one nav system is interactive per viewport. */
.cui-mobile-nav-layer{display:none!important;}
@media(max-width:899px){
  .cui-app-sidebar:not(.q-drawer){display:none!important;}
  .cui-app-main--with-sidebar,html[data-sidebar='compact'] .cui-app-main--with-sidebar{margin-left:0!important;width:100%!important;max-width:100%!important;}
  .cui-shell-mobile-menu.cui-icon-button{display:inline-flex!important;}
  .cui-mobile-nav-layer{display:block!important;position:fixed!important;inset:var(--cui-shell-header-height) 0 0 0!important;z-index:calc(var(--cui-overlay-z) - 120)!important;pointer-events:none!important;visibility:hidden!important;}
  html[data-mobile-nav='open'] .cui-mobile-nav-layer{pointer-events:auto!important;visibility:visible!important;}
  .cui-mobile-nav-backdrop{position:absolute!important;inset:0!important;border:0!important;padding:0!important;margin:0!important;background:rgba(8,12,20,.32)!important;opacity:0!important;transition:opacity var(--cui-duration-shell) var(--cui-ease-standard)!important;backdrop-filter:blur(2px);}
  html[data-mobile-nav='open'] .cui-mobile-nav-backdrop{opacity:1!important;}
  .cui-mobile-nav-drawer{position:absolute!important;top:8px!important;bottom:8px!important;left:8px!important;width:min(326px,calc(100vw - 24px))!important;display:flex!important;flex-direction:column!important;background:var(--cui-surface-elevated)!important;border:1px solid var(--cui-border-subtle)!important;border-radius:var(--cui-radius-overlay)!important;box-shadow:0 24px 80px rgba(0,0,0,.24)!important;overflow:hidden!important;transform:translateX(calc(-100% - 16px))!important;transition:transform var(--cui-duration-overlay-precise) var(--cui-easing-standard)!important;}
  html[data-mobile-nav='open'] .cui-mobile-nav-drawer{transform:translateX(0)!important;}
  .cui-mobile-nav-head{height:56px!important;min-height:56px!important;padding:0 10px 0 14px!important;display:flex!important;align-items:center!important;justify-content:space-between!important;}
  .cui-mobile-nav-head__copy{display:flex!important;flex-direction:column!important;gap:0!important;}
  .cui-mobile-nav-title{font-size:var(--cui-font-size-13)!important;line-height:var(--cui-line-height-17)!important;font-weight:var(--cui-font-weight-720)!important;}
  .cui-mobile-nav-subtitle{font-size:var(--cui-font-size-10)!important;line-height:var(--cui-line-height-13)!important;color:var(--cui-text-tertiary)!important;}
  .cui-mobile-nav-body{flex:1 1 auto!important;height:auto!important;min-height:0!important;overflow:auto!important;padding:8px!important;}
  .cui-mobile-nav-drawer>.cui-sidebar-footer{padding:8px 10px 10px!important;}
}
@media(min-width:900px){
  .cui-mobile-nav-layer{display:none!important;}
}
@media(max-width:680px){
  .cui-shell-greeting{display:none!important;}
  .cui-shell-subtitle{display:none!important;}
  .cui-environment-badge{display:none!important;}
  .cui-app-header{padding-inline:12px!important;}
}
@media(max-width:420px){
  .cui-shell-title{max-width:190px!important;}
  .cui-shell-actions{gap:3px!important;}
}

/* v1.7 Phase 2 - optical interaction constitution */
:root{--cui-v17-control-radius:10px;--cui-v17-choice-height:36px;--cui-v17-slider-track:6px;--cui-v17-thumb:18px;}
.cui-button.q-btn{height:var(--cui-control-height,var(--cui-control-medium))!important;min-height:var(--cui-control-height,var(--cui-control-medium))!important;padding:0 13px!important;border-radius:var(--cui-v17-control-radius)!important;overflow:hidden!important;isolation:isolate!important;}
.cui-button.q-btn .q-btn__content{display:inline-flex!important;align-items:center!important;justify-content:center!important;gap:7px!important;height:100%!important;line-height:var(--cui-line-height-ratio-1)!important;white-space:nowrap!important;}
.cui-button__label{display:inline-flex!important;align-items:center!important;line-height:var(--cui-line-height-ratio-1)!important;margin:0!important;}
.cui-button--primary{background:linear-gradient(180deg,color-mix(in srgb,var(--cui-accent) 92%,white),var(--cui-accent))!important;color:#fff!important;box-shadow:0 1px 2px rgba(0,0,0,.12),0 6px 16px color-mix(in srgb,var(--cui-accent) 16%,transparent)!important;}
.cui-button--secondary{background:var(--cui-surface)!important;color:var(--cui-text-primary)!important;box-shadow:inset 0 0 0 1px var(--cui-border-default),0 1px 2px color-mix(in srgb,var(--cui-text-primary) 8%,transparent)!important;}
.cui-button--tertiary{background:color-mix(in srgb,var(--cui-accent) 11%,var(--cui-surface))!important;color:var(--cui-accent)!important;box-shadow:none!important;}
.cui-button--ghost{background:transparent!important;color:var(--cui-text-secondary)!important;box-shadow:none!important;}
.cui-button--danger{background:linear-gradient(180deg,color-mix(in srgb,var(--cui-danger) 92%,white),var(--cui-danger))!important;color:#fff!important;box-shadow:0 1px 2px rgba(0,0,0,.12)!important;}
.cui-button--primary:hover{filter:brightness(1.035)!important}.cui-button--secondary:hover{background:var(--cui-surface-hover)!important}.cui-button--tertiary:hover{background:color-mix(in srgb,var(--cui-accent) 17%,var(--cui-surface))!important}.cui-button--ghost:hover{background:var(--cui-surface-hover)!important;color:var(--cui-text-primary)!important}
.cui-button.is-loading:disabled{opacity:1!important;cursor:progress!important}.cui-button.is-loading::before{display:none!important}.cui-button__spinner{display:block!important;width:14px!important;height:14px!important;min-width:14px!important;border-radius:var(--cui-radius-circle)!important;border:1.75px solid color-mix(in srgb,currentColor 42%,transparent)!important;border-top-color:currentColor!important;animation:cui-spin var(--cui-duration-spinner-compact) var(--cui-easing-linear) infinite!important;box-sizing:border-box!important;}
.cui-badge,.cui-count-badge,.cui-chip{box-sizing:border-box!important;align-items:center!important;justify-content:center!important;vertical-align:middle!important;line-height:var(--cui-line-height-ratio-1)!important;}
.cui-badge{min-height:24px!important;padding:0 9px!important;border:0!important;gap:6px!important;}
.cui-badge>.q-label,.cui-badge .q-label,.cui-chip .q-label,.cui-count-badge.q-label{display:inline-flex!important;align-items:center!important;justify-content:center!important;min-height:0!important;line-height:var(--cui-line-height-ratio-1)!important;margin:0!important;padding:0!important;}
.cui-count-badge{height:22px!important;min-width:22px!important;padding:0 7px!important;}
.cui-chip.q-btn{min-height:28px!important;height:28px!important;padding:0 10px!important;border-radius:var(--cui-radius-pill)!important;}
.cui-chip.q-btn .q-btn__content{height:100%!important;align-items:center!important;line-height:var(--cui-line-height-ratio-1)!important;}
.cui-choice-group{border:0!important;padding:0!important;margin:0!important;min-width:0!important;display:flex!important;flex-direction:column!important;gap:8px!important;}
.cui-choice-group__label{margin:0!important}.cui-choice-group__options{display:flex!important;flex-direction:column!important;gap:4px!important;}
.cui-choice-row{position:relative!important;display:grid!important;grid-template-columns:20px minmax(0,1fr)!important;align-items:center!important;gap:10px!important;min-height:var(--cui-v17-choice-height)!important;width:fit-content!important;max-width:100%!important;padding:5px 8px!important;margin:0!important;border-radius:var(--cui-radius-control)!important;color:var(--cui-text-primary)!important;cursor:pointer!important;transition:background var(--cui-motion-fast) var(--cui-ease-standard),box-shadow var(--cui-motion-fast) var(--cui-ease-standard)!important;}
.cui-choice-row:hover{background:var(--cui-surface-hover)!important}.cui-choice-row:has(.cui-choice-native:focus-visible){background:var(--cui-surface-hover)!important;box-shadow:0 0 0 3px color-mix(in srgb,var(--cui-focus-ring) 34%,transparent)!important;}
.cui-choice-native{position:absolute!important;opacity:0!important;pointer-events:none!important;width:1px!important;height:1px!important;}
.cui-choice-visual{grid-column:1!important;grid-row:1!important;width:18px!important;height:18px!important;border:1.5px solid var(--cui-border-strong)!important;background:var(--cui-surface)!important;box-sizing:border-box!important;display:grid!important;place-items:center!important;}
.cui-choice-row--checkbox .cui-choice-visual{border-radius:var(--cui-radius-micro)!important}.cui-choice-row--radio .cui-choice-visual{border-radius:var(--cui-radius-circle)!important}
.cui-choice-row--checkbox:has(.cui-choice-native:checked) .cui-choice-visual{background:var(--cui-accent)!important;border-color:var(--cui-accent)!important;}
.cui-choice-row--checkbox:has(.cui-choice-native:checked) .cui-choice-visual::after{content:''!important;width:8px!important;height:4px!important;border-left:2px solid #fff!important;border-bottom:2px solid #fff!important;transform:translateY(-1px) rotate(-45deg)!important;}
.cui-choice-row--radio:has(.cui-choice-native:checked) .cui-choice-visual{border-color:var(--cui-accent)!important;box-shadow:inset 0 0 0 4px var(--cui-surface)!important;background:var(--cui-accent)!important;}
.cui-choice-copy{display:flex!important;flex-direction:column!important;justify-content:center!important;gap:1px!important;min-width:0!important}.cui-choice-label{line-height:var(--cui-line-height-20)!important;margin:0!important}.cui-choice-help{line-height:var(--cui-line-height-17)!important;margin:0!important;color:var(--cui-text-tertiary)!important;font-size:var(--cui-type-caption-size)!important;}
.cui-slider-field{display:flex!important;flex-direction:column!important;gap:8px!important;width:100%!important;min-width:0!important}.cui-slider-head{display:flex!important;align-items:center!important;justify-content:space-between!important;gap:12px!important}.cui-slider-value{font-size:var(--cui-font-size-12)!important;font-weight:var(--cui-font-weight-650)!important;font-variant-numeric:tabular-nums!important;color:var(--cui-text-secondary)!important;line-height:var(--cui-line-height-18)!important;}
.cui-native-slider{appearance:none!important;-webkit-appearance:none!important;width:100%!important;height:28px!important;background:transparent!important;outline:0!important;margin:0!important;cursor:pointer!important;}
.cui-native-slider::-webkit-slider-runnable-track{height:var(--cui-v17-slider-track)!important;border-radius:var(--cui-radius-pill)!important;background:linear-gradient(90deg,var(--cui-accent) 0 var(--pct,0%),var(--cui-border-default) var(--pct,0%) 100%)!important;}
.cui-native-slider::-webkit-slider-thumb{-webkit-appearance:none!important;width:var(--cui-v17-thumb)!important;height:var(--cui-v17-thumb)!important;margin-top:-6px!important;border:0!important;border-radius:var(--cui-radius-circle)!important;background:#fff!important;box-shadow:0 1px 4px rgba(0,0,0,.28),0 0 0 1px rgba(0,0,0,.08)!important;}
.cui-native-slider:focus-visible::-webkit-slider-thumb{box-shadow:0 1px 4px rgba(0,0,0,.28),0 0 0 4px color-mix(in srgb,var(--cui-focus-ring) 32%,transparent)!important;}
.cui-slider-meta{display:flex!important;align-items:center!important;justify-content:space-between!important;line-height:var(--cui-line-height-16)!important;}
.cui-slider--v17.q-slider{min-height:30px!important;padding:6px 0!important}.cui-slider--v17.q-slider .q-slider__track-container{height:6px!important}.cui-slider--v17.q-slider .q-slider__track{background:var(--cui-border-default)!important;border-radius:var(--cui-radius-pill)!important;opacity:1!important}.cui-slider--v17.q-slider .q-slider__selection{background:var(--cui-accent)!important;border-radius:var(--cui-radius-pill)!important}.cui-slider--v17.q-slider .q-slider__thumb{width:18px!important;height:18px!important;color:#fff!important;border:0!important;box-shadow:0 1px 4px rgba(0,0,0,.28),0 0 0 1px rgba(0,0,0,.08)!important}.cui-slider--v17.q-slider .q-slider__focus-ring{display:none!important}.cui-slider--v17.q-slider:focus-within .q-slider__thumb{box-shadow:0 1px 4px rgba(0,0,0,.28),0 0 0 4px color-mix(in srgb,var(--cui-focus-ring) 30%,transparent)!important;}
.cui-surface--interactive{min-height:74px!important;padding:14px 16px!important;border-radius:var(--cui-radius-surface)!important;background:var(--cui-surface)!important;box-shadow:inset 0 0 0 1px var(--cui-border-subtle)!important;border:0!important;outline:0!important;}
.cui-surface--interactive:hover{transform:translateY(-1px)!important;background:var(--cui-surface-hover)!important;box-shadow:inset 0 0 0 1px var(--cui-border-default),0 6px 18px color-mix(in srgb,var(--cui-text-primary) 7%,transparent)!important}.cui-surface--interactive.is-selected{background:color-mix(in srgb,var(--cui-accent) 9%,var(--cui-surface))!important;box-shadow:inset 0 0 0 1.5px color-mix(in srgb,var(--cui-accent) 56%,var(--cui-border-default))!important;}
.cui-surface--interactive:focus-visible{box-shadow:inset 0 0 0 1px var(--cui-accent),0 0 0 3px color-mix(in srgb,var(--cui-focus-ring) 34%,transparent)!important;}
.cui-environment-badge{color:var(--cui-text-primary)!important;background:var(--cui-surface-elevated)!important;box-shadow:inset 0 0 0 1px var(--cui-border-default)!important;line-height:var(--cui-line-height-ratio-1)!important;}
.cui-environment-badge--development{background:color-mix(in srgb,var(--cui-info) 9%,var(--cui-surface-elevated))!important}.cui-environment-badge--staging{background:color-mix(in srgb,var(--cui-warning) 10%,var(--cui-surface-elevated))!important}.cui-environment-badge--production{background:color-mix(in srgb,var(--cui-success) 9%,var(--cui-surface-elevated))!important}
.cui-progress.q-linear-progress,.cui-progress{height:12px!important;min-height:12px!important;border-radius:var(--cui-radius-pill)!important;overflow:hidden!important}.cui-progress-metric__row{align-items:center!important}.cui-progress-metric__value{min-width:42px!important;text-align:right!important;line-height:var(--cui-line-height-18)!important;}
.cui-motion-demo{will-change:transform,opacity,box-shadow!important}.cui-motion-demo--title.is-replaying{animation:cui-v17-motion-title var(--cui-duration-title-lux-long) var(--cui-easing-enter) both!important}.cui-motion-demo--section.is-replaying{animation:cui-v17-motion-section var(--cui-duration-section-lux) var(--cui-easing-enter) both!important}.cui-motion-demo--selection.is-replaying{animation:cui-v17-motion-selection var(--cui-duration-selection-lux) var(--cui-easing-standard) both!important}
@keyframes cui-v17-motion-title{0%{opacity:.15;transform:translateY(14px) scale(.985)}100%{opacity:1;transform:none}}@keyframes cui-v17-motion-section{0%{opacity:.2;transform:translateY(12px)}100%{opacity:1;transform:none}}@keyframes cui-v17-motion-selection{0%{background:var(--cui-surface-secondary);box-shadow:0 0 0 0 transparent}45%{background:var(--cui-accent-soft);box-shadow:0 0 0 5px color-mix(in srgb,var(--cui-accent) 15%,transparent)}100%{background:var(--cui-surface-secondary);box-shadow:none}}
@media(prefers-reduced-motion:reduce){.cui-motion-demo--title.is-replaying,.cui-motion-demo--section.is-replaying,.cui-motion-demo--selection.is-replaying{animation:cui-v17-motion-reduced var(--cui-duration-reduced-emphasis) var(--cui-easing-native) both!important}}
@keyframes cui-v17-motion-reduced{0%{opacity:.45}100%{opacity:1}}


/* ================================================================
   COMPANY UI v2 — OVERLAY OWNERSHIP CONSTITUTION
   Layer tokens are declared once at the top of this final-loaded stylesheet.
   Application-local controls can never compete with portal/modal surfaces.
   ================================================================ */
/* Local sticky controls stay local. They never compete with application overlays. */
.cui-lab-controlbar,.cui-sticky,.cui-form-actions.is-sticky{z-index:var(--cui-layer-sticky)!important;}
.cui-table-toolbar,.cui-chart-toolbar,.cui-image-viewer__toolbar{position:relative!important;z-index:auto!important;}
.cui-data-table .ag-header,.cui-data-table .ag-pinned-left-header,.cui-data-table .ag-pinned-right-header,.cui-data-table .ag-floating-top,.cui-data-table .ag-floating-bottom{z-index:2!important;}
.ag-popup,.ag-popup-child,.ag-menu{z-index:var(--cui-local-popup-z)!important;}

/* Anchored application overlays. */
.q-menu.cui-menu,.q-menu.cui-user-menu,.q-menu.cui-popover,.q-menu[role='listbox']{
  z-index:var(--cui-overlay-z)!important;
  border:1px solid color-mix(in srgb,var(--cui-border-default) 86%,transparent)!important;
  border-radius:var(--cui-radius-surface)!important;
  background:color-mix(in srgb,var(--cui-surface-elevated) 97%,transparent)!important;
  box-shadow:0 18px 54px rgba(0,0,0,.16),0 1px 2px rgba(0,0,0,.05)!important;
  backdrop-filter:blur(18px)!important;-webkit-backdrop-filter:blur(18px)!important;
}
.cui-overlay-surface--popover{isolation:isolate!important;}

/* Modal ownership: every dialog/drawer dominates all app chrome and local popups. */
.q-dialog{z-index:var(--cui-modal-z)!important;}
.q-dialog__backdrop{background:color-mix(in srgb,var(--cui-overlay-scrim) 88%,transparent)!important;backdrop-filter:blur(4px)!important;-webkit-backdrop-filter:blur(4px)!important;}
.q-dialog__inner{padding:var(--cui-overlay-edge-gap)!important;pointer-events:auto!important;}
.cui-overlay-surface--dialog,.cui-overlay-surface--drawer{position:relative!important;z-index:1!important;pointer-events:auto!important;isolation:isolate!important;}
.cui-dialog{border:1px solid var(--cui-border-subtle)!important;background:var(--cui-surface-elevated)!important;box-shadow:0 28px 90px rgba(0,0,0,.24),0 2px 8px rgba(0,0,0,.08)!important;}
.cui-dialog__head{align-items:center!important;padding:18px 20px 12px!important;}
.cui-dialog__copy{display:flex!important;flex-direction:column!important;gap:3px!important;}
.cui-dialog__title{font-size:var(--cui-font-size-16)!important;line-height:var(--cui-line-height-21)!important;font-weight:var(--cui-font-weight-730)!important;letter-spacing:-.012em!important;}
.cui-dialog__description{font-size:var(--cui-font-size-12)!important;line-height:var(--cui-line-height-18)!important;margin:0!important;color:var(--cui-text-secondary)!important;}
.cui-dialog__body{padding:4px 20px 18px!important;gap:12px!important;}
.cui-dialog__footer{padding:12px 20px 16px!important;background:var(--cui-surface-elevated)!important;border-top:1px solid var(--cui-border-subtle)!important;}
.cui-dialog__confirmation{display:flex!important;flex-direction:column!important;gap:8px!important;margin:0 20px 14px!important;padding:12px!important;border-radius:var(--cui-radius-surface)!important;background:var(--cui-danger-soft)!important;box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--cui-danger) 18%,var(--cui-border-subtle))!important;}
.cui-dialog__confirmation-input{position:relative!important;z-index:2!important;width:100%!important;pointer-events:auto!important;}
.cui-dialog__confirmation-input input,.cui-dialog__confirmation-input textarea{pointer-events:auto!important;user-select:text!important;-webkit-user-select:text!important;}
.cui-dialog__close,.cui-drawer__close{position:relative!important;z-index:3!important;pointer-events:auto!important;}

.cui-drawer{background:var(--cui-surface-elevated)!important;border:1px solid var(--cui-border-subtle)!important;box-shadow:0 26px 90px rgba(0,0,0,.24)!important;}
.cui-drawer__header{align-items:center!important;padding:16px 18px 13px!important;border-bottom:1px solid var(--cui-border-subtle)!important;}
.cui-drawer__copy{display:flex!important;flex-direction:column!important;gap:2px!important;min-width:0!important;}
.cui-drawer__title{font-size:var(--cui-font-size-15)!important;line-height:var(--cui-line-height-20)!important;font-weight:var(--cui-font-weight-730)!important;}
.cui-drawer__subtitle{font-size:var(--cui-font-size-11_5)!important;line-height:var(--cui-line-height-17)!important;margin:0!important;color:var(--cui-text-secondary)!important;}
.cui-drawer__body{padding:16px 18px 18px!important;}

/* Company tooltip is a transient DOM portal, never a sticky Quasar layer. */
.cui-tooltip--company{position:fixed!important;z-index:var(--cui-tooltip-z)!important;display:block!important;width:max-content!important;pointer-events:none!important;padding:7px 9px!important;border:0!important;border-radius:var(--cui-radius-inner)!important;background:color-mix(in srgb,var(--cui-text-primary) 94%,transparent)!important;color:var(--cui-surface)!important;font-size:var(--cui-font-size-11)!important;line-height:var(--cui-line-height-15)!important;font-weight:var(--cui-font-weight-560)!important;box-shadow:0 8px 28px rgba(0,0,0,.2)!important;animation:cui-v17-tooltip-in var(--cui-duration-micro) var(--cui-easing-out) both!important;}
@keyframes cui-v17-tooltip-in{from{opacity:0;transform:translateY(2px) scale(.985)}to{opacity:1;transform:none}}

/* Toasts: explicit close control + visible/pauseable lifetime gauge. */
.cui-toast-stack{top:calc(var(--cui-shell-header-height) + 14px)!important;right:16px!important;z-index:var(--cui-toast-z)!important;width:min(390px,calc(100vw - 32px))!important;gap:9px!important;}
.cui-toast{display:flex!important;flex-direction:column!important;gap:0!important;padding:0!important;overflow:hidden!important;border:1px solid var(--cui-border-subtle)!important;border-radius:var(--cui-radius-surface)!important;background:color-mix(in srgb,var(--cui-surface-elevated) 96%,transparent)!important;box-shadow:0 18px 54px rgba(0,0,0,.18),0 1px 2px rgba(0,0,0,.06)!important;backdrop-filter:blur(20px)!important;-webkit-backdrop-filter:blur(20px)!important;}
.cui-toast__body{display:grid!important;grid-template-columns:8px minmax(0,1fr) 28px!important;align-items:center!important;gap:10px!important;padding:11px 10px 10px 12px!important;min-height:48px!important;}
.cui-toast__dot{margin:0!important;align-self:center!important;}
.cui-toast__message{font-size:var(--cui-font-size-12)!important;line-height:var(--cui-line-height-17)!important;font-weight:var(--cui-font-weight-560)!important;}
.cui-toast__close{width:28px!important;height:28px!important;min-width:28px!important;border:0!important;border-radius:var(--cui-radius-inner)!important;background:transparent!important;color:var(--cui-text-tertiary)!important;display:grid!important;place-items:center!important;cursor:pointer!important;font:var(--cui-font-weight-500) var(--cui-font-size-20)/var(--cui-line-height-ratio-1) system-ui,sans-serif!important;}
.cui-toast__close:hover{background:var(--cui-surface-hover)!important;color:var(--cui-text-primary)!important;}
.cui-toast__close:focus-visible{outline:0!important;box-shadow:0 0 0 3px color-mix(in srgb,var(--cui-focus-ring) 32%,transparent)!important;}
.cui-toast__lifetime{height:2px!important;background:color-mix(in srgb,var(--_tone) 10%,transparent)!important;overflow:hidden!important;}
.cui-toast__lifetime-bar{display:block!important;width:100%!important;height:100%!important;transform-origin:left center!important;background:var(--_tone)!important;}
.cui-toast.is-leaving{pointer-events:none!important;}

/* Mobile keeps breathing room; full-screen is deliberate rather than accidental. */
@media(max-width:599px){
  .q-dialog__inner{padding:10px!important;}
  .cui-dialog:not(.cui-dialog--full),.cui-drawer{border-radius:var(--cui-radius-overlay)!important;}
  .cui-toast-stack{right:10px!important;left:10px!important;width:auto!important;}
}
@media(prefers-reduced-motion:reduce){.cui-tooltip--company{animation:none!important;}}

/* v1.7 Phase 5 — analytical range control + exact spatial containment. */
.cui-chart-panel__body{overflow:hidden!important;}
.cui-chart-scale-band{position:relative!important;z-index:0!important;}
.cui-chart-scale-band__gradient{pointer-events:none!important;}
.cui-spatial-panel .cui-chart-panel__body{overflow:hidden!important;}
.cui-spatial-viewport{isolation:isolate!important;clip-path:inset(0 round var(--cui-radius-surface))!important;}
.cui-spatial-svg-host,.cui-spatial-svg-host>div,.cui-spatial-svg-host svg{max-width:100%!important;overflow:hidden!important;}
.cui-wafer-die,.cui-spatial-cell{vector-effect:non-scaling-stroke;}

/* Phase 5 semiconductor-native analytical matrices. */
.cui-fingerprint-bg,.cui-commonality-bg{fill:var(--cui-surface-secondary);}
.cui-fingerprint-outline,.cui-commonality-outline{fill:none;stroke:var(--cui-border-default);stroke-width:1.2;vector-effect:non-scaling-stroke;}
.cui-fingerprint-column,.cui-commonality-column{fill:var(--cui-text-secondary);font:var(--cui-font-weight-650) var(--cui-font-size-10) -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:.015em;}
.cui-fingerprint-row,.cui-commonality-row{fill:var(--cui-text-secondary);font:var(--cui-font-weight-620) var(--cui-font-size-10) -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;}
.cui-fingerprint-cell,.cui-commonality-cell{stroke:color-mix(in srgb,var(--cui-surface) 88%,transparent);stroke-width:1;vector-effect:non-scaling-stroke;transition:opacity var(--cui-duration-micro) var(--cui-easing-native),stroke var(--cui-duration-micro) var(--cui-easing-native);}
.cui-fingerprint-cell:hover,.cui-commonality-cell:hover{stroke:var(--cui-text-primary);stroke-width:2;}
.cui-fingerprint-value,.cui-commonality-value{fill:var(--cui-text-primary);font:var(--cui-font-weight-650) var(--cui-font-size-9) ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;pointer-events:none;paint-order:stroke;stroke:color-mix(in srgb,var(--cui-surface) 62%,transparent);stroke-width:1.5px;}
.cui-commonality-cell{fill:var(--cui-accent);}

/* v1.7 Phase 6 — workflow, evidence viewer, and RCA cockpit composition. */
.cui-progress-steps{display:grid!important;grid-template-columns:repeat(auto-fit,minmax(150px,1fr))!important;gap:0!important;padding:4px 0 2px!important;overflow:visible!important;}
.cui-progress-step{position:relative!important;display:grid!important;grid-template-columns:1fr!important;grid-template-rows:30px auto!important;gap:8px!important;min-width:0!important;color:var(--cui-text-tertiary)!important;}
.cui-progress-step__rail{position:relative!important;display:grid!important;place-items:center!important;height:30px!important;}
.cui-progress-step__rail::after{content:'';position:absolute;left:calc(50% + 22px);right:calc(-50% + 22px);top:14.5px;height:1px;background:var(--cui-border-default);z-index:0;}
.cui-progress-step:last-child .cui-progress-step__rail::after{display:none;}
.cui-progress-step__marker{position:relative!important;z-index:1!important;width:30px!important;height:30px!important;min-width:30px!important;display:grid!important;place-items:center!important;border-radius:var(--cui-radius-circle)!important;border:1px solid var(--cui-border-default)!important;background:var(--cui-surface)!important;line-height:var(--cui-line-height-ratio-1)!important;text-align:center!important;box-sizing:border-box!important;}
.cui-progress-step__marker>.cui-svg-icon-host,.cui-progress-step__marker svg,.cui-progress-step__marker .q-icon{display:block!important;width:14px!important;height:14px!important;margin:auto!important;align-self:center!important;justify-self:center!important;}
.cui-progress-step__number{display:grid!important;place-items:center!important;width:100%!important;height:100%!important;margin:0!important;padding:0!important;line-height:var(--cui-line-height-ratio-1)!important;font-size:var(--cui-font-size-11)!important;font-weight:var(--cui-font-weight-700)!important;}
.cui-progress-step__copy{display:grid!important;gap:2px!important;text-align:center!important;justify-items:center!important;min-width:0!important;padding:0 8px!important;}
.cui-progress-step__label{margin:0!important;line-height:var(--cui-line-height-17)!important;font-size:var(--cui-font-size-12)!important;font-weight:var(--cui-font-weight-650)!important;color:var(--cui-text-secondary)!important;white-space:normal!important;}
.cui-progress-step__state{margin:0!important;font-size:var(--cui-font-size-10)!important;line-height:var(--cui-line-height-14)!important;color:var(--cui-text-tertiary)!important;}
.cui-progress-step.is-active .cui-progress-step__marker{color:var(--cui-accent)!important;border-color:var(--cui-accent)!important;box-shadow:0 0 0 3px var(--cui-accent-soft)!important;}
.cui-progress-step.is-active .cui-progress-step__label{color:var(--cui-text-primary)!important;}
.cui-progress-step.is-complete .cui-progress-step__marker{color:var(--cui-success)!important;border-color:color-mix(in srgb,var(--cui-success) 40%,var(--cui-border-default))!important;background:var(--cui-success-soft)!important;}
.cui-progress-step.is-error .cui-progress-step__marker{color:var(--cui-danger)!important;border-color:color-mix(in srgb,var(--cui-danger) 42%,var(--cui-border-default))!important;background:var(--cui-danger-soft)!important;}

.cui-image-viewer{gap:0!important;}
.cui-image-viewer__toolbar{min-height:58px!important;padding:10px 12px!important;border-bottom:1px solid var(--cui-border-subtle)!important;background:var(--cui-surface)!important;}
.cui-image-viewer__heading{display:grid!important;gap:1px!important;min-width:0!important;}
.cui-image-viewer__caption{font-size:var(--cui-font-size-12)!important;line-height:var(--cui-line-height-17)!important;font-weight:var(--cui-font-weight-700)!important;color:var(--cui-text-primary)!important;}
.cui-image-viewer__hint{font-size:var(--cui-font-size-10)!important;line-height:var(--cui-line-height-14)!important;color:var(--cui-text-tertiary)!important;white-space:normal!important;}
.cui-image-viewer__actions{gap:2px!important;}
.cui-image-viewer__zoom{display:grid!important;place-items:center!important;min-width:48px!important;height:28px!important;padding:0 8px!important;border-radius:var(--cui-radius-inner)!important;background:var(--cui-surface-secondary)!important;color:var(--cui-text-secondary)!important;font-size:var(--cui-font-size-11)!important;font-weight:var(--cui-font-weight-700)!important;}
.cui-image-viewer__viewport{position:relative!important;height:390px!important;min-height:300px!important;margin:10px!important;border-radius:var(--cui-radius-surface)!important;background:linear-gradient(180deg,var(--cui-surface-secondary),color-mix(in srgb,var(--cui-surface-secondary) 72%,var(--cui-surface)))!important;cursor:zoom-in!important;box-shadow:inset 0 0 0 1px var(--cui-border-subtle)!important;}
.cui-image-viewer__viewport[data-cui-spatial-scale]:not([data-cui-spatial-scale="1.000"]){cursor:grab!important;}
.cui-image-viewer__viewport.is-dragging{cursor:grabbing!important;}
.cui-image-viewer__image{max-width:calc(100% - 20px)!important;max-height:calc(100% - 20px)!important;border-radius:var(--cui-radius-control)!important;box-shadow:0 8px 24px rgba(0,0,0,.06)!important;}
.cui-image-viewer__mode{position:absolute!important;left:12px!important;bottom:12px!important;z-index:2!important;display:grid!important;place-items:center!important;min-width:42px!important;height:22px!important;padding:0 7px!important;border-radius:var(--cui-radius-pill)!important;background:color-mix(in srgb,var(--cui-surface) 90%,transparent)!important;box-shadow:inset 0 0 0 1px var(--cui-border-subtle)!important;color:var(--cui-text-tertiary)!important;font-size:var(--cui-font-size-9)!important;font-weight:var(--cui-font-weight-750)!important;letter-spacing:.06em!important;pointer-events:none!important;}

.cui-eng-entity{overflow:hidden!important;container-type:inline-size!important;}
.cui-eng-entity__head{display:grid!important;grid-template-columns:minmax(0,1fr) auto!important;align-items:center!important;gap:14px!important;min-width:0!important;}
.cui-eng-entity__identity{min-width:0!important;align-items:center!important;}
.cui-eng-entity__identity>div:last-child{min-width:0!important;overflow:hidden!important;}
.cui-eng-entity__title,.cui-eng-entity__secondary{min-width:0!important;overflow-wrap:anywhere!important;}
.cui-eng-entity__title{font-size:var(--cui-font-size-15)!important;line-height:var(--cui-line-height-20)!important;font-weight:var(--cui-font-weight-720)!important;letter-spacing:-.012em!important;}
.cui-eng-entity__secondary{margin-top:2px!important;font-size:var(--cui-font-size-11)!important;line-height:var(--cui-line-height-16)!important;}
.cui-eng-property-grid{grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:8px!important;width:100%!important;min-width:0!important;overflow:hidden!important;}
.cui-eng-property{box-sizing:border-box!important;width:100%!important;min-width:0!important;min-height:58px!important;padding:9px 10px!important;overflow:hidden!important;contain:layout paint!important;}
.cui-eng-property__label,.cui-eng-property__value{max-width:100%!important;min-width:0!important;}
.cui-eng-property__value{white-space:normal!important;word-break:break-word!important;overflow-wrap:anywhere!important;}
.cui-eng-status{min-height:28px!important;align-self:center!important;}
.cui-rca-balance{grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:8px!important;}
.cui-rca-balance>div{min-width:0!important;overflow:hidden!important;}
.cui-evidence{min-width:0!important;overflow:hidden!important;}
.cui-evidence__meta{row-gap:4px!important;}

.cui-investigation-context{display:grid!important;grid-template-columns:minmax(220px,1.35fr) repeat(3,minmax(120px,.75fr))!important;gap:1px!important;padding:1px!important;border-radius:var(--cui-radius-surface)!important;background:var(--cui-border-subtle)!important;overflow:hidden!important;}
.cui-investigation-context__cell{display:grid!important;gap:3px!important;align-content:center!important;min-width:0!important;min-height:62px!important;padding:10px 12px!important;background:var(--cui-surface)!important;}
.cui-investigation-context__label{font-size:var(--cui-font-size-9)!important;line-height:var(--cui-line-height-13)!important;font-weight:var(--cui-font-weight-700)!important;text-transform:uppercase!important;letter-spacing:.06em!important;color:var(--cui-text-tertiary)!important;}
.cui-investigation-context__value{font-size:var(--cui-font-size-12)!important;line-height:var(--cui-line-height-17)!important;font-weight:var(--cui-font-weight-680)!important;color:var(--cui-text-primary)!important;overflow-wrap:anywhere!important;}
.cui-investigation-context__cell--lead .cui-investigation-context__value{font-size:var(--cui-font-size-14)!important;line-height:var(--cui-line-height-19)!important;}

@container (max-width:520px){.cui-eng-property-grid{grid-template-columns:1fr!important;}}
@media(max-width:899px){
 .cui-progress-steps{grid-template-columns:repeat(4,minmax(132px,1fr))!important;overflow-x:auto!important;padding-bottom:10px!important;}
 .cui-image-viewer__toolbar{align-items:flex-start!important;}
 .cui-image-viewer__viewport{height:330px!important;min-height:260px!important;}
 .cui-investigation-context{grid-template-columns:1fr 1fr!important;}
 .cui-investigation-context__cell--lead{grid-column:1/-1!important;}
 .cui-eng-entity__head{grid-template-columns:1fr!important;}
 .cui-eng-status{justify-self:start!important;}
}
@media(max-width:520px){
 .cui-image-viewer__toolbar{display:grid!important;grid-template-columns:1fr!important;}
 .cui-image-viewer__actions{justify-content:flex-start!important;}
 .cui-investigation-context{grid-template-columns:1fr!important;}
 .cui-investigation-context__cell--lead{grid-column:auto!important;}
}


/* ================================================================
   COMPANY UI v1.7.1 — SCREENSHOT-BACKED VISUAL + INTERACTION CORRECTION
   ================================================================ */
/* Environment metadata is a Company surface, never a Quasar badge. */
.cui-environment-badge::before{display:none!important;content:none!important;}
.cui-environment-badge{
  box-sizing:border-box!important;display:inline-flex!important;align-items:center!important;justify-content:center!important;
  gap:8px!important;min-height:30px!important;padding:0 12px 0 10px!important;border:1px solid var(--cui-border-subtle)!important;
  border-radius:var(--cui-radius-control)!important;background:var(--cui-surface-secondary)!important;color:var(--cui-text-primary)!important;
  box-shadow:none!important;font-size:var(--cui-font-size-10_5)!important;line-height:var(--cui-line-height-ratio-1)!important;font-weight:var(--cui-font-weight-760)!important;letter-spacing:.07em!important;
}
.cui-environment-badge__dot{width:8px!important;height:8px!important;flex:0 0 8px!important;border-radius:var(--cui-radius-circle)!important;background:var(--cui-text-tertiary)!important;}
.cui-environment-badge__label{margin:0!important;color:inherit!important;line-height:var(--cui-line-height-ratio-1)!important;}
.cui-environment-badge--development{background:color-mix(in srgb,var(--cui-info) 10%,var(--cui-surface))!important;border-color:color-mix(in srgb,var(--cui-info) 22%,var(--cui-border-subtle))!important;}
.cui-environment-badge--development .cui-environment-badge__dot{background:var(--cui-info)!important;}
.cui-environment-badge--staging{background:color-mix(in srgb,var(--cui-warning) 12%,var(--cui-surface))!important;border-color:color-mix(in srgb,var(--cui-warning) 25%,var(--cui-border-subtle))!important;}
.cui-environment-badge--staging .cui-environment-badge__dot{background:var(--cui-warning)!important;}
.cui-environment-badge--production{background:color-mix(in srgb,var(--cui-success) 10%,var(--cui-surface))!important;border-color:color-mix(in srgb,var(--cui-success) 24%,var(--cui-border-subtle))!important;}
.cui-environment-badge--production .cui-environment-badge__dot{background:var(--cui-success)!important;}

/* Stronger application identity without increasing header chrome. */
.cui-shell-title-block{position:relative!important;padding-left:11px!important;gap:2px!important;}
.cui-shell-title-block::before{content:'';position:absolute;left:0;top:4px;bottom:4px;width:3px;border-radius:var(--cui-radius-pill);background:var(--cui-accent);opacity:.9;}
.cui-shell-title{font-size:var(--cui-type-app_identity-size)!important;line-height:var(--cui-type-app_identity-line)!important;font-weight:var(--cui-type-app_identity-weight)!important;letter-spacing:var(--cui-type-app_identity-tracking)!important;color:var(--cui-text-primary)!important;}
.cui-shell-subtitle{font-size:var(--cui-type-app_subtitle-size)!important;line-height:var(--cui-type-app_subtitle-line)!important;font-weight:var(--cui-type-app_subtitle-weight)!important;color:var(--cui-text-secondary)!important;}
.cui-shell-greeting__hello{font-size:var(--cui-type-profile_hint-size)!important;line-height:var(--cui-type-profile_hint-line)!important;font-weight:var(--cui-type-profile_hint-weight)!important;color:var(--cui-text-secondary)!important;}
.cui-shell-greeting__name{font-size:var(--cui-type-profile_name-size)!important;line-height:var(--cui-type-profile_name-line)!important;font-weight:var(--cui-type-profile_name-weight)!important;color:var(--cui-text-primary)!important;}

/* Compact navigation footer is an icon dock. No text participates in compact geometry. */
.cui-sidebar-footer{padding:9px 4px 2px!important;gap:7px!important;overflow:hidden!important;}
.cui-sidebar-footer__actions{display:flex!important;flex-direction:column!important;gap:3px!important;min-width:0!important;}
.cui-sidebar-footer__action{
  appearance:none;border:0;box-sizing:border-box;width:100%;min-height:34px;padding:0 9px;border-radius:var(--cui-radius-control);
  display:flex;align-items:center;justify-content:flex-start;gap:9px;background:transparent;color:var(--cui-text-secondary);
  font:var(--cui-font-weight-650) var(--cui-font-size-11)/var(--cui-line-height-15) -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;cursor:pointer;text-align:left;
}
.cui-sidebar-footer__action:hover{background:var(--cui-surface-hover);color:var(--cui-text-primary);}
.cui-sidebar-footer__action:focus-visible{outline:0;box-shadow:0 0 0 3px color-mix(in srgb,var(--cui-focus-ring) 32%,transparent);}
.cui-sidebar-footer__action>.cui-svg-icon-host{flex:0 0 18px;width:18px;height:18px;display:grid;place-items:center;}
.cui-sidebar-footer__action-label{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
html[data-sidebar='compact'] .cui-sidebar-footer{padding:8px 6px 2px!important;align-items:center!important;}
html[data-sidebar='compact'] .cui-sidebar-owner{box-sizing:border-box;width:36px!important;height:36px!important;padding:0!important;display:grid!important;place-items:center!important;}
html[data-sidebar='compact'] .cui-sidebar-owner__copy{display:none!important;}
html[data-sidebar='compact'] .cui-sidebar-footer__actions{width:36px!important;align-items:center!important;}
html[data-sidebar='compact'] .cui-sidebar-footer__action{position:relative!important;width:36px!important;height:36px!important;min-width:36px!important;min-height:36px!important;padding:0!important;display:block!important;text-align:center!important;}
html[data-sidebar='compact'] .cui-sidebar-footer__action-label{display:none!important;}
html[data-sidebar='compact'] .cui-sidebar-footer__action>.cui-svg-icon-host{position:absolute!important;left:50%!important;top:50%!important;transform:translate(-50%,-50%)!important;width:18px!important;height:18px!important;margin:0!important;display:grid!important;place-items:center!important;}
html[data-sidebar='compact'] .cui-sidebar-footer__action>.cui-svg-icon-host>svg{display:block!important;margin:auto!important;}

/* Native switch — canonical geometry contract.
   51x31 track, 27px thumb, 2px containment on both endpoints, 20px travel.
   Enabled/disabled states share identical geometry; state only changes appearance. */
.cui-choice-row--switch{grid-template-columns:51px minmax(0,1fr)!important;column-gap:10px!important;align-items:center!important;}
.cui-choice-row--switch .cui-switch-track{position:relative!important;box-sizing:border-box!important;width:51px!important;height:31px!important;padding:0!important;border:0!important;border-radius:var(--cui-radius-pill)!important;background:var(--cui-border-default)!important;display:block!important;overflow:hidden!important;transition:background var(--cui-motion-fast) var(--cui-ease-standard),box-shadow var(--cui-motion-fast) var(--cui-ease-standard)!important;}
.cui-choice-row--switch .cui-switch-track::after{content:none!important;display:none!important;}
.cui-choice-row--switch .cui-switch-thumb{position:absolute!important;box-sizing:border-box!important;top:2px!important;left:2px!important;width:27px!important;height:27px!important;border:0!important;border-radius:var(--cui-radius-circle)!important;background:#fff!important;box-shadow:0 1px 2px rgba(0,0,0,.14),0 2px 5px rgba(0,0,0,.10)!important;transform:translateX(0)!important;transition:transform var(--cui-motion-fast) var(--cui-ease-standard),box-shadow var(--cui-motion-fast) var(--cui-ease-standard)!important;will-change:transform!important;}
.cui-choice-row--switch:has(.cui-choice-native:checked) .cui-switch-track{background:var(--cui-accent)!important;}
.cui-choice-row--switch:has(.cui-choice-native:checked) .cui-switch-thumb{transform:translateX(20px)!important;}
.cui-choice-row:has(.cui-choice-native:disabled){opacity:1!important;cursor:not-allowed!important;pointer-events:none!important;color:var(--cui-text-tertiary)!important;}
.cui-choice-row:has(.cui-choice-native:disabled) .cui-switch-track{background:var(--cui-border-default)!important;opacity:.72!important;}
.cui-choice-row:has(.cui-choice-native:disabled) .cui-choice-label{color:var(--cui-text-tertiary)!important;}

/* Dual native range: same track/thumb constitution as the single-value slider. */
.cui-native-range{position:relative!important;width:100%!important;height:32px!important;isolation:isolate!important;}
.cui-native-range__track{position:absolute!important;left:0!important;right:0!important;top:13px!important;height:6px!important;border-radius:var(--cui-radius-pill)!important;background:linear-gradient(90deg,var(--cui-border-default) 0 var(--low-pct),var(--cui-accent) var(--low-pct) var(--high-pct),var(--cui-border-default) var(--high-pct) 100%)!important;pointer-events:none!important;}
.cui-native-range__input{appearance:none!important;-webkit-appearance:none!important;position:absolute!important;inset:0!important;width:100%!important;height:32px!important;margin:0!important;background:transparent!important;outline:0!important;pointer-events:none!important;}
.cui-native-range__input:focus{z-index:5!important;}
.cui-native-range__input::-webkit-slider-runnable-track{height:6px!important;background:transparent!important;border:0!important;}
.cui-native-range__input::-webkit-slider-thumb{-webkit-appearance:none!important;width:18px!important;height:18px!important;margin-top:-6px!important;border:0!important;border-radius:var(--cui-radius-circle)!important;background:#fff!important;box-shadow:0 1px 4px rgba(0,0,0,.28),0 0 0 1px rgba(0,0,0,.08)!important;pointer-events:auto!important;cursor:grab!important;}
.cui-native-range__input::-moz-range-track{height:6px!important;background:transparent!important;border:0!important;}
.cui-native-range__input::-moz-range-thumb{width:18px!important;height:18px!important;border:0!important;border-radius:var(--cui-radius-circle)!important;background:#fff!important;box-shadow:0 1px 4px rgba(0,0,0,.28),0 0 0 1px rgba(0,0,0,.08)!important;pointer-events:auto!important;cursor:grab!important;}
.cui-native-range__input:focus-visible::-webkit-slider-thumb{box-shadow:0 1px 4px rgba(0,0,0,.28),0 0 0 4px color-mix(in srgb,var(--cui-focus-ring) 30%,transparent)!important;}
.cui-native-range__input:disabled::-webkit-slider-thumb,.cui-native-range__input:disabled::-moz-range-thumb{cursor:not-allowed!important;opacity:.55!important;}

/* Company progress never renders framework value text inside the track. */
.cui-progress:not(.q-linear-progress){position:relative!important;display:block!important;width:100%!important;height:12px!important;min-height:12px!important;border-radius:var(--cui-radius-pill)!important;background:var(--cui-surface-secondary)!important;overflow:hidden!important;}
.cui-progress:not(.q-linear-progress) .cui-progress__bar{display:block!important;height:100%!important;min-width:0!important;border-radius:inherit!important;background:var(--cui-accent)!important;transition:width var(--cui-duration-shell) var(--cui-ease-standard)!important;}
.cui-progress.is-indeterminate .cui-progress__bar{position:absolute!important;left:0!important;width:34%!important;animation:cui-v171-progress-indeterminate var(--cui-duration-progress) var(--cui-easing-progress) infinite!important;}
@keyframes cui-v171-progress-indeterminate{0%{transform:translateX(-120%)}50%{transform:translateX(135%)}100%{transform:translateX(330%)}}

/* Side sheets: detail/form/inspector surfaces are anchored to the viewport edge, never centered cards. */
.q-dialog__inner:has(.cui-drawer){padding:0!important;display:flex!important;align-items:stretch!important;justify-content:flex-end!important;overflow:hidden!important;}
.q-dialog__inner:has(.cui-drawer--left){justify-content:flex-start!important;}
.cui-drawer{
  position:relative!important;top:auto!important;bottom:auto!important;left:auto!important;right:auto!important;margin:0!important;
  height:100dvh!important;max-height:100dvh!important;min-height:0!important;max-width:calc(100vw - 40px)!important;
  border-radius:var(--cui-radius-overlay) 0 0 var(--cui-radius-overlay)!important;border-width:0 0 0 1px!important;animation:cui-v171-drawer-right var(--cui-duration-drawer) var(--cui-easing-standard) both!important;
}
.cui-drawer--left{border-radius:0 var(--cui-radius-overlay) var(--cui-radius-overlay) 0!important;border-width:0 1px 0 0!important;animation-name:cui-v171-drawer-left!important;}
.cui-drawer--small{width:min(380px,calc(100vw - 40px))!important;}.cui-drawer--medium{width:min(500px,calc(100vw - 40px))!important;}.cui-drawer--large{width:min(700px,calc(100vw - 40px))!important;}.cui-drawer--x-large{width:min(900px,calc(100vw - 40px))!important;}.cui-drawer--full{width:100vw!important;max-width:100vw!important;}
@keyframes cui-v171-drawer-right{from{opacity:.72;transform:translateX(28px)}to{opacity:1;transform:none}}
@keyframes cui-v171-drawer-left{from{opacity:.72;transform:translateX(-28px)}to{opacity:1;transform:none}}

/* Workflow: suppress the obsolete flex connector; one connector rail owns geometry. */
.cui-progress-step::after{content:none!important;display:none!important;}
.cui-progress-step__rail::after{top:14.5px!important;height:1px!important;left:calc(50% + 23px)!important;right:calc(-50% + 23px)!important;}

/* Command palette is a compact native command surface, not a centered list of QButtons. */
.cui-command-palette{width:min(720px,calc(100vw - 28px))!important;max-height:min(560px,calc(100dvh - 40px))!important;border:1px solid var(--cui-border-subtle)!important;border-radius:var(--cui-radius-overlay)!important;background:var(--cui-surface-elevated)!important;box-shadow:0 28px 90px rgba(0,0,0,.24)!important;overflow:hidden!important;}
.cui-command-palette__search{box-sizing:border-box;display:grid!important;grid-template-columns:20px minmax(0,1fr) auto!important;align-items:center!important;gap:10px!important;min-height:58px!important;padding:9px 12px!important;border-bottom:1px solid var(--cui-border-subtle)!important;background:var(--cui-surface-elevated)!important;}
.cui-command-palette__search>.cui-svg-icon-host{width:18px!important;height:18px!important;color:var(--cui-text-tertiary)!important;}
.cui-command-palette__search-input{appearance:none!important;width:100%!important;min-width:0!important;height:40px!important;padding:0!important;border:0!important;outline:0!important;background:transparent!important;color:var(--cui-text-primary)!important;font:var(--cui-font-weight-560) var(--cui-font-size-15)/var(--cui-line-height-20) -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif!important;}
.cui-command-palette__search-input::placeholder{color:var(--cui-text-tertiary)!important;opacity:1!important;}
.cui-command-palette__escape,.cui-command-palette__shortcut{display:inline-grid!important;place-items:center!important;min-width:28px!important;height:22px!important;padding:0 6px!important;border:1px solid var(--cui-border-subtle)!important;border-radius:var(--cui-radius-control)!important;background:var(--cui-surface-secondary)!important;color:var(--cui-text-tertiary)!important;font:var(--cui-font-weight-650) var(--cui-font-size-10)/var(--cui-line-height-ratio-1) ui-monospace,SFMono-Regular,Menlo,Consolas,monospace!important;white-space:nowrap!important;}
.cui-command-palette__results{display:flex!important;flex-direction:column!important;gap:3px!important;padding:7px!important;overflow:auto!important;}
.cui-command-palette__item{appearance:none!important;box-sizing:border-box!important;width:100%!important;min-height:50px!important;padding:7px 10px!important;border:0!important;border-radius:var(--cui-radius-control)!important;display:grid!important;grid-template-columns:minmax(0,1fr) auto!important;align-items:center!important;gap:12px!important;background:transparent!important;color:var(--cui-text-primary)!important;text-align:left!important;cursor:pointer!important;}
.cui-command-palette__item:hover,.cui-command-palette__item:focus-visible{background:var(--cui-surface-hover)!important;outline:0!important;}
.cui-command-palette__item:focus-visible{box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--cui-accent) 35%,var(--cui-border-subtle))!important;}
.cui-command-palette__item-copy{display:grid!important;gap:2px!important;min-width:0!important;}
.cui-command-palette__label{font-size:var(--cui-font-size-13)!important;line-height:var(--cui-line-height-18)!important;font-weight:var(--cui-font-weight-650)!important;color:var(--cui-text-primary)!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important;}
.cui-command-palette__group{font-size:var(--cui-font-size-10_5)!important;line-height:var(--cui-line-height-14)!important;color:var(--cui-text-tertiary)!important;}
.cui-command-palette__empty{padding:22px 14px!important;text-align:center!important;}

/* Engineering entity: outer radius owns containment; metadata cells do not create a second gray frame. */
.cui-eng-entity{box-sizing:border-box!important;border-radius:var(--cui-radius-surface)!important;padding:18px!important;overflow:hidden!important;}
.cui-eng-property-grid{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:10px!important;width:100%!important;min-width:0!important;padding:0!important;border:0!important;border-radius:0!important;background:transparent!important;overflow:visible!important;}
.cui-eng-property{box-sizing:border-box!important;width:100%!important;min-width:0!important;min-height:72px!important;padding:12px 13px!important;border-radius:var(--cui-radius-control)!important;background:var(--cui-surface-secondary)!important;box-shadow:inset 0 0 0 1px var(--cui-border-subtle)!important;overflow:hidden!important;}
.cui-eng-property__label{font-size:var(--cui-font-size-10)!important;line-height:var(--cui-line-height-14)!important;}
.cui-eng-property__value{font-size:var(--cui-font-size-13_5)!important;line-height:var(--cui-line-height-19)!important;}
@container (max-width:760px){.cui-eng-property-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important;}}
@container (max-width:460px){.cui-eng-property-grid{grid-template-columns:1fr!important;}}

@media(max-width:599px){
  .cui-shell-title-block{padding-left:9px!important;}.cui-shell-title{font-size:var(--cui-font-size-15)!important;line-height:var(--cui-line-height-19)!important;}.cui-shell-subtitle{font-size:var(--cui-font-size-10_5)!important;line-height:var(--cui-line-height-14)!important;}
  .q-dialog__inner:has(.cui-drawer){padding:0!important;}
  .cui-drawer,.cui-drawer--left{width:100vw!important;max-width:100vw!important;height:100dvh!important;border-radius:0!important;border-width:0!important;}
}
@media(prefers-reduced-motion:reduce){.cui-drawer,.cui-progress.is-indeterminate .cui-progress__bar{animation:none!important;}}

/* v3 browser UI/UX hardening: mobile targets stay finger-safe and reduced-motion wins over every later interaction rule. */
@media(max-width:599px){
  .cui-environment-badge{display:none!important;}
  .cui-button.q-btn,.cui-icon-button.q-btn{height:44px!important;min-height:44px!important;}
  .cui-field-control.q-field{min-height:44px!important;}
  .cui-field-control.q-field:not(.q-textarea) .q-field__inner,.cui-field-control.q-field:not(.q-textarea) .q-field__control{height:44px!important;min-height:44px!important;}
  .cui-choice.q-checkbox,.cui-choice.q-radio,.cui-choice-row{min-height:44px!important;}
}
@media(prefers-reduced-motion:reduce){
  :root{
    --cui-duration-drawer:var(--cui-duration-reduced);--cui-duration-fast:var(--cui-duration-reduced);--cui-duration-feedback:var(--cui-duration-reduced);--cui-duration-instant:var(--cui-duration-reduced);--cui-duration-micro:var(--cui-duration-reduced);--cui-duration-overlay-precise:var(--cui-duration-reduced);--cui-duration-progress:var(--cui-duration-reduced);--cui-duration-progress-long:var(--cui-duration-reduced);--cui-duration-reduced-emphasis:var(--cui-duration-reduced);--cui-duration-section:var(--cui-duration-reduced);--cui-duration-section-lux:var(--cui-duration-reduced);--cui-duration-selection:var(--cui-duration-reduced);--cui-duration-selection-lux:var(--cui-duration-reduced);--cui-duration-shell:var(--cui-duration-reduced);--cui-duration-shimmer:var(--cui-duration-reduced);--cui-duration-spinner:var(--cui-duration-reduced);--cui-duration-spinner-compact:var(--cui-duration-reduced);--cui-duration-spinner-soft:var(--cui-duration-reduced);--cui-duration-table-shimmer:var(--cui-duration-reduced);--cui-duration-title:var(--cui-duration-reduced);--cui-duration-title-long:var(--cui-duration-reduced);--cui-duration-title-lux:var(--cui-duration-reduced);--cui-duration-title-lux-long:var(--cui-duration-reduced);--cui-motion-fast:var(--cui-duration-reduced);--cui-motion-instant:var(--cui-duration-reduced);--cui-motion-overlay:var(--cui-duration-reduced);--cui-motion-standard:var(--cui-duration-reduced);
  }
  *,*::before,*::after{animation-duration:var(--cui-duration-reduced)!important;animation-iteration-count:1!important;transition-duration:var(--cui-duration-reduced)!important;scroll-behavior:auto!important;}
  .cui-drawer,.cui-dialog,.cui-overlay-backdrop,.cui-tooltip--company,.cui-progress.is-indeterminate .cui-progress__bar{animation:none!important;}
}


/* v3.0.0a6 switch focus: keep the row calm and focus the actual interactive track. */
.cui-choice-row--switch:has(.cui-choice-native:focus-visible){background:transparent!important;box-shadow:none!important;}
.cui-choice-row--switch:has(.cui-choice-native:focus-visible) .cui-switch-track{box-shadow:0 0 0 3px color-mix(in srgb,var(--cui-focus-ring) 34%,transparent)!important;}

/* NICEGUI BASE ITERATION 3 VISUAL CLOSURE V6 — SHARED */
/*
   NiceGUI 3.x loads Quasar's !important utility rules in CSS layers. For
   !important declarations, layered rules outrank unlayered rules; joining the
   framework's existing `theme` layer is therefore required for semantic
   Company UI authority to beat Quasar's bg-primary/text-primary utilities.
*/
@layer theme {
  /* Mobile table actions are clean semantic icon actions; accessible names remain on buttons. */
  @media(max-width:620px){
    .cui-table-tool-button .q-label,
    .cui-table-tool-button .cui-table-tool-button__label,
    .cui-table-tool-button .q-btn__content > .block,
    .cui-table-tool-button .q-btn__content > span:not(.q-icon){display:none!important;}
    .cui-table-tool-button .q-btn__content{font-size:0!important;}
    .cui-table-tool-button .q-icon{font-size:var(--cui-font-size-18)!important;}
    .cui-chart-panel__header{flex-direction:column!important;align-items:stretch!important;gap:7px!important;}
    .cui-chart-panel__header>div:first-child{width:100%!important;min-width:0!important;}
    .cui-chart-panel__title{max-width:100%!important;white-space:normal!important;word-break:normal!important;overflow-wrap:break-word!important;}
    .cui-chart-toolbar-host{width:100%!important;margin-left:0!important;}
    .cui-chart-toolbar{justify-content:flex-end!important;flex-wrap:wrap!important;}
    .cui-chart-panel--donut .cui-chart-canvas{height:220px!important;min-height:220px!important;}
  }
  /* Shared semantic button authority owns both the button and Quasar/NiceGUI leaf text. */
  .q-btn.cui-button.cui-button--primary{background:color-mix(in srgb,var(--cui-accent) 70%,black)!important;background-color:color-mix(in srgb,var(--cui-accent) 70%,black)!important;background-image:none!important;color:#fff!important;}
  .q-btn.cui-button.cui-button--primary .q-btn__content,.q-btn.cui-button.cui-button--primary .q-btn__content *{color:inherit!important;}
  .q-btn.cui-button.cui-button--secondary{color:var(--cui-text-primary)!important;}
  .q-btn.cui-button.cui-button--secondary .q-btn__content,.q-btn.cui-button.cui-button--secondary .q-btn__content *{color:inherit!important;}
  html[data-theme='light'] .q-btn.cui-button.cui-button--tertiary{color:color-mix(in srgb,var(--cui-accent) 70%,black)!important;}
  html[data-theme='light'] .q-btn.cui-button.cui-button--tertiary .q-btn__content,html[data-theme='light'] .q-btn.cui-button.cui-button--tertiary .q-btn__content *{color:inherit!important;}
  /* Table toolbar controls share the same layer authority over Quasar text-primary. */
  .q-btn.cui-table-tool-button{color:var(--cui-text-secondary)!important;}
  .q-btn.cui-table-tool-button .q-btn__content,.q-btn.cui-table-tool-button .q-btn__content *{color:inherit!important;}
  .q-btn.cui-table-tool-button:hover{color:var(--cui-text-primary)!important;}
}
'''.strip() + '\n'


__all__ = ['build_hardening_css']

# WAVE35_CONTRAST_CLOSURE_V9
# Final rendered-product contrast closure. Kept in the existing hardening authority
# so local component/layout CSS may evolve without weakening these shared actions.
_wave35_v9_base_build_hardening_css = build_hardening_css

def build_hardening_css() -> str:
    return _wave35_v9_base_build_hardening_css() + r"""
/* Wave 3.5 contrast closure: shared interactive text must remain readable. */
.cui-table-tool-button.q-btn,
.cui-table-tool-button {
  color: var(--cui-text-primary) !important;
}
.cui-user-menu-trigger.q-btn,
.cui-user-menu-trigger {
  color: var(--cui-text-primary) !important;
}
"""

# WAVE35_CONTRAST_FINAL_V11
# Browser-proven Wave 3.5 contrast closure. This wrapper intentionally sits after
# all pre-V11 hardening wrappers and changes only the three paint paths confirmed
# by the V10 browser-native contrast audit.
_wave35_v11_base_build_hardening_css = build_hardening_css

def build_hardening_css() -> str:
    return _wave35_v11_base_build_hardening_css() + r"""
/* Wave 3.5 browser-proven contrast closure. */
.cui-user-menu-trigger.q-btn,
.cui-user-menu-trigger {
  color: var(--cui-text-inverse) !important;
}
html body .cui-table-tool-button.q-btn > .q-btn__content,
html body .cui-table-tool-button.q-btn > .q-btn__content > .q-label,
html body .cui-table-tool-button.q-btn > .q-btn__content > .cui-table-tool-button__label,
html body .cui-table-tool-button .cui-table-tool-button__label {
  color: var(--cui-text-primary) !important;
}
.cui-nav-item--active {
  color: color-mix(in srgb, var(--cui-accent) 90%, var(--cui-text-primary)) !important;
}
"""

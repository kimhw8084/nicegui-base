def build_visual_asset_css()->str:
    return r'''
.cui-icon{display:inline-block;vertical-align:-.18em;flex:0 0 auto;color:currentColor}
.cui-icon-button .cui-icon{pointer-events:none}
.cui-illustration{display:block;max-width:100%;height:auto;color:var(--cui-text-tertiary);margin-inline:auto}
.cui-state-view .cui-illustration{width:min(192px,45vw);opacity:.92}
@media (prefers-reduced-motion:reduce){.cui-icon,.cui-illustration{animation:none!important;transition:none!important}}
'''

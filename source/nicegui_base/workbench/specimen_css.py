"""Small standalone layout layer shared by Studio and exported capability examples."""
from __future__ import annotations

CSS = r'''
.cui-catalog-specimen{--cui-wb-border:var(--cui-border,#d9dee7);--cui-wb-preview:var(--cui-surface,#f8fafc);width:100%;min-width:0;display:flex;flex-direction:column;gap:12px;box-sizing:border-box}
.cui-catalog-specimen>*,.cui-catalog-specimen .cui-component-specimen{min-width:0;max-width:100%;box-sizing:border-box}
.cui-catalog-specimen .cui-component-specimen{display:grid;gap:12px;width:100%}
.cui-catalog-specimen .cui-component-specimen__intro{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.cui-catalog-specimen .cui-component-specimen__stage{display:flex;align-items:center;min-height:120px;padding:18px;border:1px dashed var(--cui-wb-border);border-radius:var(--cui-radius-control);box-sizing:border-box}
.cui-catalog-specimen .cui-component-specimen__demo{display:flex;flex-direction:column;align-items:flex-start;gap:12px;width:100%;max-width:760px}
.cui-catalog-specimen .cui-component-specimen__demo>.cui-field{width:min(100%,620px)}
.cui-catalog-specimen .cui-component-specimen__surface-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;width:100%}
.cui-catalog-specimen .cui-component-specimen__row{display:flex;gap:10px;flex-wrap:wrap}
.cui-catalog-specimen img{max-width:100%;height:auto}
.cui-catalog-specimen pre{max-width:100%;overflow:auto}
@media(max-width:680px){.cui-catalog-specimen .cui-component-specimen__surface-grid{grid-template-columns:1fr}}
'''


def install_specimen_css() -> None:
    from nicegui import ui
    client = ui.context.client
    if getattr(client, '_ngb_d1_specimen_styles', False) is True:
        return
    ui.add_css(CSS)
    setattr(client, '_ngb_d1_specimen_styles', True)

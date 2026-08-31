from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from nicegui_base.design.css import build_css
from nicegui_base.components.css import build_component_css
from nicegui_base.layouts.css import build_layout_css
from nicegui_base.interaction_css import build_interaction_css
from nicegui_base.data_table.css import build_data_table_css
from nicegui_base.visualization.css import build_visualization_css
from nicegui_base.visual.css import build_visual_asset_css
from nicegui_base.engineering.css import build_engineering_css
from nicegui_base.content.css import build_content_css
from nicegui_base.integrations.visual_normalization import build_visual_normalization_css
from nicegui_base.design.system import ThemeMode
from nicegui_base.design.tokens import LIGHT
from nicegui_base.design.constitution_css import build_constitution_css
from nicegui_base.design.hardening_css import build_hardening_css
from nicegui_base.analysis.css import build_analysis_css



@lru_cache(maxsize=1)
def build_framework_css() -> str:
    return "\n".join((build_css(), build_layout_css(), build_component_css(), build_interaction_css(), build_data_table_css(), build_visualization_css(), build_visual_asset_css(), build_engineering_css(), build_content_css(), build_visual_normalization_css(), build_constitution_css(), build_hardening_css(), build_analysis_css()))

_INSTALLED=False

def install_framework_css(ui) -> None:
    """Install the complete NiceGUI Base visual layer exactly once per process."""
    global _INSTALLED
    if _INSTALLED:
        return
    ui.add_css(build_framework_css(), shared=True)
    ui.add_head_html('<meta name="darkreader-lock">', shared=True)
    ui.add_head_html(r'''<script>
window.CompanyUISpatial=window.CompanyUISpatial||{
 state:new Map(),
 get(id){const host=document.getElementById(id);if(!host)return null;const inner=host.querySelector('.cui-spatial-svg-host');if(!inner)return null;let s=this.state.get(id);if(!s){s={scale:1,x:0,y:0};this.state.set(id,s);}return {host,inner,s};},
 clamp(id){const x=this.get(id);if(!x)return null;const maxX=Math.max(0,(x.s.scale-1)*x.host.clientWidth/2),maxY=Math.max(0,(x.s.scale-1)*x.host.clientHeight/2);x.s.x=Math.max(-maxX,Math.min(maxX,x.s.x));x.s.y=Math.max(-maxY,Math.min(maxY,x.s.y));return x;},
 apply(id){const x=this.clamp(id);if(!x)return;x.inner.style.transform=`translate(${x.s.x}px,${x.s.y}px) scale(${x.s.scale})`;x.host.dataset.cuiSpatialScale=x.s.scale.toFixed(3);x.host.dataset.cuiSpatialX=x.s.x.toFixed(1);x.host.dataset.cuiSpatialY=x.s.y.toFixed(1);x.host.dispatchEvent(new CustomEvent('cui-spatial-change',{detail:{scale:x.s.scale,x:x.s.x,y:x.s.y}}));},
 zoom(id,factor){const x=this.get(id);if(!x)return;x.s.scale=Math.max(1,Math.min(4,x.s.scale*factor));if(x.s.scale===1){x.s.x=0;x.s.y=0;}this.apply(id);},
 reset(id){const x=this.get(id);if(!x)return;x.s.scale=1;x.s.x=0;x.s.y=0;this.apply(id);},
 stateOf(id){const x=this.get(id);return x?{scale:x.s.scale,x:x.s.x,y:x.s.y}:null;},
 attach(id){const x=this.get(id);if(!x||x.host.dataset.cuiSpatialAttached)return;x.host.dataset.cuiSpatialAttached='1';let dragging=false,lastX=0,lastY=0;
   x.host.addEventListener('wheel',e=>{e.preventDefault();this.zoom(id,e.deltaY<0?1.12:.89);},{passive:false});
   x.host.addEventListener('dblclick',()=>this.reset(id));
   x.host.addEventListener('pointerdown',e=>{const q=this.get(id);if(!q||q.s.scale<=1)return;dragging=true;lastX=e.clientX;lastY=e.clientY;x.host.setPointerCapture(e.pointerId);x.host.classList.add('is-dragging');});
   x.host.addEventListener('pointermove',e=>{if(!dragging)return;const q=this.get(id);if(!q)return;q.s.x+=e.clientX-lastX;q.s.y+=e.clientY-lastY;lastX=e.clientX;lastY=e.clientY;this.apply(id);});
   const stop=()=>{dragging=false;x.host.classList.remove('is-dragging');};x.host.addEventListener('pointerup',stop);x.host.addEventListener('pointercancel',stop);window.addEventListener('resize',()=>this.apply(id),{passive:true});
 }
};
</script>''', shared=True)
    _INSTALLED=True


@dataclass(slots=True)
class NiceGUIThemeAdapter:
    """Thin NiceGUI integration; all design decisions remain in nicegui_base.design.

    NiceGUI is imported lazily so the design kernel and its tests do not require a
    running browser or NiceGUI import at module import time.
    """

    default_mode: ThemeMode = ThemeMode.SYSTEM
    default_density: str = "compact"
    storage_key: str = "nicegui_base_theme"

    def install(self) -> Any:
        from nicegui import ui  # pinned by pyproject.toml

        ui.colors(
            primary=LIGHT.accent,
            positive=LIGHT.success,
            negative=LIGHT.danger,
            info=LIGHT.info,
            warning=LIGHT.warning,
        )
        install_framework_css(ui)
        ui.add_head_html(f"<script>document.documentElement.dataset.density = document.documentElement.dataset.density || '{self.default_density}';</script>", shared=True)
        dark = ui.dark_mode(value=None if self.default_mode is ThemeMode.SYSTEM else self.default_mode is ThemeMode.DARK)
        return dark

    @staticmethod
    def set_dom_theme_js(mode: ThemeMode) -> str:
        """Return the tiny DOM sync snippet used by a future ThemeService."""
        return f"document.documentElement.dataset.theme='{mode.value}'"

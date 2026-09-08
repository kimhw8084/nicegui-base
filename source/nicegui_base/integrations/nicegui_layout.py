from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from itertools import count
from types import SimpleNamespace
from importlib import metadata
from typing import Any, Callable
import inspect
import json

from nicegui_base.integrations.nicegui_theme import install_framework_css
from nicegui_base.visual import render_icon_svg
from nicegui_base.layouts.models import SidebarMode
from nicegui_base.navigation import Breadcrumb, NavigationModel, NavItem, TabSpec
from nicegui_base.version import FRAMEWORK_VERSION


_LAYOUT_IDS = count(1)


_MOBILE_NAV_A11Y_RUNTIME = r'''<script>(()=>{
  const root=document.documentElement;
  if(window.CompanyUIMobileNavObserver)return;
  const focusables=drawer=>[...drawer.querySelectorAll('button,a[href],input,select,textarea,[contenteditable="true"],[tabindex]:not([tabindex="-1"])')]
    .filter(el=>!el.disabled&&el.getAttribute('aria-hidden')!=='true'&&getComputedStyle(el).display!=='none'&&getComputedStyle(el).visibility!=='hidden'&&el.getClientRects().length>0);
  const state={open:root.dataset.mobileNav==='open',opener:null};
  const drawer=()=>document.querySelector('.cui-mobile-nav-drawer');
  const layer=()=>document.querySelector('.cui-mobile-nav-layer');
  const visible=el=>el instanceof HTMLElement&&el.isConnected&&getComputedStyle(el).display!=='none'&&getComputedStyle(el).visibility!=='hidden'&&el.getClientRects().length>0;
  const syncSemantics=open=>{
    const d=drawer(),l=layer();
    if(d){d.setAttribute('role','dialog');d.setAttribute('aria-modal','true');d.setAttribute('aria-label',d.getAttribute('aria-label')||'Mobile navigation');}
    if(l)l.setAttribute('aria-hidden',open?'false':'true');
  };
  const sync=()=>{
    const open=root.dataset.mobileNav==='open';
    syncSemantics(open);
    if(open&&!state.open){
      const active=document.activeElement;
      state.opener=visible(active)?active:document.querySelector('.cui-shell-mobile-menu');
      requestAnimationFrame(()=>{
        const d=drawer(),items=d?focusables(d):[];
        (items[0]||d)?.focus?.();
      });
    }else if(!open&&state.open){
      const target=state.opener;
      requestAnimationFrame(()=>{if(visible(target))target.focus();});
    }
    state.open=open;
  };
  new MutationObserver(sync).observe(root,{attributes:true,attributeFilter:['data-mobile-nav']});
  window.addEventListener('keydown',event=>{
    if(root.dataset.mobileNav!=='open')return;
    const d=drawer();if(!d)return;
    if(event.key==='Escape'&&!event.defaultPrevented){event.preventDefault();root.dataset.mobileNav='closed';return;}
    if(event.key!=='Tab')return;
    const items=focusables(d);if(!items.length)return;
    const first=items[0],last=items[items.length-1],active=document.activeElement;
    if(event.shiftKey&&(active===first||!d.contains(active))){event.preventDefault();last.focus();}
    else if(!event.shiftKey&&(active===last||!d.contains(active))){event.preventDefault();first.focus();}
  },true);
  window.CompanyUIMobileNavObserver={sync};
  syncSemantics(state.open);
})();</script>'''


def _install_mobile_nav_a11y_runtime(ui) -> None:
    ui.add_head_html(_MOBILE_NAV_A11Y_RUNTIME, shared=True)


# WAVE35_CONTRAST_AUTHORITY_V19: layout-owned buttons delegate color to semantic CSS, not Quasar primary.

def _ui():
    try:
        from nicegui import ui
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError('NiceGUI is required to render the company UI shell.') from exc
    return ui


def _icon(ui, key: str, *, label: str | None = None, size: str = 'sm'):
    return ui.html(render_icon_svg(key, size=size, label=label), sanitize=False).classes('cui-svg-icon-host')


def _default_navigate(route: str) -> Any:
    return _ui().navigate.to(route)


def _nav_visible(item: NavItem, permission_check: Callable[[str], bool] | None) -> bool:
    if item.permission and (permission_check is None or not permission_check(item.permission)):
        return False
    if item.children:
        return any(_nav_visible(child, permission_check) for child in item.children)
    return True


def _render_nav_item(item: NavItem, *, active_route: str | None, navigate: Callable[[str], None],
                     permission_check: Callable[[str], bool] | None = None) -> None:
    """Render navigation without Material-icon dependencies.

    Child groups deliberately use Company-owned markup rather than Quasar's
    expansion header. This keeps icon geometry deterministic in the compact rail.
    """
    ui = _ui()
    if not _nav_visible(item, permission_check):
        return
    if item.children:
        with ui.element('div').classes('cui-nav-group'):
            with ui.element('div').classes('cui-nav-group__label'):
                if item.icon:
                    _icon(ui, item.icon, size='sm')
                ui.label(item.label).classes('cui-nav-group__text')
            with ui.element('div').classes('cui-nav-group__children'):
                for child in item.children:
                    _render_nav_item(child, active_route=active_route, navigate=navigate, permission_check=permission_check)
        return
    active = item.route == active_route
    classes = 'cui-nav-item' + (' cui-nav-item--active' if active else '')
    async def _activate(e=None, route=item.route):
        result = navigate(route)
        if inspect.isawaitable(result):
            await result
    with ui.item(on_click=_activate).classes(classes).props(
        f'aria-current={"page" if active else "false"} title="{item.label}"'
    ):
        with ui.item_section().props('avatar').classes('cui-nav-item__icon'):
            _icon(ui, item.icon or 'grid', size='sm')
        with ui.item_section().classes('cui-nav-item__copy'):
            ui.item_label(item.label)
        if item.badge is not None:
            with ui.item_section().props('side').classes('cui-nav-item__badge'):
                ui.badge(str(item.badge)).classes('cui-count-badge')


def _render_navigation(nav: NavigationModel, *, active_route: str | None = None,
                       navigate: Callable[[str], None] | None = None,
                       permission_check: Callable[[str], bool] | None = None) -> None:
    ui = _ui(); navigate = navigate or _default_navigate
    for section in nav.sections:
        visible_items = tuple(item for item in section.items if _nav_visible(item, permission_check))
        if not visible_items:
            continue
        with ui.element('section').classes('cui-nav-section'):
            if section.label:
                ui.label(section.label).classes('cui-nav-section-label')
            with ui.element('div').classes('cui-nav-section__items'):
                for item in visible_items:
                    _render_nav_item(item, active_route=active_route, navigate=navigate, permission_check=permission_check)


def _render_support_footer(*, owner: str | None, on_support: Callable[[], None] | None,
                           on_feedback: Callable[[], None] | None, on_docs: Callable[[], None] | None,
                           environment: str | None = None) -> None:
    """Render owner/support actions plus runtime identity in every governed sidebar."""
    ui = _ui()

    def action(icon: str, label: str, callback: Callable[[], None]) -> None:
        async def _run(e=None):
            result = callback()
            if inspect.isawaitable(result):
                await result
        with ui.element('button').classes('cui-sidebar-footer__action').props(
            f'type="button" aria-label="{label}" title="{label}"'
        ).on('click', _run):
            _icon(ui, icon, label=label, size='xs')
            ui.label(label).classes('cui-sidebar-footer__action-label').props('aria-hidden="true"')

    try:
        nicegui_version = metadata.version('nicegui')
    except metadata.PackageNotFoundError:
        nicegui_version = 'not installed'

    with ui.element('footer').classes('cui-sidebar-footer'):
        if owner:
            with ui.element('div').classes('cui-sidebar-owner').props('title="Owner / support team"'):
                _icon(ui, 'users', label='Owner', size='xs')
                with ui.element('div').classes('cui-sidebar-owner__copy'):
                    ui.label('Owned & supported by').classes('cui-sidebar-owner__label')
                    ui.label(owner).classes('cui-sidebar-owner__name')
        with ui.element('div').classes('cui-sidebar-footer__actions'):
            if on_support: action('help', 'Support', on_support)
            if on_docs: action('file', 'Documentation', on_docs)
        with ui.element('div').classes('cui-sidebar-version').props('title="Runtime version information"'):
            ui.label('Version').classes('cui-sidebar-version__label cui-sidebar-version__full')
            ui.label(f'NiceGUI Base {FRAMEWORK_VERSION}').classes('cui-sidebar-version__value cui-sidebar-version__full')
            ui.label(f'NiceGUI {nicegui_version}').classes('cui-sidebar-version__runtime cui-sidebar-version__full')
            if environment:
                ui.label(environment.upper()).classes('cui-sidebar-version__runtime cui-sidebar-version__full')
            ui.label('v' + FRAMEWORK_VERSION).classes('cui-sidebar-version__compact')


@dataclass(slots=True)
class ShellConfig:
    title: str
    navigation: NavigationModel | None = None
    active_route: str | None = None
    sidebar: SidebarMode = SidebarMode.AUTO
    environment: str | None = None
    on_navigate: Callable[[str], None] | None = None
    subtitle: str | None = None
    greeting: str | None = None
    user_name: str | None = None
    user_initials: str = 'U'
    on_settings: Callable[[], None] | None = None
    on_about: Callable[[], None] | None = None
    on_logout: Callable[[], None] | None = None
    owner: str | None = None
    on_support: Callable[[], None] | None = None
    on_feedback: Callable[[], None] | None = None
    on_docs: Callable[[], None] | None = None
    permission_check: Callable[[str], bool] | None = None
    debugger: bool = True
    debugger_health_provider: Callable[[], Any] | None = None


class AppShell(AbstractContextManager):
    """Company-standard single-process application shell.

    ``title`` is the *application* title. Current route/view identity belongs in a
    :class:`PageHeader` rendered inside the main content region. Desktop navigation
    geometry and mobile navigation are both Company-owned markup; NiceGUI only carries events/state.
    """
    def __init__(self, title: str, navigation: NavigationModel | None = None, *, active_route: str | None = None,
                 sidebar: SidebarMode = SidebarMode.AUTO, environment: str | None = None,
                 on_navigate: Callable[[str], None] | None = None, subtitle: str | None = None,
                 greeting: str | None = None, user_name: str | None = None, user_initials: str = 'U',
                 on_settings: Callable[[], None] | None = None, on_about: Callable[[], None] | None = None,
                 on_logout: Callable[[], None] | None = None, owner: str | None = None,
                 on_support: Callable[[], None] | None = None, on_feedback: Callable[[], None] | None = None,
                 on_docs: Callable[[], None] | None = None, permission_check: Callable[[str], bool] | None = None,
                 debugger: bool = True, debugger_health_provider: Callable[[], Any] | None = None):
        self.config = ShellConfig(title, navigation, active_route, sidebar, environment, on_navigate, subtitle,
                                  greeting, user_name, user_initials, on_settings, on_about, on_logout,
                                  owner, on_support, on_feedback, on_docs, permission_check, debugger, debugger_health_provider)
        self.header = None; self.sidebar = None; self.mobile_drawer = None; self.main = None; self.debugger = None

    async def _navigate(self, route: str) -> None:
        if self.mobile_drawer is not None:
            await self.mobile_drawer.close()
        result = self.config.on_navigate(route) if self.config.on_navigate else _default_navigate(route)
        if inspect.isawaitable(result):
            await result

    async def _toggle_sidebar(self):
        return await _ui().run_javascript("""(() => {
          const root=document.documentElement;
          const compact=root.dataset.sidebar==='compact';
          root.dataset.sidebar=compact?'expanded':'compact';
          try{localStorage.setItem('nicegui_base_sidebar',root.dataset.sidebar);}catch(e){}
          return root.dataset.sidebar;
        })()""")

    async def _toggle_mobile(self):
        # The DOM state is the single mobile-nav authority. Toggling it directly
        # avoids a timing dependency on the drawer object being assigned after
        # the header button is constructed.
        return await _ui().run_javascript(
            "document.documentElement.dataset.mobileNav=document.documentElement.dataset.mobileNav==='open'?'closed':'open'"
        )

    def __enter__(self):
        ui = _ui(); install_framework_css(ui); ui.query('.nicegui-content').classes('cui-nicegui-content')
        ui.add_head_html("""<script>(()=>{
          const root=document.documentElement;
          try{root.dataset.sidebar=localStorage.getItem('nicegui_base_sidebar')||root.dataset.sidebar||'expanded'}catch(e){root.dataset.sidebar=root.dataset.sidebar||'expanded'}
          root.dataset.mobileNav='closed';
          if(!window.__cuiResponsiveNavInstalled){
            window.__cuiResponsiveNavInstalled=true;
            window.addEventListener('resize',()=>{if(window.innerWidth>=900) document.documentElement.dataset.mobileNav='closed'},{passive:true});
          }
        })();</script>""", shared=True)
        if self.config.sidebar is SidebarMode.COMPACT:
            ui.run_javascript("document.documentElement.dataset.sidebar='compact'")
        ui.link('Skip to main content', '#cui-main-content').classes('cui-skip-link')

        # Company-owned fixed header. NiceGUI/Quasar no longer owns shell geometry.
        with ui.element('header').classes('cui-app-header').props('role="banner"') as self.header:
            with ui.element('div').classes('cui-shell-brand'):
                with ui.element('div').classes('cui-shell-title-block'):
                    ui.label(self.config.title).classes('cui-shell-title cui-shell-title--animated')
                    if self.config.subtitle: ui.label(self.config.subtitle).classes('cui-shell-subtitle')
                if self.config.debugger:
                    from nicegui_base.integrations.nicegui_debugger import DebuggerConfig, UniversalDebugger
                    self.debugger = UniversalDebugger(DebuggerConfig(
                        app_name=self.config.title, app_version=FRAMEWORK_VERSION, environment=self.config.environment or '',
                        health_provider=self.config.debugger_health_provider,
                    ))
                    self.debugger.trigger()
            with ui.element('div').classes('cui-shell-actions'):
                # Mobile navigation exists only when desktop navigation no longer fits,
                # and lives with actions rather than beside the application title.
                if self.config.navigation:
                    mobile = ui.button(on_click=self._toggle_mobile, color=None).props('flat round dense aria-label="Open navigation" title="Navigation"').classes('cui-shell-mobile-menu cui-icon-button')
                    with mobile: _icon(ui, 'menu', label='Navigation')
                if self.config.environment: EnvironmentBadge(self.config.environment)
                if self.config.on_settings or self.config.on_about:
                    _ApplicationMenu(
                        environment=self.config.environment,
                        on_settings=self.config.on_settings,
                        on_about=self.config.on_about,
                    )
                if self.config.user_name or self.config.greeting or self.config.on_about or self.config.on_logout:
                    with ui.element('div').classes('cui-shell-user'):
                        if self.config.user_name or self.config.greeting:
                            with ui.element('div').classes('cui-shell-greeting'):
                                if self.config.greeting: ui.label(self.config.greeting).classes('cui-shell-greeting__hello')
                                if self.config.user_name: ui.label(self.config.user_name).classes('cui-shell-greeting__name')
                        UserMenu(
                            self.config.user_initials,
                            user_name=self.config.user_name,
                            greeting=self.config.greeting,
                            on_preferences=self.config.on_settings,
                            on_about=self.config.on_about,
                            on_logout=self.config.on_logout,
                        )

        if self.config.navigation and self.config.sidebar is not SidebarMode.HIDDEN:
            with ui.element('aside').classes('cui-app-sidebar').props('aria-label="Application navigation"') as self.sidebar:
                with ui.element('div').classes('cui-sidebar-top'):
                    collapse = ui.button(on_click=self._toggle_sidebar, color=None).props('flat round dense aria-label="Collapse or expand navigation" title="Collapse / expand navigation"').classes('cui-icon-button cui-sidebar-collapse')
                    with collapse:
                        with ui.element('span').classes('cui-sidebar-collapse__expanded'): _icon(ui, 'chevron-left', label='Collapse navigation')
                        with ui.element('span').classes('cui-sidebar-collapse__compact'): _icon(ui, 'chevron-right', label='Expand navigation')
                with ui.element('nav').classes('cui-sidebar-nav').props('aria-label="Primary navigation"'):
                    _render_navigation(self.config.navigation, active_route=self.config.active_route, navigate=self._navigate, permission_check=self.config.permission_check)
                _render_support_footer(owner=self.config.owner, on_support=self.config.on_support,
                                       on_feedback=self.config.on_feedback, on_docs=self.config.on_docs, environment=self.config.environment)
            self.mobile_drawer = MobileNavigationDrawer(
                self.config.navigation, active_route=self.config.active_route, on_navigate=self._navigate, value=False,
                owner=self.config.owner, on_support=self.config.on_support, on_feedback=self.config.on_feedback, on_docs=self.config.on_docs,
                permission_check=self.config.permission_check,
            )
            self.mobile_drawer.__enter__(); self.mobile_drawer.__exit__(None, None, None)

        main_classes = 'cui-app-main' + (' cui-app-main--with-sidebar' if self.config.navigation and self.config.sidebar is not SidebarMode.HIDDEN else '')
        self.main = ui.column().classes(main_classes).props('id="cui-main-content" tabindex="-1" role="main"')
        self.main.__enter__(); return self

    def __exit__(self, exc_type, exc, tb):
        return self.main.__exit__(exc_type, exc, tb)


class PageHeader:
    def __init__(self, title: str, description: str | None = None, *, breadcrumbs: tuple[Breadcrumb, ...] = ()):
        ui = _ui()
        with ui.element('header').classes('cui-page-header'):
            with ui.element('div').classes('cui-page-header__copy'):
                if breadcrumbs:
                    with ui.element('nav').classes('cui-breadcrumbs').props('aria-label="Breadcrumb"'):
                        for index, crumb in enumerate(breadcrumbs):
                            if index: ui.label('/').classes('cui-breadcrumb-separator').props('aria-hidden="true"')
                            if crumb.route: ui.link(crumb.label, crumb.route).classes('cui-breadcrumb')
                            else: ui.label(crumb.label).classes('cui-breadcrumb').props('aria-current="page"')
                ui.label(title).classes('cui-page-title')
                if description: ui.label(description).classes('cui-page-description')
        self.title = title


class Tabs(AbstractContextManager):
    def __init__(self, specs: tuple[TabSpec, ...], *, value: str | None = None):
        if not specs: raise ValueError('Tabs require at least one TabSpec.')
        self.specs = specs; self.value = value or specs[0].id; self.tabs = None; self.panels = None
    def __enter__(self):
        ui = _ui(); self.tabs = ui.tabs(value=self.value).classes('cui-tabs-region').props('aria-label="Sections"')
        with self.tabs:
            for spec in self.specs:
                tab = ui.tab(spec.id, label=spec.label).classes('cui-tab')
                if spec.disabled: tab.props('disable')
        self.panels = ui.tab_panels(self.tabs, value=self.value).classes('cui-tab-panels'); self.panels.__enter__(); return self
    def panel(self, tab_id: str):
        if tab_id not in {spec.id for spec in self.specs}: raise KeyError(f'Unknown tab id: {tab_id}')
        return _ui().tab_panel(tab_id)
    def __exit__(self, exc_type, exc, tb): return self.panels.__exit__(exc_type, exc, tb)


class EnvironmentBadge:
    def __init__(self, environment: str):
        if not environment.strip(): raise ValueError('environment cannot be empty')
        value = environment.strip().lower()
        if any(k in value for k in ('prod', 'production')): tone = 'production'
        elif any(k in value for k in ('stage', 'staging', 'uat', 'preprod')): tone = 'staging'
        elif any(k in value for k in ('dev', 'development', 'local', 'lab', 'test')): tone = 'development'
        else: tone = 'neutral'
        ui = _ui()
        with ui.element('span').classes(f'cui-environment-badge cui-environment-badge--{tone}').props(f'aria-label="Environment {environment.upper()}"') as self.element:
            ui.element('span').classes('cui-environment-badge__dot').props('aria-hidden="true"')
            ui.label(environment.upper()).classes('cui-environment-badge__label')


class AppHeader(AbstractContextManager):
    """Standalone Company-owned application header used by primitive demonstrations."""
    def __init__(self, title: str, *, subtitle: str | None = None, environment: str | None = None,
                 greeting: str | None = None, user_name: str | None = None, user_initials: str = 'U',
                 on_settings: Callable[[], None] | None = None, on_about: Callable[[], None] | None = None,
                 on_mobile_navigation: Callable[[], None] | None = None):
        self.title = title; self.subtitle = subtitle; self.environment = environment; self.greeting = greeting
        self.user_name = user_name; self.user_initials = user_initials; self.on_settings = on_settings; self.on_about = on_about
        self.on_mobile_navigation = on_mobile_navigation; self.element = None
    def __enter__(self):
        ui = _ui(); install_framework_css(ui); self.element = ui.element('header').classes('cui-app-header').props('role="banner"'); self.element.__enter__()
        with ui.element('div').classes('cui-shell-brand'):
            with ui.element('div').classes('cui-shell-title-block'):
                ui.label(self.title).classes('cui-shell-title cui-shell-title--animated')
                if self.subtitle: ui.label(self.subtitle).classes('cui-shell-subtitle')
        with ui.element('div').classes('cui-shell-actions'):
            if self.on_mobile_navigation:
                b=ui.button(on_click=self.on_mobile_navigation, color=None).props('flat round dense aria-label="Open navigation" title="Navigation"').classes('cui-shell-mobile-menu cui-icon-button')
                with b: _icon(ui,'menu',label='Navigation')
            if self.environment: EnvironmentBadge(self.environment)
            if self.on_settings or self.on_about: _ApplicationMenu(environment=self.environment,on_settings=self.on_settings,on_about=self.on_about)
            if self.user_name or self.greeting:
                with ui.element('div').classes('cui-shell-user'):
                    with ui.element('div').classes('cui-shell-greeting'):
                        if self.greeting: ui.label(self.greeting).classes('cui-shell-greeting__hello')
                        if self.user_name: ui.label(self.user_name).classes('cui-shell-greeting__name')
                    UserMenu(self.user_initials,user_name=self.user_name,greeting=self.greeting,on_preferences=self.on_settings,on_about=self.on_about)
        return self
    def __exit__(self, exc_type, exc, tb): return self.element.__exit__(exc_type, exc, tb)


class AppSidebar(AbstractContextManager):
    """Standalone Company-owned desktop navigation rail."""
    def __init__(self, navigation: NavigationModel, *, width: int = 264, breakpoint: int = 900,
                 active_route: str | None = None, on_navigate: Callable[[str], None] | None = None,
                 value: bool = True, owner: str | None = None, on_support: Callable[[], None] | None = None,
                 on_feedback: Callable[[], None] | None = None, on_docs: Callable[[], None] | None = None,
                 permission_check: Callable[[str], bool] | None = None):
        self.navigation = navigation; self.width = width; self.breakpoint = breakpoint; self.active_route = active_route
        self.on_navigate = on_navigate or _default_navigate; self.value = value; self.owner = owner
        self.on_support = on_support; self.on_feedback = on_feedback; self.on_docs = on_docs; self.permission_check = permission_check; self.element = None
    async def _toggle(self):
        return await _ui().run_javascript("document.documentElement.dataset.sidebar=document.documentElement.dataset.sidebar==='compact'?'expanded':'compact'")
    def __enter__(self):
        ui = _ui(); install_framework_css(ui); ui.run_javascript("document.documentElement.dataset.sidebar=document.documentElement.dataset.sidebar||'expanded'")
        self.element = ui.element('aside').classes('cui-app-sidebar').props('aria-label="Application navigation"'); self.element.__enter__()
        with ui.element('div').classes('cui-sidebar-top'):
            b = ui.button(on_click=self._toggle, color=None).props('flat round dense aria-label="Collapse or expand navigation" title="Collapse / expand navigation"').classes('cui-icon-button cui-sidebar-collapse')
            with b:
                with ui.element('span').classes('cui-sidebar-collapse__expanded'): _icon(ui,'chevron-left',label='Collapse navigation')
                with ui.element('span').classes('cui-sidebar-collapse__compact'): _icon(ui,'chevron-right',label='Expand navigation')
        with ui.element('nav').classes('cui-sidebar-nav'):
            _render_navigation(self.navigation, active_route=self.active_route, navigate=self.on_navigate, permission_check=self.permission_check)
        _render_support_footer(owner=self.owner, on_support=self.on_support, on_feedback=self.on_feedback, on_docs=self.on_docs)
        return self
    def __exit__(self, exc_type, exc, tb): return self.element.__exit__(exc_type, exc, tb)


class MobileNavigationDrawer(AbstractContextManager):
    """Company-owned temporary navigation overlay used only below the mobile breakpoint."""
    def __init__(self, navigation: NavigationModel, *, active_route: str | None = None,
                 on_navigate: Callable[[str], None] | None = None, value: bool = False,
                 owner: str | None = None, on_support: Callable[[], None] | None = None,
                 on_feedback: Callable[[], None] | None = None, on_docs: Callable[[], None] | None = None,
                 permission_check: Callable[[str], bool] | None = None):
        self.navigation = navigation; self.active_route = active_route; self.on_navigate = on_navigate or _default_navigate
        self.value = value; self.owner = owner; self.on_support = on_support; self.on_feedback = on_feedback; self.on_docs = on_docs
        self.permission_check = permission_check; self.element = None
    def __enter__(self):
        ui = _ui(); install_framework_css(ui)
        _install_mobile_nav_a11y_runtime(ui)
        with ui.element('div').classes('cui-mobile-nav-layer') as self.element:
            ui.element('button').classes('cui-mobile-nav-backdrop').props('type="button" aria-label="Close navigation"').on('click', self.close)
            with ui.element('aside').classes('cui-mobile-nav-drawer').props('aria-label="Mobile navigation"'):
                with ui.element('div').classes('cui-mobile-nav-head'):
                    with ui.element('div').classes('cui-mobile-nav-head__copy'):
                        ui.label('Navigation').classes('cui-mobile-nav-title')
                        ui.label('Application sections').classes('cui-mobile-nav-subtitle')
                    b = ui.button(on_click=self.close, color=None).props('flat round aria-label="Close navigation" title="Close navigation"').classes('cui-icon-button')
                    with b: _icon(ui, 'close', label='Close navigation')
                with ui.element('nav').classes('cui-mobile-nav-body'):
                    _render_navigation(self.navigation, active_route=self.active_route, navigate=self.on_navigate, permission_check=self.permission_check)
                _render_support_footer(owner=self.owner, on_support=self.on_support, on_feedback=self.on_feedback, on_docs=self.on_docs)
        if self.value:
            # Root dataset state is safe to set immediately; it does not depend on
            # the drawer element being mounted and therefore needs no Timer.
            ui.run_javascript("document.documentElement.dataset.mobileNav='open'")
        return self
    def __exit__(self, exc_type, exc, tb): return False
    async def open(self): return await _ui().run_javascript("document.documentElement.dataset.mobileNav='open'")
    async def close(self): return await _ui().run_javascript("document.documentElement.dataset.mobileNav='closed'")
    async def toggle(self):
        return await _ui().run_javascript("document.documentElement.dataset.mobileNav=document.documentElement.dataset.mobileNav==='open'?'closed':'open'")


class _ApplicationMenu:
    """Compact real application/settings surface, not a toast-only icon."""
    def __init__(self, *, environment: str | None = None, on_settings: Callable[[], None] | None = None,
                 on_about: Callable[[], None] | None = None):
        ui=_ui()
        with ui.button(color=None).props('flat round dense aria-label="Application settings" title="Application settings"').classes('cui-icon-button cui-shell-settings'):
            _icon(ui,'settings',label='Application settings')
            with ui.menu().props('anchor="bottom right" self="top right" :offset="[0,8]"').classes('cui-menu cui-shell-settings-menu cui-account-popover cui-overlay-surface cui-overlay-surface--popover'):
                with ui.element('div').classes('cui-account-popover__head'):
                    ui.label('Application').classes('cui-account-popover__title')
                    ui.label('Workspace preferences and information').classes('cui-account-popover__subtitle')
                with ui.element('div').classes('cui-account-popover__meta'):
                    with ui.element('div').classes('cui-account-popover__meta-row'):
                        ui.label('Appearance').classes('cui-account-popover__key'); ui.label('System preference').classes('cui-account-popover__value')
                    if environment:
                        with ui.element('div').classes('cui-account-popover__meta-row'):
                            ui.label('Environment').classes('cui-account-popover__key'); ui.label(environment.upper()).classes('cui-account-popover__value')
                if on_settings:
                    b=ui.button(on_click=on_settings, color=None).props('flat no-caps').classes('cui-menu-item cui-menu-item--with-icon')
                    with b: _icon(ui,'settings',size='xs'); ui.label('Open application settings')
                if on_about:
                    b=ui.button(on_click=on_about, color=None).props('flat no-caps').classes('cui-menu-item cui-menu-item--with-icon')
                    with b: _icon(ui,'info',size='xs'); ui.label('About this application')


class UserMenu:
    def __init__(self, initials: str = 'U', *, user_name: str | None = None, greeting: str | None = None,
                 on_preferences: Callable[[], None] | None = None, on_about: Callable[[], None] | None = None,
                 on_logout: Callable[[], None] | None = None):
        ui = _ui()
        with ui.button(initials[:2].upper(), color=None).props('flat round dense aria-label="User profile" title="User profile"').classes('cui-user-menu-trigger'):
            with ui.menu().props('anchor="bottom right" self="top right" :offset="[0,8]"').classes('cui-user-menu cui-menu cui-account-popover cui-overlay-surface cui-overlay-surface--popover'):
                with ui.element('div').classes('cui-account-popover__identity'):
                    ui.label(initials[:2].upper()).classes('cui-account-avatar')
                    with ui.element('div').classes('cui-account-popover__identity-copy'):
                        ui.label(user_name or 'Current user').classes('cui-account-popover__title')
                        if greeting: ui.label(greeting).classes('cui-account-popover__subtitle')
                if on_preferences:
                    b=ui.button(on_click=on_preferences, color=None).props('flat no-caps').classes('cui-menu-item cui-menu-item--with-icon')
                    with b: _icon(ui,'settings',size='xs'); ui.label('Preferences')
                if on_about:
                    b=ui.button(on_click=on_about, color=None).props('flat no-caps').classes('cui-menu-item cui-menu-item--with-icon')
                    with b: _icon(ui,'info',size='xs'); ui.label('About')
                if on_logout:
                    ui.separator().classes('cui-menu-separator')
                    b=ui.button(on_click=on_logout, color=None).props('flat no-caps').classes('cui-menu-item cui-menu-item--with-icon is-danger')
                    with b: _icon(ui,'logout',size='xs'); ui.label('Sign out')


class AppInfoDialog:
    def __init__(self, app_name: str, version: str, *, environment: str | None = None, framework_version: str = FRAMEWORK_VERSION):
        ui = _ui(); dialog_id = next(_LAYOUT_IDS)
        self.title_id = f'cui-app-info-title-{dialog_id}'
        self.description_id = f'cui-app-info-description-{dialog_id}'
        self.dialog = ui.dialog().props('transition-show=fade transition-hide=fade')
        with self.dialog, ui.element('section').classes('cui-dialog cui-dialog--small cui-app-info-dialog cui-overlay-surface cui-overlay-surface--dialog').props(f'role="dialog" aria-modal="true" aria-labelledby="{self.title_id}" aria-describedby="{self.description_id}" data-cui-overlay="dialog"'):
            with ui.element('div').classes('cui-dialog__head'):
                with ui.element('div').classes('cui-dialog__copy'):
                    ui.label(app_name).props(f'id="{self.title_id}"').classes('cui-dialog__title')
                    ui.label(f'Application version {version}').props(f'id="{self.description_id}"').classes('cui-dialog__description')
                    ui.label(f'Framework {framework_version}').classes('cui-dialog__description')
                    if environment: ui.label(f'Environment {environment.upper()}').classes('cui-dialog__description')
                close = ui.button(on_click=self.close, color=None).props('flat round aria-label="Close"').classes('cui-icon-button cui-dialog__close')
                with close: _icon(ui, 'close', label='Close')
            with ui.element('div').classes('cui-dialog__footer'):
                ui.element('div').classes('cui-dialog__footer-spacer')
                ui.button('Close', on_click=self.close, color=None).props('flat no-caps').classes('cui-button cui-button--secondary cui-control--medium')
    def open(self) -> None:
        self.dialog.open()
        _ui().run_javascript("window.__companyUiTooltip?.hide?.();document.dispatchEvent(new CustomEvent('cui:overlay-open',{detail:{kind:'dialog'}}));")
    def close(self) -> None:
        self.dialog.close()


class SegmentedControl:
    """Deterministic company-owned segmented choice control.

    NiceGUI/Quasar provide button mechanics only; this wrapper owns semantic
    radiogroup state, accessible option naming, and truthful programmatic state.
    """
    def __init__(self, options: dict[str, str], *, value: str | None = None, on_change: Callable[..., Any] | None = None):
        if not options:
            raise ValueError('SegmentedControl requires options.')
        ui = _ui()
        self._options = dict(options)
        self.value = value if value in self.options else next(iter(self.options))
        self._on_change = on_change
        self._buttons: dict[str, Any] = {}
        with ui.element('div').classes('cui-segmented-control q-btn-toggle cui-segmented-control--semantic-v4 cui-segmented-control--semantic-v8').props(
            'role="radiogroup" aria-label="Segmented options"'
        ) as self.element:
            for key, label in self.options.items():
                selected = key == self.value
                async def choose(_e=None, key=key):
                    await self._select(key)
                button = ui.button(str(label), on_click=choose, color=None).props(
                    f'flat no-caps unelevated role="radio" aria-label={json.dumps(str(label))} aria-checked="{str(selected).lower()}"'
                )
                if selected:
                    button.classes(add='q-btn--active')
                self._buttons[key] = button

    @property
    def options(self) -> dict[str, str]:
        return self._options

    @options.setter
    def options(self, value: dict[str, str]) -> None:
        self._options = value

    async def set_value(self, value: str, *, emit: bool = False) -> None:
        if value not in self.options:
            return
        self.value = value
        for key, button in self._buttons.items():
            selected = key == value
            button.props(f'aria-checked="{str(selected).lower()}"')
            if selected:
                button.classes(add='q-btn--active')
            else:
                button.classes(remove='q-btn--active')
        if emit and self._on_change is not None:
            result = self._on_change(SimpleNamespace(value=value))
            if inspect.isawaitable(result):
                await result

    async def _select(self, value: str) -> None:
        await self.set_value(value, emit=True)


class BackNavigation:
    def __init__(self, label: str = 'Back', *, on_click: Callable[[], None] | None = None):
        ui = _ui(); self.element = ui.button(on_click=on_click or ui.navigate.back, color=None).props('flat no-caps').classes('cui-back-navigation cui-button cui-button--ghost cui-control--medium')
        with self.element: _icon(ui, 'arrow-left', size='xs'); ui.label(label)


class PageNavigation:
    def __init__(self, *, previous: tuple[str, Callable[[], None]] | None = None,
                 next: tuple[str, Callable[[], None]] | None = None):
        ui = _ui()
        with ui.element('nav').classes('cui-page-navigation').props('aria-label="Page navigation"'):
            if previous:
                b = ui.button(on_click=previous[1], color=None).props('flat no-caps').classes('cui-button cui-button--ghost cui-control--medium')
                with b: _icon(ui, 'arrow-left', size='xs'); ui.label(previous[0])
            else: ui.element('span')
            if next:
                b = ui.button(on_click=next[1], color=None).props('flat no-caps').classes('cui-button cui-button--ghost cui-control--medium')
                with b: ui.label(next[0]); _icon(ui, 'arrow-right', size='xs')


__all__ = [
    'ShellConfig', 'AppShell', 'PageHeader', 'Tabs', 'EnvironmentBadge', 'AppHeader', 'AppSidebar',
    'MobileNavigationDrawer', 'UserMenu', 'AppInfoDialog', 'SegmentedControl', 'BackNavigation', 'PageNavigation',
]

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConvenienceDefinition:
    key: str
    category: str
    purpose: str
    use_when: str


CONVENIENCE_REGISTRY = {
    item.key: item for item in (
        ConvenienceDefinition('state_store','state','Observable framework-agnostic state with atomic updates.','Local/page/session state must notify dependents without UI coupling.'),
        ConvenienceDefinition('user_preferences','state','Typed persistent UI preferences.','Theme, density, sidebar, table layouts, filters, favorites or recent entities must persist.'),
        ConvenienceDefinition('url_state','state','Typed deterministic URL query serialization.','Analytical state should be shareable/bookmarkable.'),
        ConvenienceDefinition('async_action','async','Timeout-aware duplicate-safe async action.','Buttons or commands invoke service work.'),
        ConvenienceDefinition('cancelable_task','async','Latest-request-wins cancellable task.','Search/filter/data requests can supersede older requests.'),
        ConvenienceDefinition('auto_refresh','async','Managed periodic refresh with stale/error status.','Monitoring pages need periodic data updates.'),
        ConvenienceDefinition('debouncer','async','Delay bursty operations until input settles.','Search/filter inputs would otherwise create excessive service calls.'),
        ConvenienceDefinition('stale_response_guard','async','Prevent older responses overwriting newer state.','Concurrent requests can resolve out of order.'),
        ConvenienceDefinition('notification_service','service','Central transient feedback service.','Business actions need consistent success/warning/error messages.'),
        ConvenienceDefinition('preference_service','service','Load/update typed user preferences.','Application code needs persistence without direct storage manipulation.'),
        ConvenienceDefinition('keyboard_shortcuts','service','Canonical shortcut registry.','Pages need discoverable keyboard-first actions.'),

        ConvenienceDefinition('workspace_preferences','service','Persist complete analytical workspace state.','Users should resume tabs, split positions and filter context.'),
        ConvenienceDefinition('command_registry','service','Searchable keyboard-first application commands.','Apps have several discoverable actions/navigation targets.'),
        ConvenienceDefinition('application_services','service','Canonical bundle of standard application services.','Generated apps need the normal framework services without repetitive setup.'),
        ConvenienceDefinition('error_service','service','Safe user-facing error IDs with structured logging hook.','Technical errors must not become raw user UI.'),
    )
}


def get_convenience(key: str) -> ConvenienceDefinition:
    try: return CONVENIENCE_REGISTRY[key]
    except KeyError as exc: raise KeyError(f'Unknown convenience primitive: {key}') from exc

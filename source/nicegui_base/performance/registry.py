from dataclasses import dataclass
@dataclass(frozen=True,slots=True)
class PerformanceDefinition:key:str; purpose:str; use_when:str; avoid_when:str
PERFORMANCE_REGISTRY={x.key:x for x in (
PerformanceDefinition('ttl_cache','Bounded local TTL/LRU cache.','Deterministic repeated local result is expensive.','Data must always be read fresh.'),
PerformanceDefinition('single_flight_cache','Coalesce identical concurrent async loads.','Multiple components can request the same backend data.','Requests have distinct authorization/side effects.'),
PerformanceDefinition('analytical_data_controller','Debounce/cancel/cache analytical loads.','Filters/search can rapidly supersede earlier requests.','A simple one-shot action is enough.'),
PerformanceDefinition('lazy_resource','Load expensive content only on first use.','Tabs/drawers/panels may never be opened.','Content is tiny and always visible.'),
PerformanceDefinition('concurrency_gate','Bound async fan-out.','Many independent I/O operations could overload backend.','Only one or two requests occur.'),
PerformanceDefinition('retry_policy','Controlled bounded retry.','Idempotent reads can fail transiently.','Mutations are non-idempotent or failure is deterministic.'),
PerformanceDefinition('run_blocking','Move blocking work off async loop.','Existing synchronous library must run from async UI path.','Native async API exists.'),
PerformanceDefinition('performance_monitor','Bounded latency telemetry and budgets.','Hot path should be measured.','No decision will be made from the measurement.'),
PerformanceDefinition('table_query_engine','Indexed/cached repeated local table queries.','Same in-memory dataset is searched/filter/paged repeatedly.','Rows change every interaction.'),
PerformanceDefinition('cached_framework_css','Build deterministic framework CSS once per process.','Theme adapter initializes repeatedly across pages/tests.','Never disable this default.'),
)}
def get_performance(key):
    try:return PERFORMANCE_REGISTRY[key]
    except KeyError as exc:raise KeyError(f'Unknown performance primitive: {key}') from exc

# Company Runtime Quick Start

## Required secrets

Set these through the company secret/environment mechanism; never commit values:

- `NICEGUI_BASE_STORAGE_SECRET` — signs NiceGUI session storage cookies.
- `NICEGUI_BASE_AUTH_ASSERTION_SECRET` — recommended when a reverse proxy asserts identity headers and Uvicorn forwarded-header handling rewrites the apparent client IP.

## Single-instance production

Use one NiceGUI process / one Uvicorn worker. Configure the trusted reverse proxy and root path through `RuntimeConfig`.

## Multiple instances

When horizontal scaling is necessary:

1. Keep each NiceGUI process at one Uvicorn worker.
2. Put multiple instances behind a load balancer with session affinity/sticky sessions.
3. Configure `NICEGUI_REDIS_URL` (or an equivalent external persistence strategy) for shared persistent storage.
4. Set `NICEGUI_BASE_SESSION_AFFINITY_CONFIRMED=true` only after the load balancer behavior is verified.
5. Re-run `RuntimeDoctor` and the certification application.

## Protected page pattern

```python
@ui.page('/analysis')
def analysis(request: Request):
    principal = runtime.require_http(request, ANALYSIS_POLICY)
    # Only after this line should protected data be queried or rendered.
```

UI hiding is not a substitute for the access guard.

# Production Completion Guide — v1.2

This guide defines the v1.2 Production Gold Candidate additions that close runtime gaps identified in the v1.1 source audit.

## Accessibility

- Preserve framework-managed labels, descriptions, validation state and ARIA relationships.
- Do not remove the skip-to-main-content path or visible keyboard focus.
- Icon-only controls require semantic accessible labels.
- State must never be communicated by color alone.

## Runtime-complete table controls

Use the NiceGUI Base `DataTable` family and its rendered toolbar, density, column, selection, action, server-query and editing behaviors. Do not recreate these using raw AG Grid options in application modules.

Use `ServerDataTable` when the source dataset must remain server-side. Its query lifecycle owns latest-request-wins semantics so an older slow response does not overwrite a newer request.

## Dialogs, state views and dirty forms

- `ConfirmDialog` / `DangerConfirmDialog` own their action footer and confirmation lifecycle.
- High-risk destructive flows may require typed confirmation.
- `DirtyStateGuard` protects browser unload and internal navigation.
- `AsyncContent` owns loading, ready, refreshing, empty and error presentation.
- State views own standard recovery actions such as Retry, Clear filters and Go back.

## Registered content system

Use `CONTENT_REGISTRY` before creating custom presentation components. It includes:

- metrics and metric strips;
- key/value, description and property presentation;
- entity headers and hierarchy/tree presentation;
- Markdown, code, JSON, log and image viewers;
- search results;
- steppers and progress steps;
- comparison/difference surfaces;
- command palette;
- background-task status;
- notification history and activity feed.

## Durable work

Use `DurableJobAdapter` for jobs that must survive process restart or execute through a company scheduler/queue. `InProcessJobAdapter` is a development/short-task reference and does **not** provide restart durability.

## Content safety

Markdown remains sanitized by default. Remote image/visual resources remain disabled by default. Use packaged `Icons.*`, illustrations and approved local resources.

## Runtime certification boundary

Offline certification verifies the package, registries, CSS, static validator, visual assets, wheel/install behavior, SBOM and provenance. Production Gold still requires final live certification in the company environment for:

- NiceGUI 3.15.0 browser rendering;
- Edge and Chrome accessibility/visual regression;
- reverse-proxy base path and WebSocket upgrade behavior;
- company authentication/SSO adapter behavior.

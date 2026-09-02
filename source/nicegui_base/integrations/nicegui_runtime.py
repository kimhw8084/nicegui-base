from __future__ import annotations

from typing import Any, Callable, Mapping

from nicegui_base.diagnostics import CorrelationIdMiddleware, HealthRegistry, RuntimeDoctor
from nicegui_base.runtime import RuntimeConfig, runtime_fingerprint
from nicegui_base.security import (
    AccessPolicy, AuthenticationAdapter, AuthorizationModel, IdentityMiddleware,
    Principal, SecurityHeaders, SecurityHeadersMiddleware,
)


def _nicegui():
    try:
        from nicegui import app, ui
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError('NiceGUI is required for NiceGUIRuntimeAdapter.') from exc
    return app, ui


class NiceGUIRuntimeAdapter:
    """Company runtime integration for NiceGUI 3.15.

    The adapter keeps production configuration in typed framework objects and
    deliberately avoids coupling authentication to NiceGUI user storage.
    Identity should be established at the HTTP/WebSocket boundary before a
    protected page creates a client capability.
    """

    def __init__(
        self,
        config: RuntimeConfig,
        *,
        health: HealthRegistry | None = None,
        auth_adapter: AuthenticationAdapter | None = None,
        authorization: AuthorizationModel | None = None,
        security_headers: SecurityHeaders | None = None,
    ):
        self.config = config
        self.health = health or HealthRegistry()
        self.auth_adapter = auth_adapter
        self.authorization = authorization or AuthorizationModel()
        self.security_headers = security_headers or self._default_headers()
        self._installed = False
        self._page_routes: set[str] = set()

    def _default_headers(self) -> SecurityHeaders:
        if self.config.environment.value == 'prod':
            return SecurityHeaders(strict_transport_security='max-age=31536000; includeSubDomains')
        return SecurityHeaders()

    def run_kwargs(self, environ=None) -> dict[str, object]:
        return self.config.nicegui_run_kwargs(environ)

    def install_middleware(self, app: Any | None = None) -> None:
        if self._installed:
            return
        ng_app, _ = _nicegui() if app is None else (app, None)
        ng_app.add_middleware(SecurityHeadersMiddleware, headers=self.security_headers)
        ng_app.add_middleware(CorrelationIdMiddleware, trust_incoming=self.config.proxy.enabled)
        if self.auth_adapter is not None:
            ng_app.add_middleware(IdentityMiddleware, adapter=self.auth_adapter)
        self._installed = True

    def install_operational_endpoints(self, app: Any | None = None, *, diagnostics_policy: AccessPolicy | None = None) -> None:
        ng_app, _ = _nicegui() if app is None else (app, None)
        try:
            from fastapi import Request
            from fastapi.responses import JSONResponse
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError('FastAPI is required by NiceGUI runtime endpoints.') from exc

        health_path = self.config.health_path
        readiness_path = self.config.readiness_path

        @ng_app.get(health_path, include_in_schema=False)
        async def nicegui_base_health():
            report = await self.health.run()
            return JSONResponse({'state': report.state.value}, status_code=200)

        @ng_app.get(readiness_path, include_in_schema=False)
        async def nicegui_base_readiness():
            report = await self.health.run()
            payload = {'state': report.state.value, 'ready': report.ready}
            return JSONResponse(payload, status_code=200 if report.ready else 503)

        if self.config.diagnostics_enabled:
            if self.auth_adapter is None or diagnostics_policy is None:
                raise ValueError('diagnostics require authentication and an explicit access policy')

            @ng_app.get(self.config.diagnostics_path, include_in_schema=False)
            async def nicegui_base_diagnostics(request: Request):
                principal = self.principal_from_request(request)
                decision = self.authorization.check(principal, diagnostics_policy)
                if not decision.allowed:
                    return JSONResponse({'detail': 'forbidden'}, status_code=403)
                doctor = RuntimeDoctor(self.config).run()
                return JSONResponse({'runtime': runtime_fingerprint(), 'doctor': doctor.to_dict()}, status_code=200 if doctor.ok else 503)

    @staticmethod
    def principal_from_request(request: Any) -> Principal:
        principal = getattr(getattr(request, 'state', None), 'nicegui_base_principal', None)
        return principal if isinstance(principal, Principal) else Principal.anonymous()

    def require(self, request: Any, policy: AccessPolicy) -> Principal:
        return self.authorization.require(self.principal_from_request(request), policy)

    def require_http(self, request: Any, policy: AccessPolicy) -> Principal:
        principal = self.principal_from_request(request)
        decision = self.authorization.check(principal, policy)
        if not decision.allowed:
            try:
                from fastapi import HTTPException
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError('FastAPI is required for HTTP access guards.') from exc
            raise HTTPException(status_code=401 if not principal.authenticated else 403, detail='access denied')
        return principal

    def install_pages(self, pages: Mapping[str, Callable[..., Any]] | None) -> tuple[str, ...]:
        if not pages:
            return ()
        _, ui = _nicegui()
        reserved = {self.config.health_path, self.config.readiness_path}
        if self.config.diagnostics_enabled:
            reserved.add(self.config.diagnostics_path)
        registered: list[str] = []
        for raw_route, handler in pages.items():
            route = str(raw_route).strip()
            if route == '/':
                raise ValueError("secondary page mapping must not redefine the root route")
            if not route.startswith('/') or '?' in route or '#' in route or '://' in route:
                raise ValueError(f'invalid application page route: {route!r}')
            if route in reserved:
                raise ValueError(f'application page route conflicts with runtime endpoint: {route!r}')
            if not callable(handler):
                raise TypeError(f'application page handler for {route!r} must be callable')
            if route in self._page_routes:
                continue
            ui.page(route)(handler)
            self._page_routes.add(route)
            registered.append(route)
        return tuple(registered)

    def run(self, *, root: Callable[..., Any] | None = None, pages: Mapping[str, Callable[..., Any]] | None = None, environ=None) -> None:
        app, ui = _nicegui()
        self.install_middleware(app)
        self.install_operational_endpoints(app)
        self.install_pages(pages)
        kwargs = self.run_kwargs(environ)
        if root is None:
            ui.run(**kwargs)
        else:
            ui.run(root=root, **kwargs)

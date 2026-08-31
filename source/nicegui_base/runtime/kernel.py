from __future__ import annotations

import inspect
import time
from collections import deque
from collections.abc import Awaitable, Callable, Iterator, Mapping
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, TypeVar, cast

from nicegui_base.performance import LifecycleScope
from nicegui_base.services import ApplicationServices
from nicegui_base.data_engine import DataEngine, DataSession, DataSessionSnapshot
from nicegui_base.workspace import WorkspaceController, WorkspaceInteractionSnapshot, WorkspaceLayoutEngine, WorkspaceLayoutSnapshot
from nicegui_base.analysis import AnalysisContext, AnalysisContextSnapshot, AnalysisCoordinator, SelectionBus, SelectionSnapshot
from nicegui_base.extensions import ExtensionRegistry

T = TypeVar('T')
_MISSING = object()


class StateNamespace(str, Enum):
    APPLICATION = 'application'
    SESSION = 'session'
    WORKSPACE = 'workspace'
    VIEW = 'view'


Validator = Callable[[Any], bool]
StateWatcher = Callable[['StateMutation'], Any]


@dataclass(frozen=True, slots=True)
class StateKey(Generic[T]):
    """Typed runtime state address with optional default and validation."""

    name: str
    namespace: StateNamespace = StateNamespace.WORKSPACE
    default: T | object = field(default=_MISSING, compare=False, hash=False)
    validator: Validator | None = field(default=None, compare=False, hash=False, repr=False)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError('StateKey name must not be empty')

    def validate(self, value: Any) -> None:
        if self.validator is not None and not self.validator(value):
            raise ValueError(f'invalid value for state key {self.namespace.value}.{self.name}')


@dataclass(frozen=True, slots=True)
class StateMutation:
    namespace: StateNamespace
    key: str
    old: Any
    new: Any
    revision: int
    source: str
    old_present: bool = True
    new_present: bool = True


@dataclass(frozen=True, slots=True)
class StateSnapshot:
    revision: int
    values: Mapping[str, Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    sequence: int
    kind: str
    occurred_at: str
    workspace_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RuntimeDiagnostics:
    active_workspaces: int
    application_state_revision: int
    workspace_state_revisions: Mapping[str, int]
    active_tasks: int
    registered_cleanups: int
    registered_datasets: int
    active_data_sessions: int
    workspace_panels: int
    registered_extensions: int
    event_count: int
    latest_event_sequence: int


@dataclass(frozen=True, slots=True)
class WorkspaceSnapshot:
    workspace_id: str
    state: StateSnapshot
    layout: WorkspaceLayoutSnapshot
    data_sessions: Mapping[str, tuple[str, DataSessionSnapshot]]
    analysis: AnalysisContextSnapshot | None = None
    selections: SelectionSnapshot | None = None
    interactions: WorkspaceInteractionSnapshot | None = None


@dataclass(frozen=True, slots=True)
class ApplicationSnapshot:
    state: StateSnapshot
    workspaces: tuple[WorkspaceSnapshot, ...]


class RuntimeState:
    """Atomic, revisioned and framework-neutral state for the v3 runtime.

    Values are modified immediately inside a transaction so dependent code can read
    its own writes, but watchers and history are emitted only after the outermost
    transaction commits. If the transaction raises, every touched key is restored to
    its exact pre-transaction state and no revision/history entry is produced.
    """

    def __init__(self, initial: Mapping[StateNamespace | str, Mapping[str, Any]] | None = None, *, history_limit: int = 500):
        if history_limit < 1:
            raise ValueError('history_limit must be >= 1')
        self._values: dict[StateNamespace, dict[str, Any]] = {namespace: {} for namespace in StateNamespace}
        if initial:
            for namespace, values in initial.items():
                resolved = namespace if isinstance(namespace, StateNamespace) else StateNamespace(namespace)
                self._values[resolved].update(deepcopy(dict(values)))
        self._revision = 0
        self._history: deque[StateMutation] = deque(maxlen=history_limit)
        self._watchers: list[StateWatcher] = []
        self._key_watchers: dict[tuple[StateNamespace, str], list[StateWatcher]] = {}
        self._transaction_depth = 0
        self._transaction_originals: dict[tuple[StateNamespace, str], Any] = {}
        self._transaction_sources: dict[tuple[StateNamespace, str], str] = {}
        self._transaction_default_source = 'runtime'
        self._undo_stack: deque[tuple[StateMutation, ...]] = deque(maxlen=history_limit)
        self._redo_stack: deque[tuple[StateMutation, ...]] = deque(maxlen=history_limit)
        self._replaying_history = False

    @property
    def revision(self) -> int:
        return self._revision

    @property
    def history(self) -> tuple[StateMutation, ...]:
        return tuple(self._history)

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def contains(self, key: StateKey[Any]) -> bool:
        return key.name in self._values[key.namespace]

    def get(self, key: StateKey[T]) -> T:
        values = self._values[key.namespace]
        if key.name in values:
            return cast(T, deepcopy(values[key.name]))
        if key.default is not _MISSING:
            return cast(T, deepcopy(key.default))
        raise KeyError(f'{key.namespace.value}.{key.name}')

    def get_optional(self, key: StateKey[T], default: T | None = None) -> T | None:
        try:
            return self.get(key)
        except KeyError:
            return default

    def set(self, key: StateKey[T], value: T, *, source: str | None = None) -> None:
        key.validate(value)
        with self._auto_transaction(source=source):
            self._write(key.namespace, key.name, deepcopy(value), source=source)

    def delete(self, key: StateKey[Any], *, source: str | None = None) -> bool:
        if key.name not in self._values[key.namespace]:
            return False
        with self._auto_transaction(source=source):
            self._write(key.namespace, key.name, _MISSING, source=source)
        return True

    def set_many(self, values: Mapping[StateKey[Any], Any], *, source: str = 'runtime') -> None:
        with self.transaction(source=source):
            for key, value in values.items():
                key.validate(value)
                self._write(key.namespace, key.name, deepcopy(value), source=source)

    def watch(self, callback: StateWatcher) -> Callable[[], None]:
        self._watchers.append(callback)
        def unsubscribe() -> None:
            if callback in self._watchers:
                self._watchers.remove(callback)
        return unsubscribe

    def watch_key(self, key: StateKey[Any], callback: StateWatcher) -> Callable[[], None]:
        address = (key.namespace, key.name)
        self._key_watchers.setdefault(address, []).append(callback)
        def unsubscribe() -> None:
            watchers = self._key_watchers.get(address, [])
            if callback in watchers:
                watchers.remove(callback)
            if not watchers:
                self._key_watchers.pop(address, None)
        return unsubscribe

    @contextmanager
    def transaction(self, *, source: str = 'runtime') -> Iterator['RuntimeState']:
        outermost = self._transaction_depth == 0
        if outermost:
            self._transaction_originals = {}
            self._transaction_sources = {}
            self._transaction_default_source = source
        self._transaction_depth += 1
        try:
            yield self
        except BaseException:
            self._transaction_depth -= 1
            if outermost:
                self._rollback_transaction()
            raise
        else:
            self._transaction_depth -= 1
            if outermost:
                self._commit_transaction()

    @contextmanager
    def _auto_transaction(self, *, source: str | None) -> Iterator[None]:
        if self._transaction_depth:
            yield
            return
        with self.transaction(source=source or 'runtime'):
            yield

    def _write(self, namespace: StateNamespace, name: str, value: Any, *, source: str | None) -> None:
        address = (namespace, name)
        values = self._values[namespace]
        if address not in self._transaction_originals:
            self._transaction_originals[address] = deepcopy(values[name]) if name in values else _MISSING
        self._transaction_sources[address] = source or self._transaction_default_source
        if value is _MISSING:
            values.pop(name, None)
        else:
            values[name] = value

    def _rollback_transaction(self) -> None:
        for (namespace, name), old in reversed(tuple(self._transaction_originals.items())):
            if old is _MISSING:
                self._values[namespace].pop(name, None)
            else:
                self._values[namespace][name] = old
        self._transaction_originals = {}
        self._transaction_sources = {}

    def _commit_transaction(self) -> None:
        pending: list[tuple[StateNamespace, str, Any, Any, str, bool, bool]] = []
        for (namespace, name), old in self._transaction_originals.items():
            values = self._values[namespace]
            new = deepcopy(values[name]) if name in values else _MISSING
            old_present = old is not _MISSING; new_present = new is not _MISSING
            old_value = None if not old_present else deepcopy(old)
            new_value = None if not new_present else deepcopy(new)
            if not old_present and not new_present:
                continue
            if old_present and new_present and old == new:
                continue
            pending.append((namespace, name, old_value, new_value, self._transaction_sources.get((namespace, name), self._transaction_default_source), old_present, new_present))
        self._transaction_originals = {}
        self._transaction_sources = {}
        if not pending:
            return
        self._revision += 1
        mutations = tuple(StateMutation(namespace, name, old, new, self._revision, source, old_present, new_present) for namespace, name, old, new, source, old_present, new_present in pending)
        self._history.extend(mutations)
        if not self._replaying_history:
            self._undo_stack.append(tuple(deepcopy(mutations)))
            self._redo_stack.clear()
        for mutation in mutations:
            self._notify(mutation)

    def undo(self) -> bool:
        if self._transaction_depth:
            raise RuntimeError('cannot undo during an active state transaction')
        if not self._undo_stack:
            return False
        batch = self._undo_stack.pop()
        self._replaying_history = True
        try:
            with self.transaction(source='undo'):
                for mutation in reversed(batch):
                    value = deepcopy(mutation.old) if mutation.old_present else _MISSING
                    self._write(mutation.namespace, mutation.key, value, source='undo')
        except BaseException:
            self._undo_stack.append(batch)
            raise
        finally:
            self._replaying_history = False
        self._redo_stack.append(batch)
        return True

    def redo(self) -> bool:
        if self._transaction_depth:
            raise RuntimeError('cannot redo during an active state transaction')
        if not self._redo_stack:
            return False
        batch = self._redo_stack.pop()
        self._replaying_history = True
        try:
            with self.transaction(source='redo'):
                for mutation in batch:
                    value = deepcopy(mutation.new) if mutation.new_present else _MISSING
                    self._write(mutation.namespace, mutation.key, value, source='redo')
        except BaseException:
            self._redo_stack.append(batch)
            raise
        finally:
            self._replaying_history = False
        self._undo_stack.append(batch)
        return True

    def _notify(self, mutation: StateMutation) -> None:
        for watcher in tuple(self._watchers):
            watcher(mutation)
        for watcher in tuple(self._key_watchers.get((mutation.namespace, mutation.key), ())):
            watcher(mutation)

    def snapshot(self) -> StateSnapshot:
        return StateSnapshot(
            revision=self._revision,
            values={namespace.value: deepcopy(values) for namespace, values in self._values.items()},
        )

    def restore(self, snapshot: StateSnapshot, *, source: str = 'restore') -> None:
        desired = {StateNamespace(namespace): dict(values) for namespace, values in snapshot.values.items()}
        with self.transaction(source=source):
            for namespace in StateNamespace:
                current_keys = set(self._values[namespace])
                desired_values = desired.get(namespace, {})
                for name in current_keys - set(desired_values):
                    self._write(namespace, name, _MISSING, source=source)
                for name, value in desired_values.items():
                    self._write(namespace, name, deepcopy(value), source=source)


class WorkspaceRuntime:
    """One v3 workspace: isolated state plus deterministic resource ownership."""

    def __init__(self, workspace_id: str, *, data_engine: DataEngine | None = None, initial_state: Mapping[StateNamespace | str, Mapping[str, Any]] | None = None):
        if not workspace_id.strip():
            raise ValueError('workspace_id must not be empty')
        self.workspace_id = workspace_id
        self.state = RuntimeState(initial_state)
        self.layout = WorkspaceLayoutEngine()
        self.workspace = WorkspaceController(self.layout)
        self.analysis = AnalysisContext()
        self.selections = SelectionBus()
        self.analysis_coordinator = AnalysisCoordinator(self.analysis, self.selections)
        self.lifecycle = LifecycleScope()
        self.data_engine=data_engine
        self._data_sessions: dict[str,DataSession]={}
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed


    @property
    def data_sessions(self) -> Mapping[str,DataSession]:
        return dict(self._data_sessions)

    def data_session(self, session_id: str = 'default') -> DataSession:
        """Return an owned data session by id with a clear lifecycle error."""
        if self._closed:
            raise RuntimeError('WorkspaceRuntime is closed')
        try:
            return self._data_sessions[session_id]
        except KeyError as exc:
            raise KeyError(f'unknown workspace data session: {session_id}') from exc

    def data_source(self, key: str):
        """Resolve a provider-neutral Wave 59 data source from this workspace."""
        if self._closed:
            raise RuntimeError('WorkspaceRuntime is closed')
        if self.data_engine is None:
            raise RuntimeError('WorkspaceRuntime has no DataEngine')
        return self.data_engine.get_source(key)

    def open_data_session(self, dataset_key: str, *, session_id: str = 'default') -> DataSession:
        if self._closed: raise RuntimeError('WorkspaceRuntime is closed')
        if self.data_engine is None: raise RuntimeError('WorkspaceRuntime has no DataEngine')
        if session_id in self._data_sessions: raise ValueError(f'data session already open: {session_id}')
        session=self.data_engine.session(dataset_key); self._data_sessions[session_id]=session
        self.lifecycle.register(session.close,key=('data-session',session_id))
        return session

    def close_data_session(self, session_id: str) -> bool:
        session=self._data_sessions.pop(session_id,None)
        if session is None:return False
        self.lifecycle.unregister(('data-session',session_id)); session.close(); return True

    def snapshot(self) -> WorkspaceSnapshot:
        return WorkspaceSnapshot(
            workspace_id=self.workspace_id,
            state=self.state.snapshot(),
            layout=self.layout.snapshot(),
            data_sessions={
                session_id: (session.dataset.key, session.snapshot())
                for session_id, session in self._data_sessions.items()
            },
            analysis=self.analysis.snapshot(),
            selections=self.selections.snapshot(),
            interactions=self.workspace.snapshot(),
        )

    def restore(self, snapshot: WorkspaceSnapshot) -> None:
        if self._closed:
            raise RuntimeError('WorkspaceRuntime is closed')
        if snapshot.workspace_id != self.workspace_id:
            raise ValueError(f'workspace snapshot {snapshot.workspace_id!r} does not match {self.workspace_id!r}')
        self.state.restore(snapshot.state, source='workspace.restore')
        self.layout.restore(snapshot.layout)
        if snapshot.interactions is not None:
            self.workspace.restore(snapshot.interactions, emit=False)
        if snapshot.analysis is not None:
            self.analysis.restore(snapshot.analysis)
        if snapshot.selections is not None:
            self.selections.restore(snapshot.selections, emit=False)
        for session_id in tuple(self._data_sessions):
            self.close_data_session(session_id)
        for session_id, (dataset_key, session_snapshot) in snapshot.data_sessions.items():
            session = self.open_data_session(dataset_key, session_id=session_id)
            session.restore(session_snapshot)

    def register_cleanup(self, cleanup: Callable[[], Any | Awaitable[Any]], *, key: object | None = None):
        return self.lifecycle.register(cleanup, key=key)

    def create_task(self, awaitable: Awaitable[T], *, name: str | None = None):
        return self.lifecycle.create_task(awaitable, name=name)

    async def aclose(self) -> tuple[BaseException, ...]:
        if self._closed:
            return ()
        self._closed = True
        self.analysis_coordinator.close()
        self.analysis.close()
        self.selections.close()
        self.workspace.close()
        return await self.lifecycle.aclose()


class ApplicationRuntime:
    """NiceGUI Base v3 ownership kernel for state, workspaces, commands and lifecycle."""

    def __init__(self, *, services: ApplicationServices | None = None, event_limit: int = 1000):
        if event_limit < 1:
            raise ValueError('event_limit must be >= 1')
        self.services = services or ApplicationServices()
        self.state = RuntimeState()
        self.data = DataEngine()
        self.extensions = ExtensionRegistry()
        self._workspaces: dict[str, WorkspaceRuntime] = {}
        self._events: deque[RuntimeEvent] = deque(maxlen=event_limit)
        self._event_sequence = 0
        self._closed = False
        self._record_event('runtime.opened')

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def workspaces(self) -> Mapping[str, WorkspaceRuntime]:
        return dict(self._workspaces)

    @property
    def data_sources(self):
        """Application-level registry for provider-neutral analytical sources."""
        return self.data.sources

    @property
    def events(self) -> tuple[RuntimeEvent, ...]:
        return tuple(self._events)

    def _record_event(self, kind: str, *, workspace_id: str | None = None, **metadata: Any) -> RuntimeEvent:
        self._event_sequence += 1
        event = RuntimeEvent(
            sequence=self._event_sequence,
            kind=kind,
            occurred_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
            workspace_id=workspace_id,
            metadata=deepcopy(metadata),
        )
        self._events.append(event)
        return event

    def open_workspace(self, workspace_id: str, *, initial_state: Mapping[StateNamespace | str, Mapping[str, Any]] | None = None) -> WorkspaceRuntime:
        if self._closed:
            raise RuntimeError('ApplicationRuntime is closed')
        if workspace_id in self._workspaces:
            raise ValueError(f'workspace already open: {workspace_id}')
        workspace = WorkspaceRuntime(workspace_id, data_engine=self.data, initial_state=initial_state)
        self._workspaces[workspace_id] = workspace
        self.services.register_cleanup(workspace.aclose, key=('workspace', workspace_id))
        self._record_event('workspace.opened', workspace_id=workspace_id)
        return workspace

    async def close_workspace(self, workspace_id: str) -> tuple[BaseException, ...]:
        workspace = self._workspaces.pop(workspace_id, None)
        if workspace is None:
            return ()
        self.services.lifecycle.unregister(('workspace', workspace_id))
        failures = await workspace.aclose()
        self._record_event('workspace.closed', workspace_id=workspace_id, cleanup_failures=len(failures))
        return failures

    async def execute_command(self, key: str, *, workspace_id: str | None = None) -> Any:
        if self._closed:
            raise RuntimeError('ApplicationRuntime is closed')
        started = time.perf_counter()
        self._record_event('command.started', workspace_id=workspace_id, command=key)
        try:
            value = self.services.commands.execute(key)
            result = await value if inspect.isawaitable(value) else value
        except BaseException as exc:
            duration_ms = (time.perf_counter() - started) * 1000
            self.services.performance.record('runtime.command', duration_ms, command=key, status='error', workspace_id=workspace_id)
            self._record_event('command.failed', workspace_id=workspace_id, command=key, error_type=type(exc).__name__, duration_ms=duration_ms)
            raise
        duration_ms = (time.perf_counter() - started) * 1000
        self.services.performance.record('runtime.command', duration_ms, command=key, status='success', workspace_id=workspace_id)
        self._record_event('command.completed', workspace_id=workspace_id, command=key, duration_ms=duration_ms)
        return result

    def snapshot(self) -> ApplicationSnapshot:
        return ApplicationSnapshot(
            state=self.state.snapshot(),
            workspaces=tuple(workspace.snapshot() for workspace in self._workspaces.values()),
        )

    async def restore(self, snapshot: ApplicationSnapshot) -> None:
        if self._closed:
            raise RuntimeError('ApplicationRuntime is closed')
        desired_ids = {item.workspace_id for item in snapshot.workspaces}
        for workspace_id in tuple(self._workspaces):
            if workspace_id not in desired_ids:
                await self.close_workspace(workspace_id)
        self.state.restore(snapshot.state, source='application.restore')
        for workspace_snapshot in snapshot.workspaces:
            workspace = self._workspaces.get(workspace_snapshot.workspace_id)
            if workspace is None:
                workspace = self.open_workspace(workspace_snapshot.workspace_id)
            workspace.restore(workspace_snapshot)
        self._record_event('runtime.restored', workspaces=len(snapshot.workspaces))

    def diagnostics(self) -> RuntimeDiagnostics:
        workspace_revisions = {key: workspace.state.revision for key, workspace in self._workspaces.items()}
        active_tasks = self.services.lifecycle.active_task_count + sum(workspace.lifecycle.active_task_count for workspace in self._workspaces.values())
        cleanups = self.services.lifecycle.cleanup_count + sum(workspace.lifecycle.cleanup_count for workspace in self._workspaces.values())
        return RuntimeDiagnostics(
            active_workspaces=len(self._workspaces),
            application_state_revision=self.state.revision,
            workspace_state_revisions=workspace_revisions,
            active_tasks=active_tasks,
            registered_cleanups=cleanups,
            registered_datasets=len(self.data.datasets),
            active_data_sessions=sum(len(workspace.data_sessions) for workspace in self._workspaces.values()),
            workspace_panels=sum(len(workspace.layout.panels) for workspace in self._workspaces.values()),
            registered_extensions=len(self.extensions.list()),
            event_count=len(self._events),
            latest_event_sequence=self._event_sequence,
        )

    async def aclose(self) -> tuple[BaseException, ...]:
        if self._closed:
            return ()
        self._closed = True
        failures: list[BaseException] = []
        for workspace_id in tuple(reversed(tuple(self._workspaces))):
            failures.extend(await self.close_workspace(workspace_id))
        failures.extend(await self.data.aclose())
        failures.extend(await self.services.aclose())
        self._record_event('runtime.closed', cleanup_failures=len(failures))
        return tuple(failures)

    async def __aenter__(self) -> 'ApplicationRuntime':
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        await self.aclose()
        return False

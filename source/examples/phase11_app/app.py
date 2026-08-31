from nicegui_base import NiceGUIRuntimeAdapter, RuntimeConfig


def runtime() -> NiceGUIRuntimeAdapter:
    return NiceGUIRuntimeAdapter(RuntimeConfig('Equipment Health'))

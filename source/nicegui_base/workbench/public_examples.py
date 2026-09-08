from __future__ import annotations

"""Production-facing examples for Reference Explorer Code tabs.

Every component example uses the stable public ``nicegui_base`` API. The
Reference Explorer harness remains a separate, explicitly secondary artifact.
"""

from typing import Any

_COMPONENT_EXAMPLES: dict[str, str] = {
    "button_group": """from nicegui_base import Button, ButtonGroup, ButtonIntent

with ButtonGroup():
    Button("Run", intent=ButtonIntent.PRIMARY)
    Button("Pause")
    Button("Reset", intent=ButtonIntent.TERTIARY)
""",
    "split_button": """from nicegui_base import SplitButton

SplitButton(
    "Export CSV",
    {"Export JSON": lambda: print("json"), "Export PNG": lambda: print("png")},
    on_click=lambda: print("csv"),
)
""",
    "divider": """from nicegui_base import Divider

Divider()
""",
    "collapsible_panel": """from nicegui_base import CollapsiblePanel, TextInput

with CollapsiblePanel("Advanced settings", open=True):
    TextInput("Owner", value="Engineer")
""",
    "accordion": """from nicegui_base import Accordion, TextInput

with Accordion() as accordion:
    with accordion.item("Sampling", open=True):
        TextInput("Sampling plan", value="Every 10 wafers")
""",
    "chip": """from nicegui_base import Chip, Icons

Chip("Lot A12", selected=True, icon=Icons.LOT)
""",
    "count_badge": """from nicegui_base import CountBadge

CountBadge(24)
""",
    "severity_indicator": """from nicegui_base import SeverityIndicator, StatusIntent

SeverityIndicator("High severity", intent=StatusIntent.DANGER)
""",
    "freshness_indicator": """from nicegui_base import FreshnessIndicator

FreshnessIndicator("Updated 2 min ago", stale=False)
""",
    "data_quality_badge": """from nicegui_base import DataQuality, DataQualityBadge

DataQualityBadge(DataQuality.COMPLETE)
""",
    "button": """from nicegui_base import Button, ButtonIntent, Icons

Button("Run analysis", intent=ButtonIntent.PRIMARY, icon=Icons.PLAY)
""",
    "action_button": """from nicegui_base import ActionButton, Icons

ActionButton("Save changes", icon=Icons.SAVE, success_message="Saved")
""",
    "icon_button": """from nicegui_base import IconButton, Icons

IconButton(Icons.REFRESH, label="Refresh data")
""",
    "surface": """from nicegui_base import Card, Panel, Well

with Panel():
    pass  # compose governed NiceGUI Base content here
with Card():
    pass
with Well():
    pass
""",
    "badge": """from nicegui_base import Icons, StatusBadge, StatusIntent

StatusBadge("Healthy", intent=StatusIntent.SUCCESS, icon=Icons.CHECK)
StatusBadge("Warning", intent=StatusIntent.WARNING, icon=Icons.WARNING)
""",
    "text_input": """from nicegui_base import TextInput

TextInput("Lot ID", value="LOT-2409", clearable=True)
""",
    "number_input": """from nicegui_base import NumberInput

NumberInput("Upper limit", value=42.5, minimum=0, maximum=100, step=0.1, unit="nm")
""",
    "textarea": """from nicegui_base import TextArea

TextArea("Engineering note", value="Investigate chamber drift.", rows=3)
""",
    "search_input": """from nicegui_base import SearchInput

SearchInput("Search lots", value="LOT", debounce_ms=250)
""",
    "select": """from nicegui_base import Select

Select("Process area", {"etch": "Etch", "deposition": "Deposition", "metrology": "Metrology"},
       value="metrology", searchable=True)
""",
    "multi_select": """from nicegui_base import MultiSelect

MultiSelect("Process areas", {"etch": "Etch", "deposition": "Deposition", "metrology": "Metrology"},
            value=("etch", "metrology"))
""",
    "autocomplete": """from nicegui_base import Autocomplete

Autocomplete("Tool", {"etch": "Etch", "deposition": "Deposition", "metrology": "Metrology"},
             value="metrology")
""",
    "combobox": """from nicegui_base import Combobox

Combobox("Tag", {"etch": "Etch", "deposition": "Deposition", "metrology": "Metrology"},
         value="etch")
""",
    "checkbox": """from nicegui_base import Checkbox

Checkbox("Include rework lots", checked=True, description="Independent boolean choice")
""",
    "checkbox_group": """from nicegui_base import CheckboxGroup, SelectOption

CheckboxGroup(
    "Signals",
    (SelectOption("etch", "Etch"), SelectOption("deposition", "Deposition"),
     SelectOption("metrology", "Metrology")),
    selected=("etch", "metrology"),
)
""",
    "radio_group": """from nicegui_base import RadioGroup, SelectOption

RadioGroup(
    "Mode",
    (SelectOption("etch", "Etch"), SelectOption("deposition", "Deposition"),
     SelectOption("metrology", "Metrology")),
    selected="metrology",
)
""",
    "switch": """from nicegui_base import Switch

Switch("Auto refresh", checked=True, description="Applies immediately")
""",
    "slider": """from nicegui_base import Slider

Slider("Threshold", value=65, minimum=0, maximum=100, step=5, unit="%")
""",
    "range_slider": """from nicegui_base import RangeSlider

RangeSlider("Window", low=20, high=80, minimum=0, maximum=100, step=5, unit="%")
""",
    "date_picker": """from nicegui_base import DatePicker

DatePicker("Effective date", value="2026-09-05")
""",
    "date_range_picker": """from nicegui_base import DateRangePicker

DateRangePicker("Analysis period", start="2026-09-01", end="2026-09-05")
""",
    "time_picker": """from nicegui_base import TimePicker

TimePicker("Cutoff time", value="14:30")
""",
    "datetime_picker": """from nicegui_base import DateTimePicker

DateTimePicker("Scheduled run", value="2026-09-05T14:30")
""",
    "file_upload": """from nicegui_base import FileUpload

FileUpload(label="Upload process data", accept=(".csv", ".json"), max_file_size_mb=10)
""",
}

def production_example_code(entry: Any) -> str:
    metadata = getattr(entry, "metadata", {}) or {}
    component_key = str(metadata.get("component_key") or "")
    if component_key in _COMPONENT_EXAMPLES:
        return _COMPONENT_EXAMPLES[component_key].rstrip() + "\n"
    contract = getattr(entry, "reference_contract", None)
    code = str(getattr(contract, "recommended_code", "") or "")
    return code.rstrip() + "\n" if code.strip() else (
        "import nicegui_base\n\n"
        f"# Canonical authority: {getattr(entry, 'source_authority', 'NiceGUI Base')}\n"
    )

__all__ = ["production_example_code"]

"""Phase 3 semantic component example.

Run only in an environment with the pinned NiceGUI runtime installed.
Application code intentionally contains no raw visual CSS.
"""
from nicegui_base import (
    ActionButton, AppShell, ButtonIntent, Card, Checkbox, ContentWidth, DataQuality,
    DataQualityBadge, DateRangePicker, Grid, GridPreset, NumberInput, Page, PageHeader,
    SearchInput, Select, SelectOption, StatusBadge, StatusIntent, TextArea, TextInput,
)


def build_page() -> None:
    with AppShell('Equipment Intelligence', environment='prod'):
        with Page(ContentWidth.WIDE):
            PageHeader('Excursion investigation', 'Phase 3 semantic component composition')

            with Card():
                SearchInput(placeholder='Tool, chamber, lot, recipe...')
                Select('Area', (SelectOption('etch', 'ETCH'), SelectOption('cvd', 'CVD')))
                DateRangePicker('Analysis period')
                ActionButton('Run analysis', intent=ButtonIntent.PRIMARY)

            with Grid(GridPreset.HALVES):
                with Card():
                    TextInput('Investigation title', required=True)
                    NumberInput('Trigger threshold', value=2.5, minimum=0, maximum=10, unit='σ')
                    TextArea('Notes')
                with Card():
                    StatusBadge('Watch', intent=StatusIntent.WARNING)
                    DataQualityBadge(DataQuality.COMPLETE)
                    Checkbox('Include inactive chambers', checked=True)

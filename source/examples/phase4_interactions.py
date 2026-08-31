"""Semantic Phase 4 example; requires NiceGUI only when rendered."""

from nicegui_base import (
    ActiveFilter, AdvancedFilterDrawer, DetailDrawer, FeedbackIntent, FilterBar, FilterBarSpec,
    FilterDefinition, FilterKind, Form, FormActions, FormField, FormSection, TextInput,
    ValidationIssue, ValidationSummary, ValidationSummarySpec,
)

filters = FilterBarSpec(
    filters=(
        FilterDefinition('area', 'Area', FilterKind.SELECT),
        FilterDefinition('tool', 'Tool', FilterKind.SELECT),
        FilterDefinition('recipe', 'Recipe', FilterKind.SELECT, advanced=True),
    ),
    active=(ActiveFilter('area', 'Area', 'ETCH', 'ETCH'),),
)


def build_example() -> None:
    with FilterBar(filters):
        pass  # render approved filter controls here

    with DetailDrawer('ETCH-021 · Chamber B'):
        pass  # contextual entity details

    with AdvancedFilterDrawer('Advanced filters'):
        pass  # secondary/complex filter controls

    with Form('investigation', title='Create investigation'):
        with FormSection('Investigation details'):
            with FormField('title', 'Title', required=True):
                TextInput('Title', placeholder='e.g. ETCH-021 CD excursion')
        ValidationSummary(ValidationSummarySpec((ValidationIssue('title', 'Required'),)))
        FormActions(primary_label='Create investigation')

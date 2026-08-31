import nicegui_base


def test_phase3_rendering_api_is_public():
    names = {
        'Button','ActionButton','IconButton','Panel','Card','InteractiveCard','Well','StatusBadge','Tag',
        'TextInput','PasswordInput','NumberInput','TextArea','SearchInput','Select','MultiSelect','Autocomplete',
        'Combobox','Checkbox','CheckboxGroup','RadioGroup','Switch','Slider','RangeSlider','DatePicker',
        'DateRangePicker','TimePicker','DateTimePicker','FileUpload',
    }
    assert names.issubset(set(nicegui_base.__all__))
    for name in names:
        assert hasattr(nicegui_base, name)


def test_phase3_model_api_is_public():
    for name in ['ButtonSpec','FieldSpec','SelectOption','SurfaceVariant','StatusIntent','COMPONENT_REGISTRY','build_component_css']:
        assert name in nicegui_base.__all__
        assert hasattr(nicegui_base, name)


def test_extended_phase3_rendering_api_is_public():
    for name in ['ButtonGroup','SplitButton','Divider','CollapsiblePanel','Accordion','Chip','CountBadge','SeverityIndicator','FreshnessIndicator','DataQualityBadge']:
        assert name in nicegui_base.__all__
        assert hasattr(nicegui_base, name)

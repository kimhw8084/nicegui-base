from pathlib import Path

P=Path('showcase/phase_5_datatable_showcase.html')

def test_showcase_exists_and_is_substantial():
    assert P.exists() and P.stat().st_size > 50_000

def test_showcase_has_no_external_resources():
    s=P.read_text().lower()
    assert 'src="http' not in s and "src='http" not in s and 'href="http' not in s and "href='http" not in s

def test_showcase_exercises_key_table_behaviors():
    s=P.read_text()
    for marker in ('selectionBar','toggleExpand','validateEdits','serverNext','cui-table-loading','statusFilter'):
        assert marker in s

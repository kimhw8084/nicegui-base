from html.parser import HTMLParser
from pathlib import Path

SHOWCASE = Path(__file__).resolve().parents[1] / 'showcase' / 'phase_2_layout_showcase.html'


class Parser(HTMLParser):
    pass


def test_showcase_exists_and_parses():
    text = SHOWCASE.read_text(encoding='utf-8')
    Parser().feed(text)
    assert '<!doctype html>' in text.lower()


def test_showcase_has_no_external_dependencies():
    text = SHOWCASE.read_text(encoding='utf-8').lower()
    assert 'src="http' not in text
    assert "src='http" not in text
    assert 'href="http' not in text
    assert "href='http" not in text
    assert '@import url' not in text


def test_showcase_contains_all_ten_patterns_and_viewport_controls():
    text = SHOWCASE.read_text(encoding='utf-8')
    patterns = ['data_explorer','dashboard','master_detail','monitoring','crud','settings','wizard','comparison','search','analysis_workspace']
    for pattern in patterns:
        assert f'data-page="{pattern}"' in text
    for device in ['desktop','tablet','phone']:
        assert f'data-device="{device}"' in text


def test_showcase_uses_phase1_tokens():
    text = SHOWCASE.read_text(encoding='utf-8')
    assert '--cui-accent:' in text
    assert '--cui-type-page_title-size:' in text
    assert '--cui-shell-sidebar-width:' in text

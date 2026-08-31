from html.parser import HTMLParser
from pathlib import Path

SHOWCASE = Path(__file__).parents[1] / 'showcase/phase_3_components_showcase.html'


class Parser(HTMLParser):
    pass


def test_phase3_showcase_exists_and_parses():
    text = SHOWCASE.read_text()
    parser = Parser(); parser.feed(text)
    assert '<title>Phase 3 — Core Component System</title>' in text


def test_phase3_showcase_is_self_contained():
    text = SHOWCASE.read_text().lower()
    assert 'http://' not in text
    assert 'https://' not in text
    assert '<script src=' not in text
    assert '<link ' not in text


def test_phase3_showcase_uses_framework_classes():
    text = SHOWCASE.read_text()
    for cls in ['cui-button--primary','cui-field-control--error','cui-surface--card','cui-badge--warning','cui-chip','cui-collapsible']:
        assert cls in text


def test_phase3_showcase_has_theme_and_density_controls():
    text = SHOWCASE.read_text()
    assert 'data-theme-btn="dark"' in text
    assert 'data-density-btn="dense"' in text

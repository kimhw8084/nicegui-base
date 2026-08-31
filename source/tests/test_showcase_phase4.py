from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOWCASE = ROOT / 'showcase' / 'phase_4_interaction_showcase.html'


class RefParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.refs = []
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {'src', 'href'} and value:
                self.refs.append(value)


def test_phase4_showcase_exists_and_is_substantial():
    text = SHOWCASE.read_text(encoding='utf-8')
    assert len(text) > 40000
    for marker in ('Advanced filters', 'Create investigation', 'Delete saved view?', 'Interaction-state gallery', 'Async content behavior'):
        assert marker in text


def test_phase4_showcase_has_no_external_resources():
    parser = RefParser(); parser.feed(SHOWCASE.read_text(encoding='utf-8'))
    external = [ref for ref in parser.refs if ref.startswith(('http://', 'https://', '//'))]
    assert external == []


def test_phase4_showcase_supports_review_controls():
    text = SHOWCASE.read_text(encoding='utf-8')
    for marker in ('data-vp="desktop"', 'data-vp="tablet"', 'data-vp="phone"', 'data-theme="dark"', 'data-density="dense"'):
        assert marker in text


def test_phase4_showcase_uses_framework_css_classes():
    text = SHOWCASE.read_text(encoding='utf-8')
    for cls in ('cui-filter-bar', 'cui-drawer', 'cui-dialog', 'cui-alert', 'cui-toast', 'cui-state-view', 'cui-form-actions'):
        assert cls in text

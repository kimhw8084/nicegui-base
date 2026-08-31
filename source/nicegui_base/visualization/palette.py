from __future__ import annotations

from hashlib import sha1

# Restrained, high-separation categorical palette chosen for light/dark compatibility.
CATEGORICAL = ('#2F6FED','#8A5CF6','#00A17A','#D97706','#D14D72','#168AAD','#7C7C85','#B45F06')
SEQUENTIAL_BLUE = ('#EEF5FF','#DCEBFF','#B8D7FF','#8ABEFF','#5A9DFF','#2F7EEA','#1759B7')
DIVERGING = ('#B42318','#DD6B5E','#F4B5AC','#ECEDEF','#A9C7F8','#5C91E7','#245BB5')

SEMANTIC = {
    'success': 'var(--cui-success)',
    'warning': 'var(--cui-warning)',
    'danger': 'var(--cui-danger)',
    'info': 'var(--cui-info)',
    'neutral': 'var(--cui-text-secondary)',
    'accent': 'var(--cui-accent)',
}


def stable_series_color(key: str, palette: tuple[str, ...] = CATEGORICAL) -> str:
    if not key:
        raise ValueError('series color key is required')
    digest = int(sha1(key.encode('utf-8')).hexdigest()[:8], 16)
    return palette[digest % len(palette)]


__all__ = ['CATEGORICAL','DIVERGING','SEMANTIC','SEQUENTIAL_BLUE','stable_series_color']

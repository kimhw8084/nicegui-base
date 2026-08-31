from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import PurePath

from .redaction import safe_filename


@dataclass(frozen=True, slots=True)
class UploadPolicy:
    """Allow-list policy for user-supplied files.

    Extension/media-type checks are paired with lightweight magic/content checks
    for formats whose signatures are deterministic. This is not an antivirus
    scanner; deployments can perform deeper scanning after this mandatory gate.
    """

    max_bytes: int = 25 * 1024 * 1024
    allowed_extensions: frozenset[str] = frozenset({'.csv', '.xlsx', '.json', '.txt', '.png', '.jpg', '.jpeg', '.pdf'})
    allowed_media_types: frozenset[str] = frozenset({
        'text/csv', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/json', 'text/plain', 'image/png', 'image/jpeg', 'application/pdf',
    })
    reject_active_content: bool = True

    def __post_init__(self) -> None:
        if self.max_bytes <= 0:
            raise ValueError('max_bytes must be positive')
        if any(not ext.startswith('.') for ext in self.allowed_extensions):
            raise ValueError('allowed extensions must start with a dot')

    def validate(self, filename: str, size: int, media_type: str | None = None) -> str:
        if size < 0 or size > self.max_bytes:
            raise ValueError('upload size is not permitted')
        name = safe_filename(filename)
        ext = PurePath(name).suffix.lower()
        if ext not in self.allowed_extensions:
            raise ValueError(f'file extension {ext or "<none>"} is not permitted')
        normalized_media = (media_type or '').split(';', 1)[0].strip().lower()
        if normalized_media and normalized_media not in self.allowed_media_types:
            raise ValueError(f'media type {media_type} is not permitted')
        if self.reject_active_content and ext in {'.html', '.htm', '.svg', '.js', '.mjs'}:
            raise ValueError('active content uploads are not permitted')
        return name

    def validate_content(self, filename: str, size: int, media_type: str | None, head: bytes) -> str:
        """Validate metadata plus a bounded leading-byte signature/content sample."""
        name = self.validate(filename, size, media_type)
        ext = PurePath(name).suffix.lower()
        sample = bytes(head[:65536])
        signatures = {
            '.png': (b'\x89PNG\r\n\x1a\n',),
            '.jpg': (b'\xff\xd8\xff',),
            '.jpeg': (b'\xff\xd8\xff',),
            '.pdf': (b'%PDF-',),
            '.xlsx': (b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08'),
        }
        expected = signatures.get(ext)
        if expected is not None and sample and not sample.startswith(expected):
            raise ValueError(f'file content does not match {ext} format')
        if ext == '.json' and sample:
            try:
                json.loads(sample.decode('utf-8-sig'))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                # The complete file can exceed the inspection sample. A truncated
                # JSON sample is allowed only when it is plausibly text JSON.
                try:
                    text = sample.decode('utf-8-sig').lstrip()
                except UnicodeDecodeError:
                    raise ValueError('JSON upload is not valid UTF-8 text') from exc
                if not text.startswith(('{', '[')):
                    raise ValueError('JSON upload content is not valid JSON') from exc
        if ext in {'.csv', '.txt', '.json'} and sample and b'\x00' in sample:
            raise ValueError('text upload contains binary NUL bytes')
        return name

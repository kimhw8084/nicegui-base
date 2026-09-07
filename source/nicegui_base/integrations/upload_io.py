"""Bounded upload reads for NiceGUI 3.x FileUpload and legacy byte/stream events.

NiceGUI 3.15 FileUpload exposes size() and async read()/iterate(), not .content.
This module has no UI imports so parsing/limit behavior can be tested directly.
"""
from __future__ import annotations

import inspect
from typing import Any


def upload_parts(event: Any) -> tuple[str, str | None, Any]:
    file = getattr(event, 'file', None)
    file = event if file is None else file
    name = str(getattr(file, 'name', None) or getattr(event, 'name', None) or 'upload')
    media = getattr(file, 'content_type', None) or getattr(event, 'content_type', None)
    content = getattr(file, 'content', None)
    if content is None:
        content = getattr(event, 'content', None)
    if content is None and callable(getattr(file, 'read', None)):
        content = file
    return name, str(media) if media else None, content


async def _await(value: Any) -> Any:
    return await value if inspect.isawaitable(value) else value


async def read_upload_bytes(content: Any, *, max_bytes: int) -> bytes:
    """Read all permitted bytes or reject. Streams are rewound and restored.

    Iteration is bounded independently of the declared size, which may be wrong.
    An unbounded read is allowed only after checking a declared size.
    """
    if max_bytes < 1:
        raise ValueError('max_bytes must be positive')
    if content is None:
        raise ValueError('The upload contains no readable file content.')
    if isinstance(content, (bytes, bytearray, memoryview)):
        if len(content) > max_bytes:
            raise ValueError(f'Upload exceeds the {max_bytes:,}-byte limit. Existing data was not changed.')
        return bytes(content)
    size = getattr(content, 'size', None)
    if callable(size):
        size = await _await(size())
    if size is not None:
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ValueError('Upload has invalid size metadata.')
        if size > max_bytes:
            raise ValueError(f'Upload exceeds the {max_bytes:,}-byte limit. Existing data was not changed.')
    iterate = getattr(content, 'iterate', None)
    if callable(iterate):
        data = bytearray()
        async for block in iterate(chunk_size=min(65536, max_bytes + 1)):
            if not isinstance(block, (bytes, bytearray, memoryview)):
                raise ValueError('Upload reader returned non-byte content.')
            if len(data) + len(block) > max_bytes:
                raise ValueError(f'Upload exceeds the {max_bytes:,}-byte limit. Existing data was not changed.')
            data.extend(block)
        return bytes(data)
    read = getattr(content, 'read', None)
    if not callable(read):
        raise ValueError('The upload content cannot be read.')
    seek, tell = getattr(content, 'seek', None), getattr(content, 'tell', None)
    position = await _await(tell()) if callable(tell) else None
    try:
        if callable(seek):
            await _await(seek(0))
        try:
            inspect.signature(read).bind(max_bytes + 1)
            bounded = True
        except (TypeError, ValueError):
            bounded = False
        if not bounded and size is None:
            raise ValueError('An upload reader without a bounded read must provide size metadata.')
        data = await _await(read(max_bytes + 1) if bounded else read())
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise ValueError('Upload reader returned non-byte content.')
        if len(data) > max_bytes:
            raise ValueError(f'Upload exceeds the {max_bytes:,}-byte limit. Existing data was not changed.')
        return bytes(data)
    finally:
        if position is not None and callable(seek):
            await _await(seek(position))

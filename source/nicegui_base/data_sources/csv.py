from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .memory import InMemoryDataSource
from .models import DataSchema


class CSVDataSource(InMemoryDataSource):
    """Dependency-free CSV provider intended for development/reference workloads."""

    def __init__(self, key: str, path: str | Path, *, schema: DataSchema | None = None, encoding: str = 'utf-8-sig', timeout_seconds: float | None = 30.0) -> None:
        self.path = Path(path)
        if not self.path.is_file():
            raise FileNotFoundError(self.path)
        with self.path.open('r', encoding=encoding, newline='') as handle:
            rows: list[dict[str, Any]] = list(csv.DictReader(handle))
        super().__init__(key, rows, schema=schema, timeout_seconds=timeout_seconds)

    @property
    def provider(self) -> str:
        return 'csv'


__all__ = ['CSVDataSource']

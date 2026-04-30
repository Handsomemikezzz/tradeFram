from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DataLayerPaths:
    root: Path

    @property
    def raw_root(self) -> Path:
        return self.root / "raw"

    @property
    def warehouse_root(self) -> Path:
        return self.root / "warehouse"

    @property
    def metadata_root(self) -> Path:
        return self.root / "metadata"

    @property
    def reports_root(self) -> Path:
        return self.metadata_root / "reports"

    @property
    def sync_db(self) -> Path:
        return self.metadata_root / "sync_state.db"

    def ensure(self) -> None:
        for path in [self.raw_root, self.warehouse_root, self.metadata_root, self.reports_root]:
            path.mkdir(parents=True, exist_ok=True)

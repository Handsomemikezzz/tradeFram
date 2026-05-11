from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd


class ParquetStore:
    def write_dataset(
        self,
        path: Path,
        frame: pd.DataFrame,
        *,
        partition_cols: list[str] | None = None,
        overwrite: bool = True,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if overwrite and path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        path.mkdir(parents=True, exist_ok=True)
        if partition_cols:
            frame.to_parquet(path, index=False, partition_cols=partition_cols)
        else:
            frame.to_parquet(path / "part.parquet", index=False)

    def read_dataset(self, path: Path, *, columns: list[str] | None = None, filters=None) -> pd.DataFrame:
        frame = pd.read_parquet(path, columns=columns, filters=filters)
        for column in ["code", "symbol", "exchange", "index_code", "price_adjustment"]:
            if column in frame.columns:
                frame[column] = frame[column].astype("string").astype(str)
        if "code" in frame.columns:
            frame["code"] = frame["code"].str.zfill(6)
        return frame

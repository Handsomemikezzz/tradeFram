from __future__ import annotations

from datetime import date

import pandas as pd

from backend.app.data_layer.storage.metadata_store import MetadataStore
from backend.app.data_layer.storage.parquet_store import ParquetStore
from backend.app.data_layer.storage.paths import DataLayerPaths


def test_data_layer_paths_create_expected_directories(tmp_path):
    paths = DataLayerPaths(tmp_path / "data")

    paths.ensure()

    assert paths.raw_root.is_dir()
    assert paths.warehouse_root.is_dir()
    assert paths.metadata_root.is_dir()
    assert paths.reports_root.is_dir()
    assert paths.sync_db == tmp_path / "data" / "metadata" / "sync_state.db"


def test_parquet_store_round_trips_dataset(tmp_path):
    store = ParquetStore()
    frame = pd.DataFrame(
        [
            {"code": "600519", "trade_date": date(2026, 4, 29), "close": 101.5},
            {"code": "600519", "trade_date": date(2026, 4, 30), "close": 102.5},
        ]
    )
    target = tmp_path / "warehouse" / "daily_bars"

    store.write_dataset(target, frame, partition_cols=["code"], overwrite=True)
    result = store.read_dataset(target).sort_values("trade_date").reset_index(drop=True)

    assert list(result["code"]) == ["600519", "600519"]
    assert list(result["close"]) == [101.5, 102.5]


def test_metadata_store_tracks_runs_items_and_resume_keys(tmp_path):
    paths = DataLayerPaths(tmp_path / "data")
    paths.ensure()
    store = MetadataStore(paths.sync_db)

    run_id = store.create_run(
        provider="akshare",
        job_type="init_history_data",
        start_date=date(2020, 1, 1),
        end_date=date(2026, 4, 30),
    )
    item_id = store.record_item(
        run_id=run_id,
        provider="akshare",
        dataset="daily_bars",
        key="600519",
        start_date=date(2020, 1, 1),
        end_date=date(2026, 4, 30),
    )

    store.mark_item_success(item_id, row_count=300)
    store.finish_run(run_id, status="success")

    assert store.successful_item_keys(run_id, dataset="daily_bars") == {"600519"}
    run = store.get_run(run_id)
    assert run["status"] == "success"
    assert run["provider"] == "akshare"

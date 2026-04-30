from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _date_iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


class MetadataStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def create_run(self, *, provider: str, job_type: str, start_date: date | None, end_date: date | None) -> str:
        run_id = f"run_{uuid4().hex}"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sync_runs (id, provider, job_type, start_date, end_date, status, started_at)
                VALUES (?, ?, ?, ?, ?, 'running', ?)
                """,
                (run_id, provider, job_type, _date_iso(start_date), _date_iso(end_date), _now_iso()),
            )
        return run_id

    def finish_run(self, run_id: str, *, status: str, error_message: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE sync_runs SET status = ?, finished_at = ?, error_message = ? WHERE id = ?",
                (status, _now_iso(), error_message, run_id),
            )

    def get_run(self, run_id: str) -> dict:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM sync_runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        return dict(row)

    def record_item(
        self,
        *,
        run_id: str,
        provider: str,
        dataset: str,
        key: str,
        start_date: date | None,
        end_date: date | None,
        status: str = "pending",
    ) -> str:
        item_id = f"item_{uuid4().hex}"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sync_items (
                  id, run_id, provider, dataset, key, start_date, end_date, status, attempt_count, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    item_id,
                    run_id,
                    provider,
                    dataset,
                    key,
                    _date_iso(start_date),
                    _date_iso(end_date),
                    status,
                    _now_iso(),
                ),
            )
        return item_id

    def mark_item_success(self, item_id: str, *, row_count: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE sync_items
                SET status = 'success', row_count = ?, error_message = NULL,
                    attempt_count = attempt_count + 1, updated_at = ?
                WHERE id = ?
                """,
                (row_count, _now_iso(), item_id),
            )

    def mark_item_failed(self, item_id: str, *, error_message: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE sync_items
                SET status = 'failed', error_message = ?,
                    attempt_count = attempt_count + 1, updated_at = ?
                WHERE id = ?
                """,
                (error_message, _now_iso(), item_id),
            )

    def successful_item_keys(self, run_id: str, *, dataset: str) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT key FROM sync_items WHERE run_id = ? AND dataset = ? AND status = 'success'",
                (run_id, dataset),
            ).fetchall()
        return {row["key"] for row in rows}

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_runs (
                  id TEXT PRIMARY KEY,
                  provider TEXT NOT NULL,
                  job_type TEXT NOT NULL,
                  start_date TEXT,
                  end_date TEXT,
                  status TEXT NOT NULL,
                  started_at TEXT NOT NULL,
                  finished_at TEXT,
                  error_message TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_items (
                  id TEXT PRIMARY KEY,
                  run_id TEXT NOT NULL,
                  provider TEXT NOT NULL,
                  dataset TEXT NOT NULL,
                  key TEXT NOT NULL,
                  start_date TEXT,
                  end_date TEXT,
                  status TEXT NOT NULL,
                  row_count INTEGER,
                  error_message TEXT,
                  attempt_count INTEGER NOT NULL DEFAULT 0,
                  updated_at TEXT NOT NULL,
                  FOREIGN KEY(run_id) REFERENCES sync_runs(id)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_items_run_dataset_status ON sync_items(run_id, dataset, status)")

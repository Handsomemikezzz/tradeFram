"""screener snapshots

Revision ID: 20260602_0005
Revises: 20260601_0004
Create Date: 2026-06-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260602_0005"
down_revision = "20260601_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "screener_snapshot" not in tables:
        op.create_table(
            "screener_snapshot",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("trade_date", sa.Date(), nullable=False),
            sa.Column("strategy_type", sa.String(length=32), nullable=False),
            sa.Column("strategy_name", sa.String(length=64), nullable=False),
            sa.Column("strategy_version", sa.String(length=16), nullable=False),
            sa.Column("provider", sa.String(length=64), nullable=False),
            sa.Column("price_adjustment", sa.String(length=16), nullable=False),
            sa.Column("criteria", sa.JSON(), nullable=False),
            sa.Column("scan_count", sa.Integer(), nullable=False),
            sa.Column("eligible_count", sa.Integer(), nullable=False),
            sa.Column("confirmed_count", sa.Integer(), nullable=False),
            sa.Column("pending_count", sa.Integer(), nullable=False),
            sa.Column("coverage", sa.Float(), nullable=False),
            sa.Column("generated_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "trade_date",
                "strategy_type",
                "strategy_version",
                "provider",
                name="uq_screener_snapshot_date_strategy_provider",
            ),
        )
    _create_index_if_missing("screener_snapshot", "ix_screener_snapshot_trade_date", ["trade_date"])
    _create_index_if_missing("screener_snapshot", "ix_screener_snapshot_strategy_type", ["strategy_type"])

    if "screener_item" not in tables:
        op.create_table(
            "screener_item",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("snapshot_id", sa.String(length=64), nullable=False),
            sa.Column("trade_date", sa.Date(), nullable=False),
            sa.Column("code", sa.String(length=6), nullable=False),
            sa.Column("name", sa.String(length=64), nullable=False),
            sa.Column("industry", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("signal_date", sa.Date(), nullable=False),
            sa.Column("score", sa.Integer(), nullable=False),
            sa.Column("price_action_score", sa.Integer(), nullable=False),
            sa.Column("moving_average_score", sa.Integer(), nullable=False),
            sa.Column("volume_score", sa.Integer(), nullable=False),
            sa.Column("change_percent", sa.Float(), nullable=True),
            sa.Column("tags", sa.JSON(), nullable=False),
            sa.Column("reason", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["snapshot_id"], ["screener_snapshot.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("screener_item", "ix_screener_item_snapshot_id", ["snapshot_id"])
    _create_index_if_missing("screener_item", "ix_screener_item_code", ["code"])
    _create_index_if_missing("screener_item", "ix_screener_item_status", ["status"])


def downgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "screener_item" in tables:
        _drop_index_if_exists("screener_item", "ix_screener_item_status")
        _drop_index_if_exists("screener_item", "ix_screener_item_code")
        _drop_index_if_exists("screener_item", "ix_screener_item_snapshot_id")
        op.drop_table("screener_item")
    if "screener_snapshot" in tables:
        _drop_index_if_exists("screener_snapshot", "ix_screener_snapshot_strategy_type")
        _drop_index_if_exists("screener_snapshot", "ix_screener_snapshot_trade_date")
        op.drop_table("screener_snapshot")


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str]) -> None:
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}
    if index_name not in indexes:
        op.create_index(index_name, table_name, columns)


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}
    if index_name in indexes:
        op.drop_index(index_name, table_name=table_name)

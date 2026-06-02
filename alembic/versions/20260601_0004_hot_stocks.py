"""hot stocks

Revision ID: 20260601_0004
Revises: 20260517_0003
Create Date: 2026-06-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260601_0004"
down_revision = "20260517_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "hot_stock_snapshot" not in tables:
        op.create_table(
            "hot_stock_snapshot",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("trade_date", sa.Date(), nullable=False),
            sa.Column("source", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("trade_date", "source", name="uq_hot_stock_snapshot_date_source"),
        )
    _create_index_if_missing("hot_stock_snapshot", "ix_hot_stock_snapshot_trade_date", ["trade_date"])
    _create_index_if_missing("hot_stock_snapshot", "ix_hot_stock_snapshot_source", ["source"])
    _create_index_if_missing("hot_stock_snapshot", "ix_hot_stock_snapshot_status", ["status"])

    if "hot_stock_item" not in tables:
        op.create_table(
            "hot_stock_item",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("snapshot_id", sa.String(length=64), nullable=False),
            sa.Column("rank", sa.Integer(), nullable=False),
            sa.Column("code", sa.String(length=6), nullable=False),
            sa.Column("name", sa.String(length=64), nullable=False),
            sa.Column("price", sa.Float(), nullable=True),
            sa.Column("change_percent", sa.Float(), nullable=True),
            sa.Column("industry", sa.String(length=64), nullable=True),
            sa.Column("ma5", sa.Float(), nullable=True),
            sa.Column("ma20", sa.Float(), nullable=True),
            sa.Column("trend_label", sa.String(length=16), nullable=False),
            sa.Column("is_recent_limit_up_break", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["snapshot_id"], ["hot_stock_snapshot.id"]),
            sa.ForeignKeyConstraint(["code"], ["stock.code"]),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("hot_stock_item", "ix_hot_stock_item_snapshot_id", ["snapshot_id"])
    _create_index_if_missing("hot_stock_item", "ix_hot_stock_item_code", ["code"])


def downgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "hot_stock_item" in tables:
        _drop_index_if_exists("hot_stock_item", "ix_hot_stock_item_code")
        _drop_index_if_exists("hot_stock_item", "ix_hot_stock_item_snapshot_id")
        op.drop_table("hot_stock_item")
    if "hot_stock_snapshot" in tables:
        _drop_index_if_exists("hot_stock_snapshot", "ix_hot_stock_snapshot_status")
        _drop_index_if_exists("hot_stock_snapshot", "ix_hot_stock_snapshot_source")
        _drop_index_if_exists("hot_stock_snapshot", "ix_hot_stock_snapshot_trade_date")
        op.drop_table("hot_stock_snapshot")


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str]) -> None:
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}
    if index_name not in indexes:
        op.create_index(index_name, table_name, columns)


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}
    if index_name in indexes:
        op.drop_index(index_name, table_name=table_name)

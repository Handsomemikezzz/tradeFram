"""stock review cards

Revision ID: 20260517_0003
Revises: 20260517_0002
Create Date: 2026-05-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260517_0003"
down_revision = "20260517_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "stock_review_cards" not in tables:
        op.create_table(
            "stock_review_cards",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("code", sa.String(length=6), nullable=True),
            sa.Column("name", sa.String(length=64), nullable=True),
            sa.Column("sector_tags", sa.JSON(), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("initial_action", sa.String(length=32), nullable=False),
            sa.Column("initial_position_context", sa.String(length=32), nullable=True),
            sa.Column("initial_plan_status", sa.String(length=32), nullable=False),
            sa.Column("initial_reason_text", sa.Text(), nullable=False),
            sa.Column("expected_move_text", sa.Text(), nullable=False),
            sa.Column("original_plan_text", sa.Text(), nullable=False),
            sa.Column("initial_emotion_tags", sa.JSON(), nullable=False),
            sa.Column("problem_tags", sa.JSON(), nullable=False),
            sa.Column("sell_reason_text", sa.Text(), nullable=True),
            sa.Column("pnl_text", sa.Text(), nullable=True),
            sa.Column("followed_plan", sa.Boolean(), nullable=True),
            sa.Column("discipline_score", sa.Integer(), nullable=True),
            sa.Column("did_well_text", sa.Text(), nullable=True),
            sa.Column("did_wrong_text", sa.Text(), nullable=True),
            sa.Column("reflection_text", sa.Text(), nullable=True),
            sa.Column("rule_text", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("stock_review_cards", "ix_stock_review_cards_status", ["status"])
    _create_index_if_missing("stock_review_cards", "ix_stock_review_cards_code", ["code"])
    _create_index_if_missing("stock_review_cards", "ix_stock_review_cards_start_date", ["start_date"])
    _create_index_if_missing("stock_review_cards", "ix_stock_review_cards_end_date", ["end_date"])
    _create_index_if_missing("stock_review_cards", "ix_stock_review_cards_initial_action", ["initial_action"])
    _create_index_if_missing(
        "stock_review_cards",
        "ix_stock_review_cards_initial_plan_status",
        ["initial_plan_status"],
    )

    if "stock_review_events" not in tables:
        op.create_table(
            "stock_review_events",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("card_id", sa.String(length=64), nullable=False),
            sa.Column("event_date", sa.Date(), nullable=False),
            sa.Column("event_type", sa.String(length=32), nullable=False),
            sa.Column("title", sa.String(length=96), nullable=False),
            sa.Column("reason_text", sa.Text(), nullable=False),
            sa.Column("position_snapshot", sa.String(length=128), nullable=True),
            sa.Column("deviated_from_plan", sa.Boolean(), nullable=False),
            sa.Column("emotion_tags", sa.JSON(), nullable=False),
            sa.Column("problem_tags", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["card_id"], ["stock_review_cards.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("stock_review_events", "ix_stock_review_events_card_id", ["card_id"])
    _create_index_if_missing("stock_review_events", "ix_stock_review_events_event_date", ["event_date"])
    _create_index_if_missing("stock_review_events", "ix_stock_review_events_event_type", ["event_type"])


def downgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "stock_review_events" in tables:
        _drop_index_if_exists("stock_review_events", "ix_stock_review_events_event_type")
        _drop_index_if_exists("stock_review_events", "ix_stock_review_events_event_date")
        _drop_index_if_exists("stock_review_events", "ix_stock_review_events_card_id")
        op.drop_table("stock_review_events")
    if "stock_review_cards" in tables:
        _drop_index_if_exists("stock_review_cards", "ix_stock_review_cards_initial_plan_status")
        _drop_index_if_exists("stock_review_cards", "ix_stock_review_cards_initial_action")
        _drop_index_if_exists("stock_review_cards", "ix_stock_review_cards_end_date")
        _drop_index_if_exists("stock_review_cards", "ix_stock_review_cards_start_date")
        _drop_index_if_exists("stock_review_cards", "ix_stock_review_cards_code")
        _drop_index_if_exists("stock_review_cards", "ix_stock_review_cards_status")
        op.drop_table("stock_review_cards")


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str]) -> None:
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}
    if index_name not in indexes:
        op.create_index(index_name, table_name, columns)


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}
    if index_name in indexes:
        op.drop_index(index_name, table_name=table_name)

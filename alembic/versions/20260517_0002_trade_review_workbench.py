"""trade review workbench

Revision ID: 20260517_0002
Revises: 20260426_0001
Create Date: 2026-05-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260517_0002"
down_revision = "20260426_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "review_entry" not in tables:
        op.create_table(
            "review_entry",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("entry_type", sa.String(length=32), nullable=False),
            sa.Column("action_type", sa.String(length=32), nullable=False),
            sa.Column("trade_date", sa.Date(), nullable=False),
            sa.Column("code", sa.String(length=6), nullable=True),
            sa.Column("name", sa.String(length=64), nullable=True),
            sa.Column("sector_tags", sa.JSON(), nullable=False),
            sa.Column("position_context", sa.String(length=32), nullable=True),
            sa.Column("plan_status", sa.String(length=32), nullable=False),
            sa.Column("emotion_tags", sa.JSON(), nullable=False),
            sa.Column("problem_tags", sa.JSON(), nullable=False),
            sa.Column("reason_text", sa.Text(), nullable=False),
            sa.Column("reflection_text", sa.Text(), nullable=False),
            sa.Column("conclusion_text", sa.Text(), nullable=False),
            sa.Column("next_action_text", sa.Text(), nullable=False),
            sa.Column("discipline_score", sa.Integer(), nullable=False),
            sa.Column("outcome_text", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing("review_entry", "ix_review_entry_entry_type", ["entry_type"])
    _create_index_if_missing("review_entry", "ix_review_entry_action_type", ["action_type"])
    _create_index_if_missing("review_entry", "ix_review_entry_trade_date", ["trade_date"])
    _create_index_if_missing("review_entry", "ix_review_entry_code", ["code"])
    _create_index_if_missing("review_entry", "ix_review_entry_plan_status", ["plan_status"])

    if "weekly_review" not in tables:
        op.create_table(
            "weekly_review",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("week_start", sa.Date(), nullable=False),
            sa.Column("week_end", sa.Date(), nullable=False),
            sa.Column("summary_text", sa.Text(), nullable=False),
            sa.Column("repeated_mistakes_text", sa.Text(), nullable=False),
            sa.Column("effective_actions_text", sa.Text(), nullable=False),
            sa.Column("emotion_pattern_text", sa.Text(), nullable=False),
            sa.Column("next_week_focus_text", sa.Text(), nullable=False),
            sa.Column("rule_candidates_text", sa.Text(), nullable=False),
            sa.Column("linked_entry_ids", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("week_start", name="uq_weekly_review_week_start"),
        )
    _create_index_if_missing("weekly_review", "ix_weekly_review_week_start", ["week_start"])


def downgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "weekly_review" in tables:
        _drop_index_if_exists("weekly_review", "ix_weekly_review_week_start")
        op.drop_table("weekly_review")
    if "review_entry" in tables:
        _drop_index_if_exists("review_entry", "ix_review_entry_plan_status")
        _drop_index_if_exists("review_entry", "ix_review_entry_code")
        _drop_index_if_exists("review_entry", "ix_review_entry_trade_date")
        _drop_index_if_exists("review_entry", "ix_review_entry_action_type")
        _drop_index_if_exists("review_entry", "ix_review_entry_entry_type")
        op.drop_table("review_entry")


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str]) -> None:
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}
    if index_name not in indexes:
        op.create_index(index_name, table_name, columns)


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}
    if index_name in indexes:
        op.drop_index(index_name, table_name=table_name)

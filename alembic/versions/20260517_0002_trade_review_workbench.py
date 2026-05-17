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
    op.create_index("ix_review_entry_entry_type", "review_entry", ["entry_type"])
    op.create_index("ix_review_entry_action_type", "review_entry", ["action_type"])
    op.create_index("ix_review_entry_trade_date", "review_entry", ["trade_date"])
    op.create_index("ix_review_entry_code", "review_entry", ["code"])
    op.create_index("ix_review_entry_plan_status", "review_entry", ["plan_status"])

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
    op.create_index("ix_weekly_review_week_start", "weekly_review", ["week_start"])


def downgrade() -> None:
    op.drop_index("ix_weekly_review_week_start", table_name="weekly_review")
    op.drop_table("weekly_review")
    op.drop_index("ix_review_entry_plan_status", table_name="review_entry")
    op.drop_index("ix_review_entry_code", table_name="review_entry")
    op.drop_index("ix_review_entry_trade_date", table_name="review_entry")
    op.drop_index("ix_review_entry_action_type", table_name="review_entry")
    op.drop_index("ix_review_entry_entry_type", table_name="review_entry")
    op.drop_table("review_entry")

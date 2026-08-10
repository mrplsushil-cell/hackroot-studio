"""asset ordering + original filename

Revision ID: 0002
Revises: 0001
Create Date: 2026-01-02
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa


revision = "0002_asset_ordering"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assets",
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "assets",
        sa.Column("original_filename", sa.String(255), nullable=True),
    )
    op.add_column(
        "assets",
        sa.Column("checksum", sa.String(64), nullable=True),
    )
    op.create_index("ix_assets_owner_video", "assets", ["owner_id", "video_id"])
    # `duration` was created as INTEGER but the ORM/schema treat it as a float
    # (seconds, fractional for audio/video assets).
    op.alter_column(
        "assets", "duration", type_=sa.Float(), existing_type=sa.Integer(), existing_nullable=True
    )


def downgrade() -> None:
    op.alter_column(
        "assets", "duration", type_=sa.Integer(), existing_type=sa.Float(), existing_nullable=True
    )
    op.drop_index("ix_assets_owner_video", table_name="assets")
    op.drop_column("assets", "checksum")
    op.drop_column("assets", "original_filename")
    op.drop_column("assets", "sort_order")

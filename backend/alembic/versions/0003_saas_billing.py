"""Phase 8 — SaaS monetization schema.

Adds subscription plans, subscriptions, invoices, credit transactions,
notifications, API keys, request logs and audit logs.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_saas_billing"
down_revision = "0002_asset_ordering"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("slug", sa.String(48), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(96), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_monthly", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("price_yearly", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="INR"),
        sa.Column("credits_per_month", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("video_limit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("has_watermark", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("priority_queue", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("api_access", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("team_members", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("razorpay_plan_id", sa.String(128), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  onupdate=sa.func.now(), nullable=False),
    )
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("subscription_plans.id"), nullable=False, index=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="active", index=True),
        sa.Column("billing_cycle", sa.String(12), nullable=False, server_default="monthly"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("razorpay_subscription_id", sa.String(128), nullable=True, index=True),
        sa.Column("razorpay_customer_id", sa.String(128), nullable=True),
        sa.Column("external_status", sa.String(48), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  onupdate=sa.func.now(), nullable=False),
    )
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("invoice_no", sa.String(48), unique=True, nullable=False, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("subscription_id", sa.Integer(), sa.ForeignKey("subscriptions.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("subscription_plans.id"), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="INR"),
        sa.Column("tax_amount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(24), nullable=False, server_default="paid", index=True),
        sa.Column("billing_cycle", sa.String(12), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("razorpay_order_id", sa.String(128), nullable=True, index=True),
        sa.Column("razorpay_payment_id", sa.String(128), nullable=True),
        sa.Column("razorpay_signature", sa.String(256), nullable=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("receipt_url", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "credit_transactions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("change", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(32), nullable=False, index=True),
        sa.Column("reference_type", sa.String(32), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("admin_user_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False, index=True),
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("type", sa.String(32), nullable=False, index=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("link", sa.String(256), nullable=True),
        sa.Column("read", sa.Boolean(), nullable=False, server_default=sa.false(), index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False, index=True),
    )
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("name", sa.String(96), nullable=False),
        sa.Column("key_prefix", sa.String(12), nullable=False, index=True),
        sa.Column("key_hash", sa.String(128), nullable=False),
        sa.Column("scopes", sa.String(128), nullable=False, server_default="generate:video,generate:script,generate:thumbnail"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("monthly_quota", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "request_logs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), nullable=True, index=True),
        sa.Column("api_key_id", sa.Integer(), nullable=True, index=True),
        sa.Column("method", sa.String(8), nullable=False),
        sa.Column("path", sa.String(255), nullable=False, index=True),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
    )
    op.create_table(
        "team_members",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("email", sa.String(255), nullable=False, index=True),
        sa.Column("role", sa.String(16), nullable=False, server_default="viewer"),
        sa.Column("status", sa.String(16), nullable=False, server_default="invited"),
        sa.Column("invited_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("actor_id", sa.Integer(), nullable=True, index=True),
        sa.Column("actor_type", sa.String(16), nullable=False, server_default="user"),
        sa.Column("action", sa.String(64), nullable=False, index=True),
        sa.Column("target_type", sa.String(32), nullable=True),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
    )


def downgrade() -> None:
    for t in ("audit_logs", "team_members", "request_logs", "api_keys", "notifications",
              "credit_transactions", "invoices", "subscriptions", "subscription_plans"):
        op.drop_table(t)

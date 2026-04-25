"""Initial security schema: users, refresh_tokens, audit_log, abuse_events, ip_bans

Revision ID: 0001_initial_security
Revises:
Create Date: 2026-04-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_initial_security"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "citext";')

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("email_normalized", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_admin", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("tier", sa.String(32), nullable=False, server_default="free"),
        sa.Column("failed_login_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True)),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("last_login_ip", sa.String(45)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("char_length(email) >= 3", name="ck_users_email_len"),
        sa.CheckConstraint("tier IN ('free','pro','admin')", name="ck_users_tier"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_email_normalized", "users", ["email_normalized"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("user_agent", sa.String(512)),
        sa.Column("ip", sa.String(45)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("rotated_from", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("event", sa.String(64), nullable=False),
        sa.Column("ip", sa.String(45)),
        sa.Column("user_agent", sa.String(512)),
        sa.Column("meta", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("ix_audit_log_event", "audit_log", ["event"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])

    op.create_table(
        "abuse_events",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("ip", sa.String(45)),
        sa.Column("user_agent", sa.String(512)),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("severity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("payload_excerpt", sa.Text),
        sa.Column("matched_rules", postgresql.JSONB),
        sa.Column("route", sa.String(128)),
        sa.Column("action_taken", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_abuse_events_user_id", "abuse_events", ["user_id"])
    op.create_index("ix_abuse_events_ip", "abuse_events", ["ip"])
    op.create_index("ix_abuse_events_category", "abuse_events", ["category"])
    op.create_index("ix_abuse_events_payload_hash", "abuse_events", ["payload_hash"])
    op.create_index("ix_abuse_events_created_at", "abuse_events", ["created_at"])
    op.create_index("ix_abuse_events_ip_created", "abuse_events", ["ip", "created_at"])
    op.create_index("ix_abuse_events_user_created", "abuse_events", ["user_id", "created_at"])

    op.create_table(
        "ip_bans",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("ip", sa.String(45), nullable=False),
        sa.Column("reason", sa.String(256), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ip_bans_ip", "ip_bans", ["ip"], unique=True)


def downgrade() -> None:
    op.drop_table("ip_bans")
    op.drop_table("abuse_events")
    op.drop_table("audit_log")
    op.drop_table("refresh_tokens")
    op.drop_table("users")

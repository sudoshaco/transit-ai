"""2FA + Email-Verify fields

Revision ID: 0002_2fa_email_verify
Revises: 0001_initial_security
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_2fa_email_verify"
down_revision = "0001_initial_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verify_token", sa.String(128), nullable=True))
    op.add_column("users", sa.Column("email_verify_expires", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("email_verify_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("totp_secret_enc", sa.Text, nullable=True))
    op.add_column("users", sa.Column("totp_enabled", sa.Boolean, nullable=False, server_default=sa.text("false")))
    op.add_column("users", sa.Column("totp_backup_codes", postgresql.JSONB, nullable=True))
    op.add_column("users", sa.Column("totp_confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_email_verify_token", "users", ["email_verify_token"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_email_verify_token", table_name="users")
    for col in ("totp_confirmed_at", "totp_backup_codes", "totp_enabled",
                "totp_secret_enc", "email_verify_sent_at",
                "email_verify_expires", "email_verify_token"):
        op.drop_column("users", col)

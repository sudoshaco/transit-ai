"""User bio + username_changed_at

Revision ID: 0004_user_bio
Revises: 0003_community
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_user_bio"
down_revision = "0003_community"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("bio", sa.String(280), nullable=True))
    op.add_column("users", sa.Column("username_changed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "username_changed_at")
    op.drop_column("users", "bio")

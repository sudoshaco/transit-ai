"""Community: username, karma, connection_comments, connection_votes

Revision ID: 0003_community
Revises: 0002_2fa_email_verify
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_community"
down_revision = "0002_2fa_email_verify"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(30), nullable=True))
    op.add_column("users", sa.Column("karma", sa.Integer, nullable=False, server_default=sa.text("0")))
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "connection_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("fp_hash", sa.String(64), nullable=False, index=True),
        sa.Column("fp_meta", postgresql.JSONB, nullable=False),
        sa.Column("body", sa.String(140), nullable=False),
        sa.Column("upvotes", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("downvotes", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("score", sa.Integer, nullable=False, server_default=sa.text("0"), index=True),
        sa.Column("hidden", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("author_id", "fp_hash", name="uq_comment_author_fp"),
    )
    op.create_index("ix_comments_fp_score", "connection_comments", ["fp_hash", "score"])

    op.create_table(
        "connection_votes",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("comment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("connection_comments.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("value", sa.SmallInteger, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("value IN (-1, 1)", name="ck_vote_value"),
    )
    op.create_index("ix_votes_comment", "connection_votes", ["comment_id"])


def downgrade() -> None:
    op.drop_index("ix_votes_comment", table_name="connection_votes")
    op.drop_table("connection_votes")
    op.drop_index("ix_comments_fp_score", table_name="connection_comments")
    op.drop_table("connection_comments")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "karma")
    op.drop_column("users", "username")

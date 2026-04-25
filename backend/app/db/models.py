import uuid
from datetime import datetime
from sqlalchemy import (
    String, Boolean, Integer, DateTime, ForeignKey, Text, Index, func,
    CheckConstraint, BigInteger,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    email_normalized: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tier: Mapped[str] = mapped_column(String(32), default="free", nullable=False)

    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    email_verify_token: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    email_verify_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_verify_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    totp_secret_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    totp_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    totp_backup_codes: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    username: Mapped[str | None] = mapped_column(String(30), nullable=True, unique=True, index=True)
    username_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    karma: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bio: Mapped[str | None] = mapped_column(String(280), nullable=True)

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user", cascade="all,delete-orphan")

    __table_args__ = (
        CheckConstraint("char_length(email) >= 3", name="ck_users_email_len"),
        CheckConstraint("tier IN ('free','pro','admin')", name="ck_users_tier"),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rotated_from: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="refresh_tokens")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class AbuseEvent(Base):
    """Dokumentiert Verstöße — für internes Monitoring und ggf. Meldung an Behörden."""
    __tablename__ = "abuse_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # prompt_injection, illegal_drugs, weapons, hacking, csam, doxing, other
    severity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)      # 1 low ... 5 critical
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)       # gekürzt, max 2000 chars
    matched_rules: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    route: Mapped[str | None] = mapped_column(String(128), nullable=True)
    action_taken: Mapped[str | None] = mapped_column(String(64), nullable=True)    # blocked, warned, banned
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    __table_args__ = (
        Index("ix_abuse_events_ip_created", "ip", "created_at"),
        Index("ix_abuse_events_user_created", "user_id", "created_at"),
    )


class IpBan(Base):
    __tablename__ = "ip_bans"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ip: Mapped[str] = mapped_column(String(45), unique=True, nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(256), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ConnectionComment(Base):
    __tablename__ = "connection_comments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    fp_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    fp_meta: Mapped[dict] = mapped_column(JSONB, nullable=False)
    body: Mapped[str] = mapped_column(String(140), nullable=False)
    upvotes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    downvotes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ConnectionVote(Base):
    __tablename__ = "connection_votes"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    comment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connection_comments.id", ondelete="CASCADE"), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


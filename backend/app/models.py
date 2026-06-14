from datetime import datetime
from sqlalchemy import BigInteger, Integer, String, Boolean, DateTime, Text, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database import Base

class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str] = mapped_column(String(10), default="ru")
    pro_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    last_digest_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    digest_schedule_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    stars_income: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    timezone: Mapped[str | None] = mapped_column(String(50), default="Europe/Moscow", nullable=True)


    # Relationships
    activations: Mapped[list["Activation"]] = relationship("Activation", back_populates="user", cascade="all, delete-orphan")
    keywords: Mapped[list["Keyword"]] = relationship("Keyword", back_populates="user", cascade="all, delete-orphan")
    caught_messages: Mapped[list["CaughtMessage"]] = relationship("CaughtMessage", back_populates="user", cascade="all, delete-orphan")
    user_channels: Mapped[list["UserChannel"]] = relationship("UserChannel", back_populates="user", cascade="all, delete-orphan")
    digest_history: Mapped[list["DigestHistory"]] = relationship("DigestHistory", back_populates="user", cascade="all, delete-orphan")

    @property
    def is_pro(self) -> bool:
        if self.is_admin:
            return True
        if self.pro_expires_at is None:
            return False
        return self.pro_expires_at > datetime.utcnow()

class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True) # lowercase channel handle (e.g. "durov")
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True, index=True) # resolved chat ID
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    userbot_session_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("userbot_sessions.id", ondelete="SET NULL"), nullable=True, index=True)

    # Relationships
    user_channels: Mapped[list["UserChannel"]] = relationship("UserChannel", back_populates="channel", cascade="all, delete-orphan")
    caught_messages: Mapped[list["CaughtMessage"]] = relationship("CaughtMessage", back_populates="channel", cascade="all, delete-orphan")
    session: Mapped["UserbotSession | None"] = relationship("UserbotSession", back_populates="channels")

class UserChannel(Base):
    __tablename__ = "user_channels"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), primary_key=True)
    channel_id: Mapped[int] = mapped_column(Integer, ForeignKey("channels.id", ondelete="CASCADE"), primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    digest_schedule_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    digest_schedule_days: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="user_channels")
    channel: Mapped["Channel"] = relationship("Channel", back_populates="user_channels")

class Keyword(Base):
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), index=True)
    channel_id: Mapped[int] = mapped_column(Integer, ForeignKey("channels.id", ondelete="CASCADE"), index=True)
    keyword: Mapped[str] = mapped_column(String(255), index=True)
    mode: Mapped[str] = mapped_column(String(20), default="semantic") # semantic, exact_phrase, exact_word, exclude

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="keywords")

    __table_args__ = (
        UniqueConstraint("user_id", "channel_id", "keyword", "mode", name="uq_user_channel_keyword_mode"),
    )

class CaughtMessage(Base):
    __tablename__ = "caught_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), index=True)
    channel_id: Mapped[int] = mapped_column(Integer, ForeignKey("channels.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[int] = mapped_column(BigInteger)
    text: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="caught_messages")
    channel: Mapped["Channel"] = relationship("Channel", back_populates="caught_messages")

class Promocode(Base):
    __tablename__ = "promocodes"

    code: Mapped[str] = mapped_column(String(100), primary_key=True)
    duration_days: Mapped[int] = mapped_column(Integer) # e.g. 30, 9999 for lifetime
    max_activations: Mapped[int] = mapped_column(Integer)
    activations_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    activations: Mapped[list["Activation"]] = relationship("Activation", back_populates="promocode", cascade="all, delete-orphan")

class Activation(Base):
    __tablename__ = "activations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(100), ForeignKey("promocodes.code", ondelete="CASCADE"), index=True)
    activated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="activations")
    promocode: Mapped["Promocode"] = relationship("Promocode", back_populates="activations")

    __table_args__ = (
        UniqueConstraint("user_id", "code", name="uq_user_code_activation"),
    )

class UserbotSession(Base):
    __tablename__ = "userbot_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(50), unique=True)
    session_name: Mapped[str] = mapped_column(String(100), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    channels: Mapped[list["Channel"]] = relationship("Channel", back_populates="session")

class DigestHistory(Base):
    __tablename__ = "digest_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    period_hours: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="digest_history")

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User")

class AIUsageStat(Base):
    __tablename__ = "ai_usage_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(50), index=True) # groq, mistral, gemini
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    is_success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

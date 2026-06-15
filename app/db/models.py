from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    TIMESTAMP,
    BigInteger,
    Boolean,
    ForeignKey,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Log(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )


class ExtractedFacts(Base):
    __tablename__ = "extracted_facts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    log_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("logs.id"), nullable=False, unique=True
    )
    habits: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    adherence: Mapped[str | None] = mapped_column(Text, nullable=True)
    mood: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )


class HabitCategory(Base):
    __tablename__ = "habit_categories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    __table_args__ = (UniqueConstraint("telegram_user_id", "name"),)


class HabitPlan(Base):
    __tablename__ = "habit_plans"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    category_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("habit_categories.id"), nullable=False
    )
    habit_name: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    cadence_type: Mapped[str] = mapped_column(Text, nullable=False)
    cadence_value: Mapped[object | None] = mapped_column(JSON, nullable=True)
    success_condition: Mapped[str] = mapped_column(Text, nullable=False)
    habit_aliases: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    known_triggers: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    fallback_checkin_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expected_evidence_window: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    __table_args__ = (UniqueConstraint("telegram_user_id", "habit_name"),)


class CorpusChunk(Base):
    __tablename__ = "corpus_chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )


class UserProgress(Base):
    __tablename__ = "user_progress"

    telegram_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    xp: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    level: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class HabitProgress(Base):
    __tablename__ = "habit_progress"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    habit_name: Mapped[str] = mapped_column(Text, nullable=False)
    xp: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    level: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    __table_args__ = (UniqueConstraint("telegram_user_id", "habit_name"),)


class Intervention(Base):
    __tablename__ = "interventions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # 'proactive' | 'silence' | 'check-in'
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    technique: Mapped[str | None] = mapped_column(Text, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    engaged: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

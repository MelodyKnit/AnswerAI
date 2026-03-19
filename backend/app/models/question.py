from datetime import datetime

from sqlalchemy import Float, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, utcnow


class Question(Base, TimestampMixin):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    type: Mapped[str] = mapped_column(String(30), index=True)
    stem: Mapped[str] = mapped_column(Text)
    answer_text: Mapped[str] = mapped_column(Text)
    analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    difficulty: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(50), default="manual", index=True)
    quality_status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    ai_review_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class QuestionOption(Base):
    __tablename__ = "question_options"
    __table_args__ = (UniqueConstraint("question_id", "option_key", name="uq_question_option"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    option_key: Mapped[str] = mapped_column(String(10))
    content: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

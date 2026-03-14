from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, utcnow


class Exam(Base, TimestampMixin):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    total_score: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    allow_review: Mapped[bool] = mapped_column(Boolean, default=True)
    random_question_order: Mapped[bool] = mapped_column(Boolean, default=False)
    start_time: Mapped[datetime] = mapped_column(index=True)
    end_time: Mapped[datetime] = mapped_column(index=True)
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    ai_evaluation_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ExamQuestion(Base):
    __tablename__ = "exam_questions"
    __table_args__ = (
        UniqueConstraint("exam_id", "question_id", name="uq_exam_question"),
        UniqueConstraint("exam_id", "order_no", name="uq_exam_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    score: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    order_no: Mapped[int] = mapped_column(Integer, index=True)
    section_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class ExamClass(Base):
    __tablename__ = "exam_classes"
    __table_args__ = (UniqueConstraint("exam_id", "class_id", name="uq_exam_class"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class ExamSubmission(Base, TimestampMixin):
    __tablename__ = "exam_submissions"
    __table_args__ = (UniqueConstraint("exam_id", "student_id", name="uq_exam_student_submission"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="not_started", index=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    deadline_at: Mapped[datetime | None] = mapped_column(nullable=True)
    objective_score: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    subjective_score: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    total_score: Mapped[float] = mapped_column(Numeric(10, 2), default=0, index=True)
    correct_rate: Mapped[float] = mapped_column(Float, default=0)
    ranking_in_class: Mapped[int | None] = mapped_column(Integer, nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    ai_analysis_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)


class SubmissionAnswer(Base, TimestampMixin):
    __tablename__ = "submission_answers"
    __table_args__ = (UniqueConstraint("submission_id", "question_id", name="uq_submission_question_answer"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("exam_submissions.id"), index=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    answer_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(nullable=True, index=True)
    score: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    spent_seconds: Mapped[int] = mapped_column(Integer, default=0)
    answer_version: Mapped[int] = mapped_column(Integer, default=1)
    mark_difficult: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    ai_error_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class SubmissionBehaviorEvent(Base):
    __tablename__ = "submission_behavior_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("exam_submissions.id"), index=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    question_id: Mapped[int | None] = mapped_column(ForeignKey("questions.id"), index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, utcnow


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    school_name: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    grade_name: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)


class ReviewItem(Base):
    __tablename__ = "review_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("exam_submissions.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    ai_suggest_score: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    final_score: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    ai_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    teacher_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class ReviewLog(Base):
    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_item_id: Mapped[int] = mapped_column(ForeignKey("review_items.id"), index=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    old_score: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    new_score: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class AITask(Base, TimestampMixin):
    __tablename__ = "ai_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    resource_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    request_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)


class AIChatSession(Base, TimestampMixin):
    __tablename__ = "ai_chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    exam_id: Mapped[int | None] = mapped_column(ForeignKey("exams.id"), nullable=True, index=True)
    question_id: Mapped[int | None] = mapped_column(ForeignKey("questions.id"), nullable=True, index=True)
    mode: Mapped[str] = mapped_column(String(50), index=True)
    context_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)


class AIChatMessage(Base):
    __tablename__ = "ai_chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("ai_chat_sessions.id"), index=True)
    sender_role: Mapped[str] = mapped_column(String(20), index=True)
    message_type: Mapped[str] = mapped_column(String(30), default="text", index=True)
    content: Mapped[str] = mapped_column(Text)
    extra_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class StudyPlan(Base, TimestampMixin):
    __tablename__ = "study_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    source_exam_id: Mapped[int | None] = mapped_column(ForeignKey("exams.id"), nullable=True, index=True)
    plan_type: Mapped[str] = mapped_column(String(30), index=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    ai_generation_task_id: Mapped[int | None] = mapped_column(ForeignKey("ai_tasks.id"), nullable=True, index=True)
    start_date: Mapped[datetime | None] = mapped_column(nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(nullable=True)


class StudyTask(Base):
    __tablename__ = "study_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("study_plans.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    task_type: Mapped[str] = mapped_column(String(50), index=True)
    knowledge_point_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_points.id"), nullable=True, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, index=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_type: Mapped[str] = mapped_column(String(30), index=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    exam_id: Mapped[int | None] = mapped_column(ForeignKey("exams.id"), nullable=True, index=True)
    class_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id"), nullable=True, index=True)
    student_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="generating", index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    generated_by_task_id: Mapped[int | None] = mapped_column(ForeignKey("ai_tasks.id"), nullable=True, index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)


class StudentProfileSnapshot(Base):
    __tablename__ = "student_profile_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    source_exam_id: Mapped[int | None] = mapped_column(ForeignKey("exams.id"), nullable=True, index=True)
    profile_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class ClassAnalysisSnapshot(Base):
    __tablename__ = "class_analysis_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), index=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    analysis_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class KnowledgeMasterySnapshot(Base):
    __tablename__ = "knowledge_mastery_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_type: Mapped[str] = mapped_column(String(20), index=True)
    owner_id: Mapped[int] = mapped_column(index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    knowledge_point_id: Mapped[int] = mapped_column(ForeignKey("knowledge_points.id"), index=True)
    mastery_score: Mapped[float] = mapped_column(Float, default=0, index=True)
    wrong_count: Mapped[int] = mapped_column(Integer, default=0)
    source_exam_id: Mapped[int | None] = mapped_column(ForeignKey("exams.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
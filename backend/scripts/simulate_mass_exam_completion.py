from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Iterable

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.academic import ClassStudent
from app.models.exam import Exam, ExamClass, ExamQuestion, ExamSubmission, SubmissionAnswer
from app.models.question import Question
from app.models.user import ReviewItem, User


SUBJECTIVE_TYPES = {"essay", "short_answer", "material"}


@dataclass
class Counters:
    submissions_created: int = 0
    submissions_updated: int = 0
    answers_created: int = 0
    answers_updated: int = 0
    review_items_marked: int = 0
    class_links_created: int = 0


def _f(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _parse_student_no(username: str) -> int:
    suffix = ""
    for ch in reversed(username):
        if ch.isdigit():
            suffix = ch + suffix
        else:
            break
    return int(suffix) if suffix else 10**9


def _pick_score_for_bucket(bucket: str) -> float:
    if bucket == "high":
        return float(random.randint(30, 44))
    if bucket == "warning":
        return float(random.randint(45, 59))
    return float(random.randint(65, 95))


def _pick_correct_rate_for_bucket(bucket: str) -> float:
    if bucket == "high":
        return round(random.uniform(0.30, 0.44), 2)
    if bucket == "warning":
        return round(random.uniform(0.45, 0.59), 2)
    return round(random.uniform(0.65, 0.93), 2)


def _student_bucket(index: int, high_risk: int, warning: int) -> str:
    if index < high_risk:
        return "high"
    if index < high_risk + warning:
        return "warning"
    return "normal"


def _ensure_class_link(db: Session, class_id: int, teacher_id: int, student_id: int) -> bool:
    existing = db.scalar(
        select(ClassStudent).where(
            and_(ClassStudent.class_id == class_id, ClassStudent.student_id == student_id)
        )
    )
    if existing:
        if existing.status != "active":
            existing.status = "active"
            db.add(existing)
        return False

    db.add(
        ClassStudent(
            class_id=class_id,
            student_id=student_id,
            teacher_id=teacher_id,
            status="active",
        )
    )
    return True


def _upsert_answer(
    db: Session,
    submission_id: int,
    exam_id: int,
    question_id: int,
    answer_content: str | None,
    answer_text: str | None,
    is_correct: bool,
    score: float,
    spent_seconds: int,
    counters: Counters,
) -> None:
    answer = db.scalar(
        select(SubmissionAnswer).where(
            and_(SubmissionAnswer.submission_id == submission_id, SubmissionAnswer.question_id == question_id)
        )
    )

    if answer is None:
        db.add(
            SubmissionAnswer(
                submission_id=submission_id,
                exam_id=exam_id,
                question_id=question_id,
                answer_content=answer_content,
                answer_text=answer_text,
                is_correct=is_correct,
                score=score,
                spent_seconds=spent_seconds,
                answer_version=1,
                mark_difficult=False,
                favorite=False,
            )
        )
        counters.answers_created += 1
        return

    answer.answer_content = answer_content
    answer.answer_text = answer_text
    answer.is_correct = is_correct
    answer.score = score
    answer.spent_seconds = spent_seconds
    answer.answer_version = int(answer.answer_version or 0) + 1
    db.add(answer)
    counters.answers_updated += 1


def _build_exam_map(db: Session, exam_ids: Iterable[int]) -> dict[int, list[tuple[ExamQuestion, Question]]]:
    items: dict[int, list[tuple[ExamQuestion, Question]]] = {}
    rows = db.execute(
        select(ExamQuestion, Question)
        .join(Question, Question.id == ExamQuestion.question_id)
        .where(ExamQuestion.exam_id.in_(list(exam_ids)))
        .order_by(ExamQuestion.exam_id.asc(), ExamQuestion.order_no.asc())
    ).all()
    for eq, q in rows:
        items.setdefault(eq.exam_id, []).append((eq, q))
    return items


def _calc_latest_risk_distribution(db: Session, teacher_exam_ids: list[int]) -> dict[str, int]:
    if not teacher_exam_ids:
        return {"high": 0, "warning": 0, "normal": 0}

    subs = db.scalars(
        select(ExamSubmission)
        .where(ExamSubmission.exam_id.in_(teacher_exam_ids))
        .where(ExamSubmission.status.in_(["submitted", "completed", "reviewed"]))
        .order_by(ExamSubmission.submitted_at.desc(), ExamSubmission.created_at.desc())
    ).all()

    latest_by_student: dict[int, ExamSubmission] = {}
    for sub in subs:
        sid = int(sub.student_id)
        if sid in latest_by_student:
            continue
        latest_by_student[sid] = sub

    counts = {"high": 0, "warning": 0, "normal": 0}
    for sub in latest_by_student.values():
        score = _f(sub.total_score)
        rate = float(sub.correct_rate or 0)
        if score < 45 or rate < 0.45:
            counts["high"] += 1
        elif score < 60 or rate < 0.6:
            counts["warning"] += 1
        else:
            counts["normal"] += 1
    return counts


def run(
    teacher_email: str,
    student_prefix: str,
    student_count: int,
    high_risk: int,
    warning: int,
    seed: int,
) -> None:
    if high_risk < 0 or warning < 0:
        raise ValueError("high_risk and warning must be >= 0")
    if high_risk > 5:
        raise ValueError("high_risk must be <= 5")
    if warning > 10:
        raise ValueError("warning must be <= 10")
    if high_risk + warning > student_count:
        raise ValueError("high_risk + warning cannot exceed student_count")

    random.seed(seed)
    counters = Counters()

    with SessionLocal() as db:
        teacher = db.scalar(
            select(User).where(and_(User.email == teacher_email, User.role == "teacher"))
        )
        if teacher is None:
            raise RuntimeError(f"Teacher not found: {teacher_email}")

        requested_usernames = [f"{student_prefix}{i}" for i in range(1, student_count + 1)]
        students = db.scalars(
            select(User)
            .where(and_(User.role == "student", User.username.in_(requested_usernames)))
            .order_by(User.username.asc())
        ).all()
        students = sorted(students, key=lambda s: _parse_student_no(s.username or ""))

        if len(students) != student_count:
            found = {s.username for s in students}
            missing = [u for u in requested_usernames if u not in found]
            raise RuntimeError(f"Missing students: {missing}")

        exams = db.scalars(
            select(Exam)
            .where(Exam.created_by == teacher.id)
            .where(Exam.status.in_(["published", "finished", "draft"]))
            .order_by(Exam.created_at.asc())
        ).all()

        if not exams:
            raise RuntimeError("No exams found for teacher")

        exam_ids = [int(e.id) for e in exams]
        question_map = _build_exam_map(db, exam_ids)

        valid_exams = [e for e in exams if question_map.get(e.id)]
        if not valid_exams:
            raise RuntimeError("Teacher exams have no questions")

        latest_exam = valid_exams[-1]
        now = datetime.now(UTC).replace(tzinfo=None)

        exam_class_rows = db.execute(
            select(ExamClass.exam_id, ExamClass.class_id).where(ExamClass.exam_id.in_(exam_ids))
        ).all()
        exam_classes: dict[int, list[int]] = {}
        for row in exam_class_rows:
            exam_classes.setdefault(int(row.exam_id), []).append(int(row.class_id))

        for exam_index, exam in enumerate(valid_exams):
            eq_pairs = question_map[exam.id]
            total_question_score = sum(_f(eq.score) for eq, _ in eq_pairs)
            exam_class_ids = exam_classes.get(exam.id, [])
            if not exam_class_ids:
                continue

            base_submitted_at = now - timedelta(days=(len(valid_exams) - exam_index + 1))
            if exam.id == latest_exam.id:
                base_submitted_at = now + timedelta(minutes=1)

            for student_index, student in enumerate(students):
                bucket = _student_bucket(student_index, high_risk, warning)

                target_score = _pick_score_for_bucket(bucket) if exam.id == latest_exam.id else float(random.randint(62, 96))
                target_correct_rate = _pick_correct_rate_for_bucket(bucket) if exam.id == latest_exam.id else round(random.uniform(0.62, 0.95), 2)

                if exam.id != latest_exam.id and total_question_score > 0:
                    target_score = min(target_score, max(total_question_score, target_score))

                class_id = exam_class_ids[student_index % len(exam_class_ids)]
                if _ensure_class_link(db, class_id, teacher.id, student.id):
                    counters.class_links_created += 1

                submission = db.scalar(
                    select(ExamSubmission).where(
                        and_(ExamSubmission.exam_id == exam.id, ExamSubmission.student_id == student.id)
                    )
                )
                if submission is None:
                    submission = ExamSubmission(
                        exam_id=exam.id,
                        student_id=student.id,
                        class_id=class_id,
                        teacher_id=teacher.id,
                    )
                    db.add(submission)
                    db.flush()
                    counters.submissions_created += 1
                else:
                    counters.submissions_updated += 1

                submission.class_id = class_id
                submission.teacher_id = teacher.id
                submission.status = "completed"
                submission.review_status = "completed"
                submission.ai_analysis_status = "completed"
                submission.started_at = base_submitted_at - timedelta(minutes=max(5, int(exam.duration_minutes * 0.6)))
                submission.submitted_at = base_submitted_at + timedelta(seconds=student_index)
                submission.deadline_at = submission.started_at + timedelta(minutes=max(exam.duration_minutes, 5))

                answer_count = len(eq_pairs)
                correct_count = max(0, min(answer_count, int(round(answer_count * target_correct_rate))))
                correct_indexes = set(random.sample(range(answer_count), k=correct_count)) if answer_count > 0 else set()

                obj_total = 0.0
                sub_total = 0.0

                for idx, (eq, q) in enumerate(eq_pairs):
                    is_correct = idx in correct_indexes
                    question_score = _f(eq.score)
                    gained_score = question_score if is_correct else 0.0

                    q_type = str(q.type or "").lower()
                    if q_type in SUBJECTIVE_TYPES:
                        sub_total += gained_score
                        answer_content = None
                        answer_text = q.answer_text if is_correct else "(simulated)"
                    else:
                        obj_total += gained_score
                        answer_content = q.answer_text if is_correct else json.dumps(["X"], ensure_ascii=False)
                        answer_text = None

                    _upsert_answer(
                        db=db,
                        submission_id=submission.id,
                        exam_id=exam.id,
                        question_id=q.id,
                        answer_content=answer_content,
                        answer_text=answer_text,
                        is_correct=is_correct,
                        score=round(gained_score, 2),
                        spent_seconds=random.randint(20, 180),
                        counters=counters,
                    )

                if exam.id == latest_exam.id:
                    submission.total_score = round(target_score, 2)
                else:
                    submission.total_score = round(obj_total + sub_total, 2)

                submission.correct_rate = float(target_correct_rate)

                scored_total = obj_total + sub_total
                if scored_total > 0:
                    ratio_obj = obj_total / scored_total
                    submission.objective_score = round(_f(submission.total_score) * ratio_obj, 2)
                else:
                    submission.objective_score = 0
                submission.subjective_score = round(_f(submission.total_score) - _f(submission.objective_score), 2)
                submission.ranking_in_class = None

                db.add(submission)

                review_items = db.scalars(
                    select(ReviewItem).where(ReviewItem.submission_id == submission.id)
                ).all()
                for item in review_items:
                    item.review_status = "reviewed"
                    item.final_score = item.final_score if item.final_score is not None else item.ai_suggest_score
                    item.reviewed_by = teacher.id
                    item.reviewed_at = submission.submitted_at
                    db.add(item)
                    counters.review_items_marked += 1

        db.commit()

        risk = _calc_latest_risk_distribution(db, exam_ids)
        print("Simulation completed")
        print(f"teacher={teacher.email} exams={len(valid_exams)} students={len(students)}")
        print(
            "submissions created/updated="
            f"{counters.submissions_created}/{counters.submissions_updated}"
        )
        print(
            "answers created/updated="
            f"{counters.answers_created}/{counters.answers_updated}"
        )
        print(f"review items marked reviewed={counters.review_items_marked}")
        print(f"class links created={counters.class_links_created}")
        print(
            "latest-risk-distribution "
            f"high={risk['high']} warning={risk['warning']} normal={risk['normal']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate mass exam completion for a teacher's students."
    )
    parser.add_argument("--teacher-email", required=True)
    parser.add_argument("--student-prefix", default="student")
    parser.add_argument("--student-count", type=int, default=59)
    parser.add_argument("--high-risk", type=int, default=5)
    parser.add_argument("--warning", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260319)
    args = parser.parse_args()

    run(
        teacher_email=args.teacher_email,
        student_prefix=args.student_prefix,
        student_count=args.student_count,
        high_risk=args.high_risk,
        warning=args.warning,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()

import json
import re
from datetime import datetime, UTC, timedelta
from uuid import uuid4
from random import Random
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.core.response import success_response
from app.models.academic import ClassRoom, ClassStudent, KnowledgePoint, Subject
from app.models.exam import Exam, ExamClass, ExamQuestion, ExamSubmission, SubmissionAnswer, SubmissionBehaviorEvent
from app.models.question import Question, QuestionKnowledgePoint, QuestionOption
from app.models.user import AITask, ReviewItem, ReviewLog, StudentProfileSnapshot, StudyPlan, StudyTask, User
from app.schemas.teacher import AIExamAssembleRequest, AIQuestionGenerateRequest, AIQuestionReviewRequest, AIScoreRequest, ClassCreateRequest, ClassInviteRequest, DeleteRequest, ExamActionRequest, ExamCreateRequest, ExamUpdateRequest, ImportQuestionsRequest, QuestionCreateRequest, QuestionUpdateRequest, RetakeRequestActionRequest, ReviewSubmitRequest
from app.services.student_growth_ai import build_growth_ability_profile
from app.services.realtime import realtime_events, submission_channel
from app.services.llm import generate_questions_with_llm
from app.services.scoring import SUBJECTIVE_TYPES, serialize_answer
from app.services.tasks import complete_ai_task, create_ai_task, mark_ai_task_running, queue_ai_task


router = APIRouter()


def _to_utc_aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _to_utc_naive(value: datetime) -> datetime:
    return _to_utc_aware(value).astimezone(UTC).replace(tzinfo=None)


def _normalize_exam_window(start_time: datetime, end_time: datetime, duration_minutes: int, publish_now: bool) -> tuple[datetime, datetime]:
    start_aware = _to_utc_aware(start_time)
    end_aware = _to_utc_aware(end_time)

    if publish_now:
        now_utc = datetime.now(UTC)
        if end_aware <= now_utc or start_aware >= end_aware:
            start_aware = now_utc
            end_aware = now_utc + timedelta(minutes=max(int(duration_minutes or 60), 1))
    elif start_aware >= end_aware:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam end time must be later than start time")

    return _to_utc_naive(start_aware), _to_utc_naive(end_aware)


@router.get("/teacher/dashboard/overview")
def get_teacher_dashboard_overview(
    subject: str | None = None,
    current_user: User = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    """
    获取 teacher dashboard overview 相关数据。
    """
    exam_query = select(Exam.id).where(Exam.created_by == current_user.id)
    if subject:
        subject_obj = db.scalar(select(Subject).where(Subject.name == subject))
        if subject_obj is None:
            return success_response(
                {
                    "exam_count": 0,
                    "pending_review_count": 0,
                    "risk_student_count": 0,
                    "avg_score_trend": [],
                    "ai_class_summary": "当前学科下暂无考试数据。",
                    "risk_students": [],
                }
            )
        exam_query = exam_query.where(Exam.subject_id == subject_obj.id)

    exam_ids = list(db.scalars(exam_query).all())
    if not exam_ids:
        return success_response(
            {
                "exam_count": 0,
                "pending_review_count": 0,
                "risk_student_count": 0,
                "avg_score_trend": [],
                "ai_class_summary": "当前暂无考试数据，建议先创建并发布考试。",
                "risk_students": [],
            }
        )

    pending_review_count = db.scalar(
        select(func.count()).select_from(ReviewItem).where(ReviewItem.exam_id.in_(exam_ids), ReviewItem.review_status == "pending")
    ) or 0

    risk_submissions = db.scalars(
        select(ExamSubmission)
        .where(ExamSubmission.exam_id.in_(exam_ids))
        .where(ExamSubmission.status.in_(["submitted", "completed", "reviewed"]))
        .order_by(ExamSubmission.submitted_at.desc(), ExamSubmission.created_at.desc())
    ).all()

    latest_submission_by_student: dict[int, ExamSubmission] = {}
    for submission in risk_submissions:
        student_id = int(submission.student_id)
        if student_id in latest_submission_by_student:
            continue
        latest_submission_by_student[student_id] = submission

    ability_suggestion_map = {
        "审题能力": "先带学生口述题意和关键词，再下笔作答，降低读题偏差。",
        "知识迁移能力": "每次讲评后补 2 道同知识点变式题，强化迁移应用。",
        "稳定作答能力": "训练固定答题节奏（先易后难），并限制单题停留时间。",
    }

    risk_students: list[dict[str, Any]] = []
    for student_id, submission in latest_submission_by_student.items():
        latest_score = float(submission.total_score or 0)
        correct_rate = float(submission.correct_rate or 0)
        if latest_score >= 60 and correct_rate >= 0.6:
            continue

        if latest_score < 45 or correct_rate < 0.45:
            risk_level = "high"
        elif latest_score < 60 or correct_rate < 0.6:
            risk_level = "medium"
        else:
            risk_level = "low"

        student = db.get(User, student_id)
        exam = db.get(Exam, submission.exam_id)
        class_obj = db.get(ClassRoom, submission.class_id) if submission.class_id else None

        snapshot = db.scalar(
            select(StudentProfileSnapshot)
            .where(
                StudentProfileSnapshot.student_id == student_id,
                StudentProfileSnapshot.source_exam_id.in_(exam_ids),
            )
            .order_by(StudentProfileSnapshot.created_at.desc())
            .limit(1)
        )
        profile_json = snapshot.profile_json if snapshot and isinstance(snapshot.profile_json, dict) else {}
        weak_points = profile_json.get("weak_knowledge_points") or []
        weak_point_names = [str(item.get("name") or "").strip() for item in weak_points if item.get("name")]
        weak_point_names = [name for name in weak_point_names if name][:3]

        weak_abilities: list[str] = []
        wrong_count = int(profile_json.get("wrong_question_count") or 0)
        total_questions = int(profile_json.get("total_questions") or 0)
        if total_questions > 0 and wrong_count / max(total_questions, 1) >= 0.5:
            weak_abilities.append("审题能力")
        if latest_score < 60:
            weak_abilities.append("稳定作答能力")
        if correct_rate < 0.6 or len(weak_point_names) >= 2:
            weak_abilities.append("知识迁移能力")
        if not weak_abilities:
            weak_abilities.append("审题能力")

        # 去重保序
        seen_ability: set[str] = set()
        weak_abilities = [ability for ability in weak_abilities if not (ability in seen_ability or seen_ability.add(ability))][:3]

        coaching_suggestions: list[str] = []
        if weak_point_names:
            coaching_suggestions.append(f"围绕 {weak_point_names[0]} 做“讲 1 题 + 练 2 题 + 复盘 1 题”微循环训练。")
        for ability in weak_abilities:
            suggestion = ability_suggestion_map.get(ability)
            if suggestion:
                coaching_suggestions.append(suggestion)
        if not coaching_suggestions:
            coaching_suggestions.append("建议先进行 15 分钟错因复盘，再安排 20 分钟针对训练。")

        seen_suggestion: set[str] = set()
        coaching_suggestions = [text for text in coaching_suggestions if not (text in seen_suggestion or seen_suggestion.add(text))][:3]

        risk_students.append(
            {
                "student_id": student_id,
                "student_name": student.name if student else f"学生#{student_id}",
                "class_name": class_obj.name if class_obj else None,
                "exam_id": submission.exam_id,
                "exam_title": exam.title if exam else None,
                "latest_score": round(latest_score, 1),
                "correct_rate": round(correct_rate, 2),
                "risk_level": risk_level,
                "weak_abilities": weak_abilities,
                "weak_knowledge_points": weak_point_names,
                "coaching_suggestions": coaching_suggestions,
            }
        )

    risk_students.sort(key=lambda item: (0 if item["risk_level"] == "high" else 1, item["latest_score"]))
    risk_students = risk_students[:12]
    risk_student_count = len(risk_students)

    trend_rows = db.execute(
        select(
            ExamSubmission.exam_id,
            func.avg(ExamSubmission.total_score).label("avg_score"),
            func.max(ExamSubmission.submitted_at).label("latest_submitted_at"),
        )
        .where(ExamSubmission.exam_id.in_(exam_ids))
        .group_by(ExamSubmission.exam_id)
        .order_by(func.max(ExamSubmission.submitted_at).desc())
        .limit(6)
    ).all()

    avg_score_trend = [{"exam_id": row.exam_id, "avg_score": round(float(row.avg_score or 0), 2)} for row in reversed(trend_rows)]

    return success_response(
        {
            "exam_count": len(exam_ids),
            "pending_review_count": pending_review_count,
            "risk_student_count": risk_student_count,
            "avg_score_trend": avg_score_trend,
            "ai_class_summary": f"已创建 {len(exam_ids)} 场考试，当前待批阅 {pending_review_count} 份，风险学生 {risk_student_count} 人。",
            "risk_students": risk_students,
        }
    )


@router.get("/teacher/feedback/list")
def list_user_feedback(
    category: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    """
    教师端查看用户功能反馈列表，支持按类型筛选、关键词筛选与分页。
    """
    del current_user
    safe_category = (category or "").strip().lower()
    if safe_category and safe_category not in {"bug", "product", "design", "other"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid category")

    safe_keyword = (keyword or "").strip().lower()

    records = db.scalars(
        select(AITask)
        .where(AITask.type == "user_feedback")
        .order_by(AITask.created_at.desc())
        .limit(1000)
    ).all()

    filtered: list[dict[str, Any]] = []
    for task in records:
        payload = task.request_payload if isinstance(task.request_payload, dict) else {}
        item_category = str(payload.get("category") or "other").strip().lower()
        if item_category not in {"bug", "product", "design", "other"}:
            item_category = "other"

        content = str(payload.get("content") or "").strip()
        page_path = str(payload.get("page_path") or "").strip() or None
        client_role = str(payload.get("client_role") or "").strip() or None
        client_name = str(payload.get("client_name") or "").strip() or None
        client_email = str(payload.get("client_email") or "").strip() or None

        if safe_category and item_category != safe_category:
            continue

        if safe_keyword:
            target_text = " ".join(
                [
                    content.lower(),
                    (page_path or "").lower(),
                    (client_name or "").lower(),
                    (client_email or "").lower(),
                ]
            )
            if safe_keyword not in target_text:
                continue

        raw_images = payload.get("images")
        images: list[str] = []
        if isinstance(raw_images, list):
            for raw in raw_images:
                item = str(raw or "").strip()
                if item:
                    images.append(item)

        filtered.append(
            {
                "id": task.id,
                "category": item_category,
                "content": content,
                "images": images,
                "page_path": page_path,
                "client_role": client_role,
                "client_name": client_name,
                "client_email": client_email,
                "created_at": task.created_at.isoformat(),
            }
        )

    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    items = filtered[start:end]

    summary = {
        "bug": sum(1 for row in filtered if row["category"] == "bug"),
        "product": sum(1 for row in filtered if row["category"] == "product"),
        "design": sum(1 for row in filtered if row["category"] == "design"),
        "other": sum(1 for row in filtered if row["category"] == "other"),
    }

    return success_response({"items": items, "total": total, "summary": summary, "page": page, "page_size": page_size})


@router.get("/teacher/classes")
def list_classes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    """
    列出 classes 的数据列表。
    """
    query = select(ClassRoom).where(ClassRoom.teacher_id == current_user.id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return success_response(
        {
            "items": [_serialize_class(item) for item in items],
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        }
    )


@router.post("/teacher/classes/create")
def create_class(payload: ClassCreateRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    创建新的 class 记录。
    """
    invite_code = f"CLS-{uuid4().hex[:6].upper()}"
    classroom = ClassRoom(
        teacher_id=current_user.id,
        name=payload.name,
        grade_name=payload.grade_name,
        subject=payload.subject,
        invite_code=invite_code,
        student_count=0,
        status="active",
    )
    db.add(classroom)
    db.commit()
    db.refresh(classroom)
    return success_response({"class": _serialize_class(classroom)}, "class created")


@router.get("/teacher/classes/detail")
def get_class_detail(class_id: int, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    获取 class detail 相关数据。
    """
    classroom = _get_teacher_class(db, current_user.id, class_id)
    exam_count = db.scalar(
        select(func.count()).select_from(ExamClass).join(Exam, Exam.id == ExamClass.exam_id).where(ExamClass.class_id == class_id, Exam.created_by == current_user.id)
    ) or 0
    return success_response({"class": _serialize_class(classroom), "recent_exam_count": exam_count, "student_count": classroom.student_count})


@router.get("/teacher/classes/students")
def get_class_students(
    class_id: int,
    keyword: str | None = None,
    risk_level: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    """
    获取 class students 相关数据。
    """
    _get_teacher_class(db, current_user.id, class_id)
    query = select(User).join(ClassStudent, ClassStudent.student_id == User.id).where(ClassStudent.class_id == class_id, ClassStudent.status == "active")
    if keyword:
        query = query.where(User.name.contains(keyword))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    serialized = []
    for item in items:
        serialized.append({
            "id": item.id,
            "name": item.name,
            "email": item.email,
            "phone": item.phone,
            "grade_name": item.grade_name,
            "risk_level": risk_level or "unknown",
        })
    return success_response({"items": serialized, "total": total})


@router.post("/teacher/classes/students/invite")
def invite_student_to_class(payload: ClassInviteRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    处理 invite student to class 请求并返回结果。
    """
    classroom = _get_teacher_class(db, current_user.id, payload.class_id)

    student = db.get(User, payload.student_id)
    if not student or student.role != "student":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    relation = db.scalar(
        select(ClassStudent).where(
            ClassStudent.class_id == classroom.id,
            ClassStudent.student_id == student.id,
            ClassStudent.teacher_id == current_user.id,
        )
    )

    if relation and relation.status == "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student already in class")

    if relation and relation.status != "active":
        relation.status = "active"
        db.add(relation)
    else:
        db.add(
            ClassStudent(
                class_id=classroom.id,
                student_id=student.id,
                teacher_id=current_user.id,
                status="active",
            )
        )

    active_count = db.scalar(
        select(func.count()).select_from(ClassStudent).where(
            ClassStudent.class_id == classroom.id,
            ClassStudent.status == "active",
        )
    ) or 0
    classroom.student_count = int(active_count) + 1
    db.add(classroom)
    db.commit()

    return success_response(
        {
            "class_id": classroom.id,
            "student": {
                "id": student.id,
                "name": student.name,
                "email": student.email,
                "phone": student.phone,
            },
            "student_count": classroom.student_count,
        },
        "student invited",
    )


@router.post("/teacher/classes/students/remove")
def remove_student_from_class(payload: ClassInviteRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    处理 remove student from class 请求并返回结果。
    """
    classroom = _get_teacher_class(db, current_user.id, payload.class_id)

    relation = db.scalar(
        select(ClassStudent).where(
            ClassStudent.class_id == classroom.id,
            ClassStudent.student_id == payload.student_id,
            ClassStudent.teacher_id == current_user.id,
            ClassStudent.status == "active",
        )
    )
    if not relation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student is not in this class")

    relation.status = "inactive"
    db.add(relation)

    active_count = db.scalar(
        select(func.count()).select_from(ClassStudent).where(
            ClassStudent.class_id == classroom.id,
            ClassStudent.status == "active",
        )
    ) or 0
    classroom.student_count = max(0, int(active_count) - 1)
    db.add(classroom)

    db.commit()
    return success_response(
        {
            "class_id": classroom.id,
            "student_id": payload.student_id,
            "student_count": classroom.student_count,
        },
        "student removed",
    )


@router.get("/teacher/students/detail")
def get_student_detail(student_id: int, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    获取 student detail 相关数据。
    """
    student = db.get(User, student_id)
    if not student or student.role != "student":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    relation = db.scalar(select(ClassStudent).where(ClassStudent.student_id == student_id, ClassStudent.teacher_id == current_user.id, ClassStudent.status == "active"))
    if not relation:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission for this student")
    classroom = db.get(ClassRoom, relation.class_id)
    submissions = db.scalars(
        select(ExamSubmission)
        .where(
            ExamSubmission.student_id == student_id,
            ExamSubmission.teacher_id == current_user.id,
            ExamSubmission.status.in_(["submitted", "completed", "reviewed"]),
        )
        .order_by(ExamSubmission.submitted_at.asc(), ExamSubmission.created_at.asc())
    ).all()
    latest_submission = submissions[-1] if submissions else None

    exam_ids = [item.exam_id for item in submissions]
    answer_records: list[dict[str, Any]] = []
    if exam_ids:
        answer_rows = db.execute(
            select(SubmissionAnswer, Question, Subject)
            .join(ExamSubmission, SubmissionAnswer.submission_id == ExamSubmission.id)
            .join(Question, SubmissionAnswer.question_id == Question.id)
            .outerjoin(Subject, Question.subject_id == Subject.id)
            .where(
                ExamSubmission.student_id == student_id,
                ExamSubmission.teacher_id == current_user.id,
                ExamSubmission.exam_id.in_(exam_ids),
            )
        ).all()
        answer_records = [
            {
                "subject": subject_obj.name if subject_obj else None,
                "question_type": question.type,
                "stem": question.stem,
                "analysis": question.analysis,
                "is_correct": answer.is_correct,
            }
            for answer, question, subject_obj in answer_rows
        ]

    growth_profile = build_growth_ability_profile(answer_records)

    trend: list[dict[str, Any]] = []
    recent_submissions = submissions[-8:]
    for submission in recent_submissions:
        exam = db.get(Exam, submission.exam_id)
        class_avg = db.scalar(
            select(func.avg(ExamSubmission.total_score)).where(
                ExamSubmission.exam_id == submission.exam_id,
                ExamSubmission.status.in_(["submitted", "completed", "reviewed"]),
            )
        ) or 0
        trend.append(
            {
                "exam_id": submission.exam_id,
                "exam_title": exam.title if exam else f"考试#{submission.exam_id}",
                "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else submission.created_at.isoformat(),
                "score": round(float(submission.total_score or 0), 1),
                "correct_rate": round(float(submission.correct_rate or 0), 2),
                "class_avg": round(float(class_avg or 0), 1),
                "ranking_in_class": submission.ranking_in_class,
            }
        )

    knowledge_rows = db.execute(
        select(
            KnowledgePoint.id,
            KnowledgePoint.name,
            func.count(SubmissionAnswer.id).label("question_count"),
            func.sum(case((SubmissionAnswer.is_correct == True, 1), else_=0)).label("correct_count"),
            func.sum(case((SubmissionAnswer.is_correct == False, 1), else_=0)).label("wrong_count"),
        )
        .select_from(SubmissionAnswer)
        .join(ExamSubmission, SubmissionAnswer.submission_id == ExamSubmission.id)
        .join(QuestionKnowledgePoint, QuestionKnowledgePoint.question_id == SubmissionAnswer.question_id)
        .join(KnowledgePoint, KnowledgePoint.id == QuestionKnowledgePoint.knowledge_point_id)
        .where(
            ExamSubmission.student_id == student_id,
            ExamSubmission.teacher_id == current_user.id,
            ExamSubmission.status.in_(["submitted", "completed", "reviewed"]),
        )
        .group_by(KnowledgePoint.id, KnowledgePoint.name)
        .order_by(
            func.sum(case((SubmissionAnswer.is_correct == False, 1), else_=0)).desc(),
            func.count(SubmissionAnswer.id).desc(),
        )
        .limit(8)
    ).all()
    knowledge_points = [
        {
            "id": row.id,
            "name": row.name,
            "question_count": int(row.question_count or 0),
            "wrong_count": int(row.wrong_count or 0),
            "mastery": round((float(row.correct_count or 0) / max(1, int(row.question_count or 0))), 2),
        }
        for row in knowledge_rows
    ]

    question_type_rows = db.execute(
        select(
            Question.type,
            func.count(SubmissionAnswer.id).label("question_count"),
            func.sum(case((SubmissionAnswer.is_correct == True, 1), else_=0)).label("correct_count"),
        )
        .select_from(SubmissionAnswer)
        .join(ExamSubmission, SubmissionAnswer.submission_id == ExamSubmission.id)
        .join(Question, SubmissionAnswer.question_id == Question.id)
        .where(
            ExamSubmission.student_id == student_id,
            ExamSubmission.teacher_id == current_user.id,
            ExamSubmission.status.in_(["submitted", "completed", "reviewed"]),
        )
        .group_by(Question.type)
        .order_by(func.count(SubmissionAnswer.id).desc())
    ).all()
    question_types = [
        {
            "type": row.type,
            "question_count": int(row.question_count or 0),
            "accuracy": round((float(row.correct_count or 0) / max(1, int(row.question_count or 0))), 2),
        }
        for row in question_type_rows
    ]

    task_items = db.scalars(
        select(StudyTask)
        .where(StudyTask.student_id == student_id)
        .order_by(StudyTask.priority.asc(), StudyTask.created_at.desc())
        .limit(6)
    ).all()
    pending_task_count = sum(1 for task in task_items if task.status in {"pending", "in_progress"})
    task_summary = {
        "pending_count": pending_task_count,
        "completed_count": sum(1 for task in task_items if task.status == "completed"),
        "ignored_count": sum(1 for task in task_items if task.status == "ignored"),
        "estimated_minutes": sum(int(task.estimated_minutes or 0) for task in task_items if task.status in {"pending", "in_progress"}),
    }

    latest_snapshot = db.scalar(
        select(StudentProfileSnapshot)
        .where(StudentProfileSnapshot.student_id == student_id, StudentProfileSnapshot.source_exam_id.in_(exam_ids))
        .order_by(StudentProfileSnapshot.created_at.desc())
        .limit(1)
    ) if exam_ids else None
    profile_json = latest_snapshot.profile_json if latest_snapshot and isinstance(latest_snapshot.profile_json, dict) else {}
    weak_knowledge_points = [
        str(item.get("name") or "").strip()
        for item in (profile_json.get("weak_knowledge_points") or [])
        if isinstance(item, dict)
    ]
    weak_knowledge_points = [name for name in weak_knowledge_points if name][:4]

    avg_score = round(sum(float(item.total_score or 0) for item in submissions) / len(submissions), 1) if submissions else 0.0
    avg_correct_rate = round(sum(float(item.correct_rate or 0) for item in submissions) / len(submissions), 2) if submissions else 0.0
    latest_score = round(float(latest_submission.total_score or 0), 1) if latest_submission else 0.0
    momentum = 0.0
    if len(trend) >= 2:
        momentum = round(float(trend[-1]["score"] or 0) - float(trend[0]["score"] or 0), 1)

    strongest_ability = growth_profile.get("ability_profile", [])[:1]
    weakest_ability = sorted(growth_profile.get("ability_profile", []), key=lambda item: item.get("value", 0))[:1]
    coaching_suggestions = [str(item) for item in (growth_profile.get("ai_actions") or []) if str(item).strip()][:4]
    if weak_knowledge_points:
        coaching_suggestions.insert(0, f"建议优先围绕 {weak_knowledge_points[0]} 做一次“讲 1 题 + 练 2 题 + 复盘 1 题”的短周期训练。")
    coaching_suggestions = coaching_suggestions[:4]

    return success_response(
        {
            "student": {
                "id": student.id,
                "name": student.name,
                "email": student.email,
                "phone": student.phone,
                "avatar_url": student.avatar_url,
                "grade_name": student.grade_name,
                "school_name": student.school_name,
                "status": student.status,
                "last_login_at": student.last_login_at.isoformat() if student.last_login_at else None,
            },
            "class": _serialize_class(classroom) if classroom else None,
            "overview": {
                "exam_count": len(submissions),
                "avg_score": avg_score,
                "latest_score": latest_score,
                "avg_correct_rate": avg_correct_rate,
                "momentum": momentum,
                "pending_review_count": db.scalar(
                    select(func.count()).select_from(ReviewItem).where(
                        ReviewItem.student_id == student_id,
                        ReviewItem.review_status == "pending",
                        ReviewItem.exam_id.in_(exam_ids if exam_ids else [-1]),
                    )
                ) or 0,
                "active_task_count": pending_task_count,
                "estimated_study_minutes": task_summary["estimated_minutes"],
                "risk_level": _teacher_student_risk_level(latest_score, avg_correct_rate),
            },
            "ability_profile": growth_profile.get("ability_profile", []),
            "question_type_distribution": question_types,
            "knowledge_points": knowledge_points,
            "trend": trend,
            "study_tasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "task_type": task.task_type,
                    "status": task.status,
                    "priority": task.priority,
                    "estimated_minutes": task.estimated_minutes,
                    "feedback": task.feedback,
                    "created_at": task.created_at.isoformat(),
                }
                for task in task_items
            ],
            "task_summary": task_summary,
            "ai_insight": {
                "summary": latest_snapshot.ai_summary if latest_snapshot and latest_snapshot.ai_summary else growth_profile.get("ai_summary"),
                "coaching_suggestions": coaching_suggestions,
                "weak_knowledge_points": weak_knowledge_points,
                "highlight": strongest_ability[0] if strongest_ability else None,
                "risk_focus": weakest_ability[0] if weakest_ability else None,
            },
            "latest_summary": {
                "latest_exam_id": latest_submission.exam_id if latest_submission else None,
                "latest_exam_title": db.get(Exam, latest_submission.exam_id).title if latest_submission and db.get(Exam, latest_submission.exam_id) else None,
                "latest_total_score": float(latest_submission.total_score) if latest_submission else None,
                "latest_submitted_at": latest_submission.submitted_at.isoformat() if latest_submission and latest_submission.submitted_at else None,
            },
        }
    )


@router.get("/teacher/questions")
def list_questions(
    subject: str | None = None,
    type: str | None = None,
    difficulty_min: float | None = None,
    difficulty_max: float | None = None,
    knowledge_point_id: int | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    """
    列出 questions 的数据列表。
    """
    query = select(Question).where(Question.created_by == current_user.id)
    if subject:
        subject_obj = db.scalar(select(Subject).where(Subject.name == subject))
        if subject_obj:
            query = query.where(Question.subject_id == subject_obj.id)
    if type:
        query = query.where(Question.type == type)
    if difficulty_min is not None:
        query = query.where(Question.difficulty >= difficulty_min)
    if difficulty_max is not None:
        query = query.where(Question.difficulty <= difficulty_max)
    if keyword:
        query = query.where(Question.stem.contains(keyword))
    if knowledge_point_id:
        query = query.join(QuestionKnowledgePoint, QuestionKnowledgePoint.question_id == Question.id).where(QuestionKnowledgePoint.knowledge_point_id == knowledge_point_id)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(Question.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return success_response({"items": [_serialize_question(db, item) for item in items], "total": total})


@router.get("/teacher/questions/subjects")
def list_question_subjects(current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    返回当前教师题库中实际存在题目的科目名称列表。
    """
    names = db.scalars(
        select(Subject.name)
        .join(Question, Question.subject_id == Subject.id)
        .where(Question.created_by == current_user.id)
        .group_by(Subject.name)
        .order_by(Subject.name.asc())
    ).all()
    return success_response({"items": [name for name in names if name]})


@router.get("/teacher/questions/detail")
def get_question_detail(question_id: int, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    获取单个题目的完整详情，用于教师侧独立预览页。
    """
    question = db.get(Question, question_id)
    if not question or question.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return success_response({"question": _serialize_question(db, question)})


@router.post("/teacher/questions/create")
def create_question(payload: QuestionCreateRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    创建新的 question 记录。
    """
    subject_obj = _get_subject_by_name(db, payload.subject)
    question = Question(
        created_by=current_user.id,
        subject_id=subject_obj.id,
        type=payload.type,
        stem=payload.stem,
        answer_text=serialize_answer(payload.answer),
        analysis=payload.analysis,
        score=payload.score,
        difficulty=payload.difficulty,
        source="manual",
        quality_status="draft",
        extra_meta={"ability_tags": payload.ability_tags},
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    _replace_question_relations(db, question.id, payload.options, payload.knowledge_point_ids)
    return success_response({"question": _serialize_question(db, question)}, "question created")


@router.post("/teacher/questions/update")
def update_question(payload: QuestionUpdateRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    更新已有的 question 记录。
    """
    question = db.get(Question, payload.question_id)
    if not question or question.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    data = payload.model_dump(exclude_none=True)
    subject_name = data.pop("subject", None)
    options = data.pop("options", None)
    knowledge_point_ids = data.pop("knowledge_point_ids", None)
    answer = data.pop("answer", None)
    ability_tags = data.pop("ability_tags", None)
    if subject_name:
        question.subject_id = _get_subject_by_name(db, subject_name).id
    if answer is not None:
        question.answer_text = serialize_answer(answer)
    if ability_tags is not None:
        extra = question.extra_meta or {}
        extra["ability_tags"] = ability_tags
        question.extra_meta = extra
    for field, value in data.items():
        setattr(question, field, value)
    db.add(question)
    db.commit()
    if options is not None or knowledge_point_ids is not None:
        _replace_question_relations(db, question.id, options, knowledge_point_ids)
    db.refresh(question)
    return success_response({"question": _serialize_question(db, question)}, "question updated")


@router.post("/teacher/questions/delete")
def delete_question(payload: DeleteRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    删除指定的 question 记录。
    """
    if payload.question_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="question_id is required")
    question = db.get(Question, payload.question_id)
    if not question or question.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    affected_exam_ids = db.scalars(select(ExamQuestion.exam_id).where(ExamQuestion.question_id == question.id)).all()
    if affected_exam_ids:
        db.query(ExamQuestion).filter(ExamQuestion.question_id == question.id).delete(synchronize_session=False)

    db.query(QuestionOption).filter(QuestionOption.question_id == question.id).delete()
    db.query(QuestionKnowledgePoint).filter(QuestionKnowledgePoint.question_id == question.id).delete()
    db.delete(question)

    for exam_id in set(affected_exam_ids):
        if _count_valid_exam_questions(db, exam_id) <= 0:
            _cleanup_study_tasks_for_exam(db, exam_id)

    db.commit()
    return success_response({"success": True}, "question deleted")


@router.post("/teacher/questions/import")
def import_questions(payload: ImportQuestionsRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    处理 import questions 请求并返回结果。
    """
    task = queue_ai_task(
        db,
        task_type="question_import",
        resource_type="question",
        resource_id=None,
        created_by=current_user.id,
        request_payload=payload.model_dump(),
    )
    mark_ai_task_running(db, task, progress=20)
    complete_ai_task(db, task, result_payload={"import_count": 0, "failed_count": 0, "errors": ["当前阶段未实现文件导题，保留接口"]})
    return success_response({"import_count": 0, "failed_count": 0, "errors": ["当前阶段未实现文件导题"], "task_id": task.task_id})


@router.post("/teacher/questions/ai-generate")
def ai_generate_questions(payload: AIQuestionGenerateRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    处理 ai generate questions 请求并返回结果。
    """
    task = queue_ai_task(
        db,
        task_type="ai_generate_question",
        resource_type="question",
        resource_id=None,
        created_by=current_user.id,
        request_payload=payload.model_dump(),
    )
    mark_ai_task_running(db, task, progress=35)
    generated = generate_questions_with_llm(payload)
    complete_ai_task(
        db,
        task,
        result_payload=generated,
    )
    return success_response(
        {
            "questions": task.result_payload.get("questions", []),
            "used_model": task.result_payload.get("used_model"),
            "model_errors": task.result_payload.get("model_errors", []),
            "task_id": task.task_id,
        }
    )


@router.post("/teacher/exams/ai-assemble")
def ai_assemble_exam_from_bank(
    payload: AIExamAssembleRequest,
    current_user: User = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    """
    根据教师的自然语言描述，从现有题库中自动挑题组卷。
    """
    subject_obj = _get_subject_by_name(db, payload.subject)
    questions = db.scalars(
        select(Question)
        .where(Question.created_by == current_user.id, Question.subject_id == subject_obj.id)
        .order_by(Question.created_at.desc())
    ).all()
    if not questions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="当前科目题库为空，无法智能组卷")

    requirements = _parse_exam_assemble_requirement(payload.requirement)
    if not requirements:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未能识别出组卷要求，请更明确说明题型与数量")

    excluded_ids = set(payload.exclude_question_ids or [])
    selected_ids: set[int] = set(excluded_ids)
    selected_questions: list[Question] = []
    matched_blocks: list[dict[str, Any]] = []
    unmet_blocks: list[dict[str, Any]] = []

    for block in requirements:
      matched = _pick_questions_for_requirement(questions, block, selected_ids)
      if matched:
          selected_questions.extend(matched)
          selected_ids.update(item.id for item in matched)

      matched_blocks.append(
          {
              "label": block["label"],
              "count": block["count"],
              "matched_count": len(matched),
              "keywords": block["keywords"],
          }
      )
      if len(matched) < block["count"]:
          unmet_blocks.append(
              {
                  "label": block["label"],
                  "requested_count": block["count"],
                  "matched_count": len(matched),
                  "keywords": block["keywords"],
              }
          )

    serialized = [_serialize_question(db, item) for item in selected_questions]
    summary_parts = [f"已匹配 {len(serialized)} 题"]
    for block in matched_blocks:
        summary_parts.append(f"{block['label']} {block['matched_count']}/{block['count']} 题")

    return success_response(
        {
            "questions": serialized,
            "matched_requirements": matched_blocks,
            "unmet_requirements": unmet_blocks,
            "summary": "，".join(summary_parts),
        }
    )


@router.post("/teacher/questions/ai-review")
def ai_review_question(payload: AIQuestionReviewRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    处理 ai review question 请求并返回结果。
    """
    question = db.get(Question, payload.question_id)
    if not question or question.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    review = {
        "ambiguity_risk": "low",
        "option_quality": "good",
        "answer_consistency": "consistent",
        "difficulty_estimation": question.difficulty or 0.5,
        "suggestions": ["当前为第一阶段规则占位结果，后续接入大模型细化审核。"],
    }
    question.ai_review_summary = json.dumps(review, ensure_ascii=False)
    question.quality_status = "reviewed"
    db.add(question)
    db.commit()
    return success_response({"review": review})


@router.post("/teacher/exams/create")
def create_exam(payload: ExamCreateRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    创建新的 exam 记录。
    """
    normalized_title = payload.title.strip()
    if not normalized_title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam title is required")

    duplicate_exam = db.scalar(
        select(Exam).where(
            Exam.created_by == current_user.id,
            func.lower(Exam.title) == normalized_title.lower(),
        ).limit(1)
    )
    if duplicate_exam:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Exam title already exists for current teacher")

    if payload.publish_now and len(payload.class_ids) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please bind at least one class before publishing")
    if payload.publish_now and len(payload.question_items) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please add at least one question before publishing")

    start_time, end_time = _normalize_exam_window(
        payload.start_time,
        payload.end_time,
        payload.duration_minutes,
        payload.publish_now,
    )

    subject_obj = _get_subject_by_name(db, payload.subject)
    exam = Exam(
        created_by=current_user.id,
        subject_id=subject_obj.id,
        title=normalized_title,
        duration_minutes=payload.duration_minutes,
        total_score=sum(item.score for item in payload.question_items),
        status="published" if payload.publish_now else "draft",
        instructions=payload.instructions,
        allow_review=payload.allow_review,
        random_question_order=payload.random_question_order,
        start_time=start_time,
        end_time=end_time,
        published_at=datetime.now(UTC).replace(tzinfo=None) if payload.publish_now else None,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    _replace_exam_relations(db, exam.id, payload.class_ids, payload.question_items)
    db.refresh(exam)
    return success_response({"exam": _serialize_exam(db, exam)}, "exam created")


@router.get("/teacher/exams")
def list_exams(
    status: str | None = None,
    subject: str | None = None,
    class_id: int | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    """
    列出 exams 的数据列表。
    """
    query = select(Exam).where(Exam.created_by == current_user.id)
    if status:
        query = query.where(Exam.status == status)
    if subject:
        subject_obj = db.scalar(select(Subject).where(Subject.name == subject))
        if subject_obj:
            query = query.where(Exam.subject_id == subject_obj.id)
    if keyword:
        query = query.where(Exam.title.contains(keyword))
    if class_id:
        query = query.join(ExamClass, ExamClass.exam_id == Exam.id).where(ExamClass.class_id == class_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(Exam.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return success_response({"items": [_serialize_exam(db, item) for item in items], "total": total})


@router.get("/teacher/exams/detail")
def get_exam_detail(exam_id: int, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    获取 exam detail 相关数据。
    """
    exam = _get_teacher_exam(db, current_user.id, exam_id)
    question_items = db.scalars(select(ExamQuestion).where(ExamQuestion.exam_id == exam.id).order_by(ExamQuestion.order_no.asc())).all()
    classes = db.scalars(select(ClassRoom).join(ExamClass, ExamClass.class_id == ClassRoom.id).where(ExamClass.exam_id == exam.id)).all()
    return success_response({"exam": _serialize_exam(db, exam), "question_items": [_serialize_exam_question(db, item) for item in question_items], "classes": [_serialize_class(item) for item in classes]})


@router.get("/teacher/exams/insights")
def get_exam_insights(exam_id: int, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    获取 exam insights 相关数据。
    """
    exam = _get_teacher_exam(db, current_user.id, exam_id)

    target_students = db.scalar(
        select(func.count(func.distinct(ClassStudent.student_id)))
        .select_from(ClassStudent)
        .join(ExamClass, ExamClass.class_id == ClassStudent.class_id)
        .where(
            ExamClass.exam_id == exam.id,
            ClassStudent.teacher_id == current_user.id,
            ClassStudent.status == "active",
        )
    ) or 0

    submissions = db.scalars(select(ExamSubmission).where(ExamSubmission.exam_id == exam.id)).all()
    submitted_statuses = {"submitted", "reviewed"}
    submitted_submissions = [item for item in submissions if item.status in submitted_statuses]
    active_submissions = [item for item in submissions if item.status in {"in_progress", "submitted", "reviewed"}]
    submitted_count = len(active_submissions)
    completion_rate = round((submitted_count / target_students) if target_students else 0, 4)

    duration_samples: list[float] = []
    for item in submitted_submissions:
        if item.started_at and item.submitted_at and item.submitted_at >= item.started_at:
            duration_minutes = (item.submitted_at - item.started_at).total_seconds() / 60
            duration_samples.append(duration_minutes)
    avg_duration_minutes = round(sum(duration_samples) / len(duration_samples), 1) if duration_samples else 0.0

    avg_score = round(
        float(sum(float(item.total_score or 0) for item in submitted_submissions) / len(submitted_submissions)),
        2,
    ) if submitted_submissions else 0.0

    answer_rows = db.execute(
        select(
            SubmissionAnswer.question_id,
            func.count(SubmissionAnswer.id).label("answer_count"),
            func.sum(case((SubmissionAnswer.is_correct == False, 1), else_=0)).label("wrong_count"),
            func.avg(SubmissionAnswer.spent_seconds).label("avg_spent_seconds"),
        )
        .where(SubmissionAnswer.exam_id == exam.id, SubmissionAnswer.is_correct.is_not(None))
        .group_by(SubmissionAnswer.question_id)
    ).all()

    question_insights: list[dict] = []
    total_answers = 0
    total_wrong = 0
    for row in answer_rows:
        answer_count = int(row.answer_count or 0)
        wrong_count = int(row.wrong_count or 0)
        total_answers += answer_count
        total_wrong += wrong_count
        wrong_rate = round((wrong_count / answer_count), 4) if answer_count else 0
        question = db.get(Question, row.question_id)
        question_insights.append(
            {
                "question_id": row.question_id,
                "stem": question.stem if question else "题目缺失",
                "answer_count": answer_count,
                "wrong_count": wrong_count,
                "wrong_rate": wrong_rate,
                "avg_spent_seconds": round(float(row.avg_spent_seconds or 0), 1),
            }
        )

    question_insights.sort(key=lambda x: x["wrong_rate"], reverse=True)
    top_wrong_questions = question_insights[:3]
    overall_wrong_rate = round((total_wrong / total_answers), 4) if total_answers else 0

    easy_mistakes: list[str] = []
    teaching_suggestions: list[str] = []
    if completion_rate < 0.4:
        easy_mistakes.append("当前作答覆盖偏低，学生可能未进入考试或提醒触达不足。")
        teaching_suggestions.append("建议先在班级群进行一次集中提醒，并设置明确截止时段。")
    if top_wrong_questions and top_wrong_questions[0]["wrong_rate"] >= 0.6:
        easy_mistakes.append("头部错题错误率较高，可能存在知识点理解断层。")
        teaching_suggestions.append("建议围绕最高错题组织 10 分钟微讲解，并布置同类 2-3 题跟练。")
    if avg_duration_minutes > float(exam.duration_minutes or 0) * 0.9 and submitted_submissions:
        easy_mistakes.append("平均用时接近考试时长上限，存在时间分配压力。")
        teaching_suggestions.append("建议强化限时训练和先易后难策略，降低后程失分。")
    if not easy_mistakes:
        easy_mistakes.append("整体作答数据平稳，暂未出现明显异常。")
        teaching_suggestions.append("可继续按章节迭代小测，维持学习节奏与诊断闭环。")

    return success_response(
        {
            "progress": {
                "submitted_count": submitted_count,
                "target_count": target_students,
                "completion_rate": completion_rate,
            },
            "learning": {
                "avg_duration_minutes": avg_duration_minutes,
                "avg_score": avg_score,
                "overall_wrong_rate": overall_wrong_rate,
            },
            "top_wrong_questions": top_wrong_questions,
            "ai_summary": {
                "easy_mistakes": easy_mistakes,
                "teaching_suggestions": teaching_suggestions,
            },
        }
    )


@router.post("/teacher/exams/update")
def update_exam(payload: ExamUpdateRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    更新已有的 exam 记录。
    """
    exam = _get_teacher_exam(db, current_user.id, payload.exam_id)
    data = payload.model_dump(exclude_none=True)
    class_ids = data.pop("class_ids", None)
    question_items = data.pop("question_items", None)
    data.pop("exam_id", None)
    if "start_time" in data or "end_time" in data:
        normalized_start, normalized_end = _normalize_exam_window(
            data.get("start_time") or exam.start_time,
            data.get("end_time") or exam.end_time,
            int(data.get("duration_minutes") or exam.duration_minutes or 60),
            False,
        )
        if "start_time" in data:
            data["start_time"] = normalized_start
        if "end_time" in data:
            data["end_time"] = normalized_end
    for field, value in data.items():
        setattr(exam, field, value)
    if question_items is not None:
        exam.total_score = sum(item.score for item in question_items)
    db.add(exam)
    db.commit()
    if class_ids is not None or question_items is not None:
        _replace_exam_relations(db, exam.id, class_ids, question_items)
    db.refresh(exam)
    return success_response({"exam": _serialize_exam(db, exam)}, "exam updated")


@router.post("/teacher/exams/publish")
def publish_exam(payload: ExamActionRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    处理 publish exam 请求并返回结果。
    """
    exam = _get_teacher_exam(db, current_user.id, payload.exam_id)

    # Publishing an exam without bound classes means students can never see it.
    bound_class_count = db.scalar(
        select(func.count()).select_from(ExamClass).where(ExamClass.exam_id == exam.id)
    ) or 0
    if bound_class_count <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please bind at least one class before publishing")

    question_count = db.scalar(
        select(func.count()).select_from(ExamQuestion).where(ExamQuestion.exam_id == exam.id)
    ) or 0
    if question_count <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please add at least one question before publishing")

    now_utc = datetime.now(UTC)

    # SQLite 历史数据可能是 naive datetime；新数据可能是 aware datetime。
    # 统一比较基准，避免 naive/aware 混比触发 TypeError。
    if exam.start_time.tzinfo is None and exam.end_time.tzinfo is None:
        compare_now = now_utc.replace(tzinfo=None)
        compare_start = exam.start_time
        compare_end = exam.end_time
    else:
        compare_now = now_utc
        compare_start = exam.start_time if exam.start_time.tzinfo is not None else exam.start_time.replace(tzinfo=UTC)
        compare_end = exam.end_time if exam.end_time.tzinfo is not None else exam.end_time.replace(tzinfo=UTC)

    # If a draft is published long after creation, the original exam window may already expire.
    # Auto-refresh the window to keep the exam visible to students after publishing.
    if compare_end <= compare_now or compare_start >= compare_end:
        exam.start_time = compare_now
        exam.end_time = compare_now + timedelta(minutes=max(int(exam.duration_minutes or 60), 1))

    exam.status = "published"
    exam.published_at = compare_now
    db.add(exam)
    db.commit()
    return success_response(
        {
            "exam_id": exam.id,
            "status": exam.status,
            "start_time": exam.start_time.isoformat(),
            "end_time": exam.end_time.isoformat(),
        },
        "exam published",
    )


@router.post("/teacher/exams/pause")
def pause_exam(payload: ExamActionRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    处理 pause exam 请求并返回结果。
    """
    exam = _get_teacher_exam(db, current_user.id, payload.exam_id)
    exam.status = "draft"
    db.add(exam)
    db.commit()
    return success_response({"exam_id": exam.id, "status": exam.status}, "exam paused")


@router.post("/teacher/exams/finish")
def finish_exam(payload: ExamActionRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    处理 finish exam 请求并返回结果。
    """
    exam = _get_teacher_exam(db, current_user.id, payload.exam_id)
    exam.status = "finished"
    exam.finished_at = datetime.now(UTC)
    db.add(exam)
    db.commit()
    return success_response({"exam_id": exam.id, "status": exam.status}, "exam finished")


@router.post("/teacher/exams/delete")
def delete_exam(payload: DeleteRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    删除指定的 exam 记录。
    """
    if payload.exam_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="exam_id is required")
    exam = _get_teacher_exam(db, current_user.id, payload.exam_id)

    # Only finished exams can be deleted to prevent accidental removal of active tasks.
    if exam.status != "finished":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only finished exams can be deleted")

    _cleanup_study_tasks_for_exam(db, exam.id)

    submission_ids = db.scalars(
        select(ExamSubmission.id).where(ExamSubmission.exam_id == exam.id)
    ).all()
    if submission_ids:
        review_item_ids = db.scalars(
            select(ReviewItem.id).where(ReviewItem.submission_id.in_(submission_ids))
        ).all()
        if review_item_ids:
            db.query(ReviewLog).filter(ReviewLog.review_item_id.in_(review_item_ids)).delete(synchronize_session=False)
            db.query(ReviewItem).filter(ReviewItem.id.in_(review_item_ids)).delete(synchronize_session=False)

        db.query(SubmissionAnswer).filter(SubmissionAnswer.submission_id.in_(submission_ids)).delete(synchronize_session=False)
        db.query(SubmissionBehaviorEvent).filter(SubmissionBehaviorEvent.submission_id.in_(submission_ids)).delete(synchronize_session=False)
        db.query(ExamSubmission).filter(ExamSubmission.id.in_(submission_ids)).delete(synchronize_session=False)

    db.query(AITask).filter(AITask.resource_type == "exam", AITask.resource_id == exam.id).delete(synchronize_session=False)

    db.query(ExamQuestion).filter(ExamQuestion.exam_id == exam.id).delete()
    db.query(ExamClass).filter(ExamClass.exam_id == exam.id).delete()
    db.delete(exam)
    db.commit()
    return success_response({"success": True}, "exam deleted")


@router.post("/teacher/exams/ai-evaluate")
def ai_evaluate_exam(payload: ExamActionRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    处理 ai evaluate exam 请求并返回结果。
    """
    exam = _get_teacher_exam(db, current_user.id, payload.exam_id)
    questions = db.scalars(select(ExamQuestion).where(ExamQuestion.exam_id == exam.id)).all()
    evaluation = {
        "difficulty": 0.6,
        "discrimination": 0.55,
        "coverage_score": 0.7,
        "structure_comments": [f"当前试卷共 {len(questions)} 题，结构基本完整。"],
        "estimated_duration_minutes": exam.duration_minutes,
    }
    exam.ai_evaluation_result = evaluation
    db.add(exam)
    db.commit()
    task = queue_ai_task(db, "exam_evaluate", "exam", exam.id, current_user.id, {"exam_id": exam.id})
    mark_ai_task_running(db, task, progress=60)
    complete_ai_task(db, task, result_payload=evaluation)
    return success_response({"evaluation": evaluation})


@router.get("/teacher/review/objective-score")
def get_objective_score(exam_id: int, submission_id: int, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    获取 objective score 相关数据。
    """
    _get_teacher_exam(db, current_user.id, exam_id)
    submission = db.get(ExamSubmission, submission_id)
    if not submission or submission.exam_id != exam_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    answers = db.scalars(select(SubmissionAnswer).where(SubmissionAnswer.submission_id == submission_id)).all()
    return success_response({"submission_id": submission_id, "objective_score": float(submission.objective_score), "question_scores": [{"question_id": item.question_id, "score": float(item.score)} for item in answers]})


@router.post("/teacher/review/ai-score")
def ai_score(payload: AIScoreRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    处理 ai score 请求并返回结果。
    """
    _get_teacher_exam(db, current_user.id, payload.exam_id)
    task = queue_ai_task(
        db,
        "ai_score",
        "submission",
        payload.submission_id,
        current_user.id,
        payload.model_dump(),
    )
    mark_ai_task_running(db, task, progress=50)
    complete_ai_task(db, task, result_payload={"message": "当前阶段为规则占位评分，后续接入大模型。"})
    return success_response({"task_id": task.task_id, "status": task.status})


@router.get("/teacher/review/items")
def list_review_items(
    exam_id: int,
    review_status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    """
    列出 review items 的数据列表。
    """
    _get_teacher_exam(db, current_user.id, exam_id)
    query = select(ReviewItem).where(ReviewItem.exam_id == exam_id)
    if review_status:
        query = query.where(ReviewItem.review_status == review_status)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()

    submission_rows = db.execute(
        select(ExamSubmission, User)
        .join(User, User.id == ExamSubmission.student_id)
        .where(ExamSubmission.exam_id == exam_id)
        .order_by(ExamSubmission.submitted_at.desc(), ExamSubmission.created_at.desc())
    ).all()

    submission_items: list[dict[str, Any]] = []
    for submission, student in submission_rows:
        item_count = db.scalar(
            select(func.count()).select_from(ReviewItem).where(ReviewItem.submission_id == submission.id)
        ) or 0
        pending_count = db.scalar(
            select(func.count()).select_from(ReviewItem).where(
                ReviewItem.submission_id == submission.id,
                ReviewItem.review_status == "pending",
            )
        ) or 0
        submission_items.append(
            {
                "submission_id": submission.id,
                "student_id": submission.student_id,
                "student_name": student.name,
                "status": submission.status,
                "review_status": submission.review_status,
                "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
                "total_score": float(submission.total_score or 0),
                "manual_item_count": int(item_count),
                "pending_manual_count": int(pending_count),
            }
        )

    return success_response(
        {
            "items": [_serialize_review_item(item) for item in items],
            "total": total,
            "manual_review_required": total > 0,
            "submissions": submission_items,
        }
    )


@router.get("/teacher/review/tasks")
def list_review_tasks(
    view: str = Query("all"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    """
    教师阅卷任务总览：同时返回待阅和已阅任务。
    """
    exams = db.scalars(
        select(Exam)
        .where(Exam.created_by == current_user.id)
        .order_by(Exam.created_at.desc())
    ).all()

    tasks = []
    for exam in exams:
        total_submissions = db.scalar(select(func.count()).select_from(ExamSubmission).where(ExamSubmission.exam_id == exam.id)) or 0
        if total_submissions <= 0:
            continue

        # 与 /teacher/review/items 保持一致：阅卷任务只统计真实存在的 review items。
        total_review_items = db.scalar(
            select(func.count()).select_from(ReviewItem).where(ReviewItem.exam_id == exam.id)
        ) or 0

        pending_review_count = db.scalar(
            select(func.count()).select_from(ReviewItem).where(
                ReviewItem.exam_id == exam.id,
                ReviewItem.review_status == "pending",
            )
        ) or 0
        reviewed_count = db.scalar(
            select(func.count()).select_from(ReviewItem).where(
                ReviewItem.exam_id == exam.id,
                ReviewItem.review_status == "reviewed",
            )
        ) or 0
        has_pending = pending_review_count > 0
        review_mode = "manual" if total_review_items > 0 else "objective_only"
        if view == "pending" and not has_pending:
            continue
        if view == "completed" and has_pending:
            continue

        latest_submit = db.scalar(
            select(func.max(ExamSubmission.submitted_at)).where(ExamSubmission.exam_id == exam.id)
        )
        subject = db.get(Subject, exam.subject_id)
        tasks.append(
            {
                "exam_id": exam.id,
                "exam_title": exam.title,
                "subject": subject.name if subject else None,
                "exam_status": exam.status,
                "total_submissions": int(total_submissions),
                "total_review_items": int(total_review_items),
                "pending_count": int(pending_review_count),
                "reviewed_count": int(reviewed_count),
                "ai_status": "completed",
                "task_status": "pending" if has_pending else "completed",
                "review_mode": review_mode,
                "latest_submitted_at": latest_submit.isoformat() if latest_submit else None,
            }
        )

    total = len(tasks)
    start = (page - 1) * page_size
    end = start + page_size
    return success_response({"items": tasks[start:end], "total": total})


@router.get("/teacher/review/retake-requests")
def list_retake_requests(
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    """
    列出学生重考申请，供教师审批。
    """
    exam_ids = db.scalars(select(Exam.id).where(Exam.created_by == current_user.id)).all()
    if not exam_ids:
        return success_response({"items": [], "total": 0})

    query = select(AITask).where(
        AITask.type == "retake_request",
        AITask.resource_type == "exam",
        AITask.resource_id.in_(exam_ids),
    )
    if status_filter:
        query = query.where(AITask.status == status_filter)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(
            case((AITask.status == "pending", 0), else_=1),
            AITask.created_at.desc(),
        ).offset((page - 1) * page_size).limit(page_size)
    ).all()

    items = []
    for row in rows:
        payload = row.request_payload or {}
        exam = db.get(Exam, int(row.resource_id or 0))
        student_id = int(payload.get("student_id") or 0)
        student = db.get(User, student_id) if student_id else None
        items.append(
            {
                "request_id": row.id,
                "status": row.status,
                "exam_id": row.resource_id,
                "exam_title": exam.title if exam else None,
                "student_id": student_id or None,
                "student_name": student.name if student else payload.get("student_name"),
                "reason": payload.get("reason"),
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat(),
                "comment": (row.result_payload or {}).get("comment") if row.result_payload else None,
            }
        )

    return success_response({"items": items, "total": total})


@router.post("/teacher/review/retake-requests/action")
def review_retake_request(
    payload: RetakeRequestActionRequest,
    current_user: User = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    """
    教师审批重考申请：approve 或 reject。
    """
    request_task = db.get(AITask, payload.request_id)
    if not request_task or request_task.type != "retake_request":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Retake request not found")

    exam_id = int(request_task.resource_id or 0)
    exam = _get_teacher_exam(db, current_user.id, exam_id)
    request_payload = request_task.request_payload or {}
    student_id = int(request_payload.get("student_id") or request_task.created_by or 0)
    if student_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid retake request")

    action = (payload.action or "").strip().lower()
    if action not in {"approve", "reject"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action")
    if request_task.status not in {"pending", "approved", "rejected"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Retake request is not actionable")

    if action == "approve":
        submission = db.scalar(
            select(ExamSubmission).where(ExamSubmission.exam_id == exam.id, ExamSubmission.student_id == student_id)
        )
        if not submission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

        review_item_ids = db.scalars(select(ReviewItem.id).where(ReviewItem.submission_id == submission.id)).all()
        if review_item_ids:
            db.query(ReviewLog).filter(ReviewLog.review_item_id.in_(review_item_ids)).delete(synchronize_session=False)
            db.query(ReviewItem).filter(ReviewItem.id.in_(review_item_ids)).delete(synchronize_session=False)

        submission.status = "not_started"
        submission.started_at = None
        submission.submitted_at = None
        submission.deadline_at = None
        submission.objective_score = 0
        submission.subjective_score = 0
        submission.total_score = 0
        submission.correct_rate = 0
        submission.ranking_in_class = None
        submission.review_status = "pending"
        submission.ai_analysis_status = "pending"
        db.query(SubmissionAnswer).filter(SubmissionAnswer.submission_id == submission.id).delete(synchronize_session=False)
        db.add(submission)

    request_task.status = "approved" if action == "approve" else "rejected"
    request_task.progress = 100
    request_task.finished_at = datetime.now(UTC)
    request_task.result_payload = {
        "reviewed_by": current_user.id,
        "action": action,
        "comment": (payload.comment or "").strip()[:300] if payload.comment else None,
        "reviewed_at": datetime.now(UTC).isoformat(),
    }
    db.add(request_task)
    db.commit()
    return success_response({"request_id": request_task.id, "status": request_task.status})


@router.post("/teacher/review/submit")
def submit_review(payload: ReviewSubmitRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    处理 submit review 请求并返回结果。
    """
    item = db.get(ReviewItem, payload.review_item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review item not found")
    submission = db.get(ExamSubmission, item.submission_id)
    exam = _get_teacher_exam(db, current_user.id, item.exam_id)
    if not submission or exam.id != item.exam_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    old_score = item.final_score
    item.final_score = payload.final_score
    item.teacher_comment = payload.review_comment
    item.review_status = "reviewed"
    item.reviewed_by = current_user.id
    item.reviewed_at = datetime.now(UTC)
    db.add(item)
    db.add(ReviewLog(review_item_id=item.id, operator_id=current_user.id, old_score=old_score, new_score=payload.final_score, comment=payload.review_comment))
    db.commit()
    return success_response({"review_item_id": item.id, "status": item.review_status})


@router.post("/teacher/review/publish-results")
def publish_results(payload: ExamActionRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    """
    处理 publish results 请求并返回结果。
    """
    exam = _get_teacher_exam(db, current_user.id, payload.exam_id)
    submissions = db.scalars(select(ExamSubmission).where(ExamSubmission.exam_id == exam.id)).all()
    for submission in submissions:
        subjective_score = db.scalar(select(func.coalesce(func.sum(ReviewItem.final_score), 0)).where(ReviewItem.submission_id == submission.id)) or 0
        submission.subjective_score = float(subjective_score)
        submission.total_score = float(submission.objective_score) + float(subjective_score)
        submission.status = "reviewed"
        submission.review_status = "completed"
        db.add(submission)
    db.commit()

    ranked = db.scalars(select(ExamSubmission).where(ExamSubmission.exam_id == exam.id).order_by(ExamSubmission.total_score.desc(), ExamSubmission.submitted_at.asc())).all()
    for rank, submission in enumerate(ranked, start=1):
        submission.ranking_in_class = rank
        db.add(submission)
    db.commit()
    for submission in ranked:
        realtime_events.publish(
            submission_channel(exam.id, submission.id),
            "results_published",
            {"submission_id": submission.id, "ranking_in_class": submission.ranking_in_class, "total_score": float(submission.total_score)},
        )
    return success_response({"exam_id": exam.id, "published": True})


def _serialize_class(classroom: ClassRoom | None) -> dict | None:
    """
    序列化 class 对象为字典。
    """
    if classroom is None:
        return None
    return {
        "id": classroom.id,
        "name": classroom.name,
        "grade_name": classroom.grade_name,
        "subject": classroom.subject,
        "teacher_id": classroom.teacher_id,
        "student_count": classroom.student_count,
        "invite_code": classroom.invite_code,
        "status": classroom.status,
        "created_at": classroom.created_at.isoformat(),
    }


def _serialize_question(db: Session, question: Question) -> dict:
    """
    序列化 question 对象为字典。
    """
    options = db.scalars(select(QuestionOption).where(QuestionOption.question_id == question.id).order_by(QuestionOption.sort_order.asc())).all()
    knowledge_links = db.scalars(select(QuestionKnowledgePoint).where(QuestionKnowledgePoint.question_id == question.id)).all()
    knowledge_ids = [item.knowledge_point_id for item in knowledge_links]
    knowledge_points = db.scalars(select(KnowledgePoint).where(KnowledgePoint.id.in_(knowledge_ids))).all() if knowledge_ids else []
    subject = db.get(Subject, question.subject_id)
    extra_meta = question.extra_meta or {}
    return {
        "id": question.id,
        "subject": subject.name if subject else None,
        "type": question.type,
        "stem": question.stem,
        "options": [{"key": option.option_key, "content": option.content} for option in options],
        "answer": json.loads(question.answer_text),
        "analysis": question.analysis,
        "score": float(question.score),
        "difficulty": question.difficulty,
        "knowledge_points": [{"id": item.id, "name": item.name} for item in knowledge_points],
        "ability_tags": extra_meta.get("ability_tags", []),
        "created_by": question.created_by,
        "created_at": question.created_at.isoformat(),
    }


def _serialize_exam(db: Session, exam: Exam) -> dict:
    """
    序列化 exam 对象为字典。
    """
    subject = db.get(Subject, exam.subject_id)
    class_ids = db.scalars(select(ExamClass.class_id).where(ExamClass.exam_id == exam.id)).all()
    question_count = db.scalar(select(func.count()).select_from(ExamQuestion).where(ExamQuestion.exam_id == exam.id)) or 0

    def as_utc_iso(dt: datetime) -> str:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")
        return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")

    return {
        "id": exam.id,
        "title": exam.title,
        "subject": subject.name if subject else None,
        "duration_minutes": exam.duration_minutes,
        "total_score": float(exam.total_score),
        "status": exam.status,
        "start_time": as_utc_iso(exam.start_time),
        "end_time": as_utc_iso(exam.end_time),
        "instructions": exam.instructions,
        "allow_review": exam.allow_review,
        "random_question_order": exam.random_question_order,
        "question_count": question_count,
        "class_ids": class_ids,
        "created_by": exam.created_by,
        "created_at": exam.created_at.isoformat(),
    }


def _serialize_exam_question(db: Session, item: ExamQuestion) -> dict:
    """
    序列化 exam question 对象为字典。
    """
    question = db.get(Question, item.question_id)
    return {
        "question_id": item.question_id,
        "score": float(item.score),
        "order_no": item.order_no,
        "section_name": item.section_name,
        "question": _serialize_question(db, question) if question else None,
    }


def _serialize_review_item(item: ReviewItem) -> dict:
    """
    序列化 review item 对象为字典。
    """
    return {
        "id": item.id,
        "exam_id": item.exam_id,
        "submission_id": item.submission_id,
        "question_id": item.question_id,
        "student_id": item.student_id,
        "ai_suggest_score": float(item.ai_suggest_score) if item.ai_suggest_score is not None else None,
        "final_score": float(item.final_score) if item.final_score is not None else None,
        "review_status": item.review_status,
    }


def _parse_exam_assemble_requirement(requirement: str) -> list[dict[str, Any]]:
    text = re.sub(r"\s+", "", str(requirement or ""))
    if not text:
        return []

    normalized = text
    replacements = {
        "单项选择题": "单选题",
        "多项选择题": "多选题",
        "选择": "选择题",
        "判断": "判断题",
        "填空": "填空题",
        "简答": "简答题",
        "问答题": "简答题",
    }
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)

    segments = [seg for seg in re.split(r"[，,；;。]|加|再加|以及|并且|同时|另加|另外", normalized) if seg]
    parsed: list[dict[str, Any]] = []
    for segment in segments:
        block = _parse_requirement_segment(segment)
        if block:
            parsed.append(block)

    if parsed:
        return parsed

    total = _extract_count_from_text(normalized)
    keywords = _extract_keywords(normalized)
    if total:
        return [{"label": "综合题目", "allowed_types": None, "count": total, "keywords": keywords}]
    return []


def _parse_requirement_segment(segment: str) -> dict[str, Any] | None:
    type_aliases = [
        ("单选题", ["single_choice"]),
        ("多选题", ["multiple_choice"]),
        ("选择题", ["single_choice", "multiple_choice"]),
        ("判断题", ["judge"]),
        ("填空题", ["blank"]),
        ("简答题", ["essay"]),
    ]
    for label, allowed_types in type_aliases:
        if label not in segment:
            continue
        count = _extract_count_from_text(segment)
        if count <= 0:
            continue
        keywords = _extract_keywords(segment.replace(label, ""))
        return {
            "label": label,
            "allowed_types": allowed_types,
            "count": count,
            "keywords": keywords,
        }
    return None


def _extract_count_from_text(text: str) -> int:
    arabic = re.search(r"(\d{1,3})\s*(?:道|个|题)?", text)
    if arabic:
        return max(0, int(arabic.group(1)))
    chinese = re.search(r"([零一二两三四五六七八九十百]+)\s*(?:道|个|题)", text)
    if chinese:
        return _chinese_number_to_int(chinese.group(1))
    return 0


def _chinese_number_to_int(text: str) -> int:
    chars = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if text == "十":
        return 10
    if "十" in text:
        left, _, right = text.partition("十")
        tens = chars.get(left, 1) if left else 1
        units = chars.get(right, 0) if right else 0
        return tens * 10 + units
    return chars.get(text, 0)


def _extract_keywords(text: str) -> list[str]:
    cleaned = re.sub(r"(\d+|[零一二两三四五六七八九十百]+)(?:道|个|题)?", " ", text)
    for token in ["我想", "我要", "希望", "出一套", "卷子", "试卷", "试题", "工程制图", "的", "和", "及", "并", "全部题型"]:
        cleaned = cleaned.replace(token, " ")
    cleaned = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]+", " ", cleaned)
    parts = [part.strip() for part in cleaned.split(" ") if part.strip()]
    unique_parts: list[str] = []
    for part in parts:
        if len(part) <= 1 and not part.isdigit():
            continue
        if part not in unique_parts:
            unique_parts.append(part)
    return unique_parts[:5]


def _pick_questions_for_requirement(
    questions: list[Question],
    requirement: dict[str, Any],
    selected_ids: set[int],
) -> list[Question]:
    ranked: list[tuple[int, Question]] = []
    for question in questions:
        if question.id in selected_ids:
            continue
        if requirement["allowed_types"] and question.type not in requirement["allowed_types"]:
            continue
        score = _score_question_for_requirement(question, requirement)
        ranked.append((score, question))

    ranked.sort(key=lambda item: (-item[0], -(item[1].id or 0)))
    if not ranked:
        return []

    top = ranked[: max(requirement["count"] * 3, requirement["count"])]
    randomizer = Random(requirement["label"] + "-" + "-".join(requirement["keywords"]))
    if requirement["keywords"]:
        head = [item for item in top if item[0] > 0]
        tail = [item for item in top if item[0] <= 0]
        randomizer.shuffle(tail)
        ordered = head + tail
    else:
        ordered = top[:]
        randomizer.shuffle(ordered)
    return [item[1] for item in ordered[: requirement["count"]]]


def _score_question_for_requirement(question: Question, requirement: dict[str, Any]) -> int:
    if not requirement["keywords"]:
        return 1
    haystacks = [str(question.stem or ""), str(question.analysis or "")]
    extra_meta = question.extra_meta or {}
    haystacks.extend(str(tag) for tag in extra_meta.get("ability_tags", []))
    full_text = " ".join(haystacks).lower()
    score = 0
    for keyword in requirement["keywords"]:
        if keyword.lower() in full_text:
            score += 4
    return score


def _get_subject_by_name(db: Session, subject_name: str) -> Subject:
    """
    处理  get subject by name 请求并返回结果。
    """
    subject_obj = db.scalar(select(Subject).where(Subject.name == subject_name))
    if not subject_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    return subject_obj


def _get_teacher_class(db: Session, teacher_id: int, class_id: int) -> ClassRoom:
    """
    处理  get teacher class 请求并返回结果。
    """
    classroom = db.scalar(select(ClassRoom).where(ClassRoom.id == class_id, ClassRoom.teacher_id == teacher_id))
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    return classroom


def _get_teacher_exam(db: Session, teacher_id: int, exam_id: int) -> Exam:
    """
    处理  get teacher exam 请求并返回结果。
    """
    exam = db.scalar(select(Exam).where(Exam.id == exam_id, Exam.created_by == teacher_id))
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    return exam


def _teacher_student_risk_level(latest_score: float, avg_correct_rate: float) -> str:
    if latest_score < 45 or avg_correct_rate < 0.45:
        return "high"
    if latest_score < 60 or avg_correct_rate < 0.6:
        return "medium"
    return "low"


def _replace_question_relations(db: Session, question_id: int, options, knowledge_point_ids) -> None:
    """
    处理  replace question relations 请求并返回结果。
    """
    if options is not None:
        db.query(QuestionOption).filter(QuestionOption.question_id == question_id).delete()
        for index, option in enumerate(options, start=1):
            db.add(QuestionOption(question_id=question_id, option_key=option.key, content=option.content, sort_order=index))
    if knowledge_point_ids is not None:
        db.query(QuestionKnowledgePoint).filter(QuestionKnowledgePoint.question_id == question_id).delete()
        for knowledge_point_id in knowledge_point_ids:
            db.add(QuestionKnowledgePoint(question_id=question_id, knowledge_point_id=knowledge_point_id))
    db.commit()


def _replace_exam_relations(db: Session, exam_id: int, class_ids, question_items) -> None:
    """
    处理  replace exam relations 请求并返回结果。
    """
    if class_ids is not None:
        db.query(ExamClass).filter(ExamClass.exam_id == exam_id).delete()
        for class_id in class_ids:
            db.add(ExamClass(exam_id=exam_id, class_id=class_id))
    if question_items is not None:
        db.query(ExamQuestion).filter(ExamQuestion.exam_id == exam_id).delete()
        for item in question_items:
            db.add(ExamQuestion(exam_id=exam_id, question_id=item.question_id, score=item.score, order_no=item.order_no, section_name=item.section_name))
        if len(question_items) == 0:
            _cleanup_study_tasks_for_exam(db, exam_id)
    db.commit()


def _count_valid_exam_questions(db: Session, exam_id: int) -> int:
    """
    统计 exam 仍然有效（题目实体存在）的题目数量。
    """
    return db.scalar(
        select(func.count())
        .select_from(ExamQuestion)
        .join(Question, Question.id == ExamQuestion.question_id)
        .where(ExamQuestion.exam_id == exam_id)
    ) or 0


def _cleanup_study_tasks_for_exam(db: Session, exam_id: int) -> None:
    """
    清理来源于指定考试的学习计划与学习任务，避免学生端残留无效待办。
    """
    plan_ids = db.scalars(select(StudyPlan.id).where(StudyPlan.source_exam_id == exam_id)).all()
    if not plan_ids:
        return
    db.query(StudyTask).filter(StudyTask.plan_id.in_(plan_ids)).delete(synchronize_session=False)
    db.query(StudyPlan).filter(StudyPlan.id.in_(plan_ids)).delete(synchronize_session=False)

import json
import re
from datetime import datetime, UTC, timedelta
import logging
from time import perf_counter
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.core.config import settings
from app.core.response import success_response
from app.models.academic import ClassRoom, ClassStudent, Subject
from app.models.exam import Exam, ExamClass, ExamQuestion, ExamSubmission, SubmissionAnswer, SubmissionBehaviorEvent
from app.models.question import Question, QuestionKnowledgePoint, QuestionOption
from app.models.user import AITask, ReviewItem, StudyPlan, StudyTask, User
from app.schemas.student import BatchSaveAnswerRequest, BehaviorReportRequest, SaveAnswerRequest, StartExamRequest, StudentAIFollowUpRequest, StudentRetakeRequestCreate, StudyTaskActionRequest, SubmitExamRequest
from app.services.learning import build_submission_analysis, generate_study_plan
from app.services.ai_client import request_chat_completion
from app.services.prompt_loader import render_prompt
from app.services.realtime import realtime_events, submission_channel
from app.services.scoring import OBJECTIVE_TYPES, SUBJECTIVE_TYPES, compute_objective_score, parse_answer, serialize_answer
from app.services.student_growth_ai import build_growth_ability_profile
from app.services.tasks import complete_ai_task, mark_ai_task_running, queue_ai_task


router = APIRouter()
logger = logging.getLogger(__name__)


def _study_task_type_label(task_type: str | None) -> str:
    mapping = {
        "wrong_question_review": "错题回顾",
        "knowledge_review": "知识点复习",
        "consolidation": "巩固训练",
    }
    normalized = (task_type or "").strip().lower()
    return mapping.get(normalized, "综合复习")


def _extract_target_question_count_from_title(title: str | None, default_count: int = 6) -> int:
    """
    从任务标题中提取“（X题）”作为目标题量，避免计划页与任务页题数不一致。
    """
    raw_title = (title or "").strip()
    if not raw_title:
        return default_count
    match = re.search(r"[（(]\s*(\d+)\s*题\s*[）)]", raw_title)
    if not match:
        return default_count
    try:
        value = int(match.group(1))
    except (TypeError, ValueError):
        return default_count
    return max(1, min(value, 30))

GROWTH_PROFILE_CACHE_TTL = timedelta(minutes=20)
_growth_profile_cache: dict[str, dict[str, Any]] = {}
STUDY_ARTIFACT_CLEANUP_TTL = timedelta(minutes=10)
_study_artifact_cleanup_cache: dict[int, datetime] = {}


@router.get("/student/exams")
def list_student_exams(
    status: str | None = None,
    subject: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """
    列出 student exams 的数据列表。
    """
    class_ids = db.scalars(select(ClassStudent.class_id).where(ClassStudent.student_id == current_user.id, ClassStudent.status == "active")).all()
    if not class_ids:
        return success_response({"items": [], "total": 0})
    question_count_subquery = (
        select(func.count())
        .select_from(ExamQuestion)
        .join(Question, Question.id == ExamQuestion.question_id)
        .where(ExamQuestion.exam_id == Exam.id)
        .scalar_subquery()
    )
    query = (
        select(Exam)
        .join(ExamClass, ExamClass.exam_id == Exam.id)
        .where(ExamClass.class_id.in_(class_ids), question_count_subquery > 0)
    )
    now = datetime.now(UTC)
    if status == "upcoming":
        query = query.where(Exam.start_time > now, Exam.status.in_(["published", "ongoing"]))
    elif status == "ongoing":
        query = query.where(Exam.start_time <= now, Exam.end_time >= now, Exam.status.in_(["published", "ongoing"]))
    elif status == "finished":
        query = query.where(Exam.end_time < now)
    if subject:
        subject_obj = db.scalar(select(Subject).where(Subject.name == subject))
        if subject_obj:
            query = query.where(Exam.subject_id == subject_obj.id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(Exam.start_time.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return success_response({"items": [_serialize_exam_list_item(db, item, current_user.id) for item in items], "total": total})


@router.get("/student/exams/detail")
def get_student_exam_detail(exam_id: int, current_user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    """
    获取 student exam detail 相关数据。
    """
    exam = _get_student_exam(db, current_user.id, exam_id)
    now = datetime.now(UTC)
    start_time = _as_utc(exam.start_time)
    end_time = _as_utc(exam.end_time)
    can_start = start_time <= now <= end_time and exam.status in {"published", "ongoing"}
    return success_response({"exam": _serialize_exam_detail(db, exam), "can_start": can_start, "rules": {"allow_review": exam.allow_review, "random_question_order": exam.random_question_order}})


@router.post("/student/exams/start")
def start_exam(payload: StartExamRequest, current_user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    """
    学生开始考试接口
    
    验证当前学生是否具备参加该考试的权限，若首次开始则在数据库中初始化一条 ExamSubmission 记录。
    生成初始的草稿数据并将状态设定为 in_progress。最终返回一个有效的 submission_id 供答题阶段使用。
    """
    exam = _get_student_exam(db, current_user.id, payload.exam_id)
    now = datetime.now(UTC)
    approved_retake_request = db.scalar(
        select(AITask)
        .where(
            AITask.type == "retake_request",
            AITask.resource_type == "exam",
            AITask.resource_id == exam.id,
            AITask.created_by == current_user.id,
            AITask.status == "approved",
        )
        .order_by(AITask.created_at.desc())
    )
    allow_retake_start = approved_retake_request is not None

    if exam.status not in {"published", "ongoing"} and not allow_retake_start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam is not available")
    if not allow_retake_start and not (_as_utc(exam.start_time) <= now <= _as_utc(exam.end_time)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam is not in progress")

    relation = db.scalar(
        select(ClassStudent)
        .join(ExamClass, ExamClass.class_id == ClassStudent.class_id)
        .where(ClassStudent.student_id == current_user.id, ClassStudent.status == "active", ExamClass.exam_id == exam.id)
        .limit(1)
    )
    if not relation:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student is not bound to any class")
    submission = db.scalar(select(ExamSubmission).where(ExamSubmission.exam_id == exam.id, ExamSubmission.student_id == current_user.id))
    if not submission:
        submission = ExamSubmission(
            exam_id=exam.id,
            student_id=current_user.id,
            class_id=relation.class_id,
            teacher_id=exam.created_by,
            status="in_progress",
            started_at=datetime.now(UTC),
            deadline_at=exam.end_time,
            review_status="pending",
            ai_analysis_status="pending",
        )
        db.add(submission)

    if allow_retake_start:
        submission.status = "in_progress"
        submission.started_at = now
        submission.submitted_at = None
        submission.deadline_at = now + timedelta(minutes=max(1, int(exam.duration_minutes or 60)))
        submission.objective_score = 0
        submission.subjective_score = 0
        submission.total_score = 0
        submission.correct_rate = 0
        submission.ranking_in_class = None
        submission.review_status = "pending"
        submission.ai_analysis_status = "pending"
        db.query(SubmissionAnswer).filter(SubmissionAnswer.submission_id == submission.id).delete(synchronize_session=False)
        db.query(SubmissionBehaviorEvent).filter(SubmissionBehaviorEvent.submission_id == submission.id).delete(synchronize_session=False)
        approved_retake_request.status = "consumed"
        approved_retake_request.result_payload = {
            "consumed_at": now.isoformat(),
            "submission_id": submission.id,
        }
        db.add(approved_retake_request)
    elif submission.status != "in_progress":
        submission.status = "in_progress"
        submission.started_at = submission.started_at or now
        submission.deadline_at = _as_utc(exam.end_time)

    db.add(submission)
    db.commit()
    db.refresh(submission)
    realtime_events.publish(
        submission_channel(exam.id, submission.id),
        "submission_started",
        {"exam_id": exam.id, "submission": _serialize_submission(submission)},
    )
    return success_response({"submission": _serialize_submission(submission), "paper_token": f"paper_{submission.id}"})


@router.get("/student/exams/paper")
def get_exam_paper(exam_id: int, submission_id: int, current_user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    """
    获取 exam paper 相关数据。
    """
    exam = _get_student_exam(db, current_user.id, exam_id)
    submission = _get_student_submission(db, current_user.id, submission_id)
    if submission.exam_id != exam.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    question_items = db.scalars(select(ExamQuestion).where(ExamQuestion.exam_id == exam.id).order_by(ExamQuestion.order_no.asc())).all()
    questions = []
    for item in question_items:
        question = db.get(Question, item.question_id)
        if not question:
            continue
        options = db.scalars(select(QuestionOption).where(QuestionOption.question_id == item.question_id).order_by(QuestionOption.sort_order.asc())).all()
        questions.append({
            "question_id": question.id,
            "type": question.type,
            "stem": question.stem,
            "score": float(item.score),
            "options": [{"key": opt.option_key, "content": opt.content} for opt in options],
        })
    deadline = _as_utc(submission.deadline_at) if submission.deadline_at else _as_utc(exam.end_time)
    remaining_seconds = max(0, int((deadline - datetime.now(UTC)).total_seconds()))
    return success_response({"exam": _serialize_exam_detail(db, exam), "questions": questions, "remaining_seconds": remaining_seconds})


@router.post("/student/exams/retake-request")
def create_retake_request(
    payload: StudentRetakeRequestCreate,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """
    学生发起重考申请，等待教师审批。
    """
    exam = _get_student_exam(db, current_user.id, payload.exam_id)
    submission = db.scalar(
        select(ExamSubmission).where(ExamSubmission.exam_id == exam.id, ExamSubmission.student_id == current_user.id)
    )
    if not submission or submission.status not in {"submitted", "reviewed"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅已提交考试可申请重考")

    latest_request = db.scalar(
        select(AITask)
        .where(
            AITask.type == "retake_request",
            AITask.resource_type == "exam",
            AITask.resource_id == exam.id,
            AITask.created_by == current_user.id,
        )
        .order_by(AITask.created_at.desc())
    )
    if latest_request and latest_request.status in {"pending", "approved"}:
        return success_response(
            {
                "request_id": latest_request.id,
                "status": latest_request.status,
                "created_at": latest_request.created_at.isoformat(),
            },
            "retake request already exists",
        )

    reason = (payload.reason or "").strip()[:500] if payload.reason else "希望再次尝试本场考试"
    request_task = AITask(
        task_id=f"retake_{exam.id}_{current_user.id}_{int(datetime.now(UTC).timestamp())}",
        type="retake_request",
        status="pending",
        progress=0,
        resource_type="exam",
        resource_id=exam.id,
        created_by=current_user.id,
        request_payload={
            "exam_id": exam.id,
            "student_id": current_user.id,
            "student_name": current_user.name,
            "reason": reason,
            "submission_id": submission.id,
        },
    )
    db.add(request_task)
    db.commit()
    db.refresh(request_task)
    return success_response({"request_id": request_task.id, "status": request_task.status, "created_at": request_task.created_at.isoformat()})


@router.post("/student/exams/answer/save")
def save_answer(payload: SaveAnswerRequest, current_user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    """
    处理 save answer 请求并返回结果。
    """
    submission = _get_student_submission(db, current_user.id, payload.submission_id)
    answer = db.scalar(select(SubmissionAnswer).where(SubmissionAnswer.submission_id == submission.id, SubmissionAnswer.question_id == payload.question_id))
    if not answer:
        answer = SubmissionAnswer(submission_id=submission.id, exam_id=payload.exam_id, question_id=payload.question_id)
    answer.answer_content = serialize_answer(payload.answer) if payload.answer is not None else None
    answer.answer_text = payload.answer_text
    answer.spent_seconds = payload.spent_seconds
    answer.mark_difficult = payload.mark_difficult
    answer.favorite = payload.favorite
    answer.answer_version = (answer.answer_version or 0) + 1
    db.add(answer)
    db.commit()
    db.refresh(answer)
    realtime_events.publish(
        submission_channel(payload.exam_id, submission.id),
        "answer_saved",
        {"submission_id": submission.id, "question_id": payload.question_id, "answer_version": answer.answer_version},
    )
    return success_response({"saved": True, "answer_version": answer.answer_version, "saved_at": answer.updated_at.isoformat()})


@router.post("/student/exams/answers/save-batch")
def save_answers_batch(payload: BatchSaveAnswerRequest, current_user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    """
    处理 save answers batch 请求并返回结果。
    """
    submission = _get_student_submission(db, current_user.id, payload.submission_id)
    saved_count = 0
    for item in payload.answers:
        answer = db.scalar(select(SubmissionAnswer).where(SubmissionAnswer.submission_id == submission.id, SubmissionAnswer.question_id == item.question_id))
        if not answer:
            answer = SubmissionAnswer(submission_id=submission.id, exam_id=payload.exam_id, question_id=item.question_id)
        answer.answer_content = serialize_answer(item.answer) if item.answer is not None else None
        answer.answer_text = item.answer_text
        answer.spent_seconds = item.spent_seconds
        answer.answer_version = (answer.answer_version or 0) + 1
        db.add(answer)
        saved_count += 1
    db.commit()
    return success_response({"saved_count": saved_count})


@router.post("/student/exams/behavior/report")
def report_behavior(payload: BehaviorReportRequest, current_user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    """
    处理 report behavior 请求并返回结果。
    """
    submission = _get_student_submission(db, current_user.id, payload.submission_id)
    for event in payload.events:
        db.add(SubmissionBehaviorEvent(submission_id=submission.id, exam_id=payload.exam_id, question_id=event.question_id, event_type=event.event_type, payload=event.payload, occurred_at=event.occurred_at))
    db.commit()
    realtime_events.publish(
        submission_channel(payload.exam_id, submission.id),
        "behavior_reported",
        {"submission_id": submission.id, "event_count": len(payload.events)},
    )
    return success_response({"received": True, "event_count": len(payload.events)})


@router.get("/student/exams/pre-submit-check")
def pre_submit_check(exam_id: int, submission_id: int, current_user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    """
    处理 pre submit check 请求并返回结果。
    """
    _get_student_exam(db, current_user.id, exam_id)
    submission = _get_student_submission(db, current_user.id, submission_id)
    question_ids = db.scalars(select(ExamQuestion.question_id).where(ExamQuestion.exam_id == exam_id)).all()
    answers = db.scalars(select(SubmissionAnswer).where(SubmissionAnswer.submission_id == submission.id)).all()
    answer_map = {item.question_id: item for item in answers}
    unanswered = [question_id for question_id in question_ids if question_id not in answer_map or (answer_map[question_id].answer_content is None and not answer_map[question_id].answer_text)]
    marked = [item.question_id for item in answers if item.mark_difficult]
    subjective_warnings = [f"题目 {question_id} 为主观题，建议检查作答完整性" for question_id in unanswered]
    ai_reminders = ["当前存在未作答题目，请确认是否提交"] if unanswered else []
    return success_response({"unanswered_question_ids": unanswered, "marked_question_ids": marked, "subjective_warnings": subjective_warnings, "ai_reminders": ai_reminders})


@router.post("/student/exams/submit")
def submit_exam(payload: SubmitExamRequest, current_user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    """
    学生交卷接口
    
    允许学生主动交卷或自动交卷。将草稿状态修改为正式提交并冻结做题修改，
    计算客观题分数，分发 AI 评分任务，修改考试状态为已提交（或已完成，视题型而定）。
    """
    if not payload.confirm_submit:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="confirm_submit must be true")
    exam = _get_student_exam(db, current_user.id, payload.exam_id)
    submission = _get_student_submission(db, current_user.id, payload.submission_id)
    answers = db.scalars(select(SubmissionAnswer).where(SubmissionAnswer.submission_id == submission.id)).all()
    question_items = db.scalars(select(ExamQuestion).where(ExamQuestion.exam_id == exam.id)).all()
    question_score_map = {item.question_id: float(item.score) for item in question_items}
    objective_total = 0.0
    triggered_tasks = []

    for answer in answers:
        question = db.get(Question, answer.question_id)
        if not question:
            continue
        standard_answer = parse_answer(question.answer_text)
        student_answer = parse_answer(answer.answer_content) if answer.answer_content else answer.answer_text
        is_correct, score = compute_objective_score(question.type, standard_answer, student_answer, question_score_map.get(question.id, 0.0))
        answer.is_correct = is_correct
        if question.type in OBJECTIVE_TYPES:
            answer.score = score
            objective_total += score
            if not is_correct:
                answer.ai_error_analysis = {"reason": "答案与标准答案不一致", "suggestion": "建议复习相关知识点"}
        db.add(answer)
        if question.type in SUBJECTIVE_TYPES:
            review_item = db.scalar(select(ReviewItem).where(ReviewItem.submission_id == submission.id, ReviewItem.question_id == question.id))
            if not review_item:
                db.add(ReviewItem(exam_id=exam.id, submission_id=submission.id, question_id=question.id, student_id=current_user.id, ai_suggest_score=0, review_status="pending", ai_comment="待 AI 主观题评分"))

    submission.objective_score = objective_total
    submission.total_score = objective_total + float(submission.subjective_score or 0)
    submission.status = "submitted"
    submission.submitted_at = datetime.now(UTC)
    submission.correct_rate = objective_total / float(exam.total_score) if float(exam.total_score) else 0
    submission.ai_analysis_status = "completed"
    db.add(submission)
    db.commit()

    analysis_task = queue_ai_task(db, "exam_analysis", "submission", submission.id, current_user.id, {"submission_id": submission.id})
    mark_ai_task_running(db, analysis_task, progress=30)
    analysis_result = build_submission_analysis(db, submission, exam)
    complete_ai_task(db, analysis_task, result_payload=analysis_result)
    triggered_tasks.append({"task_id": analysis_task.task_id, "type": analysis_task.type, "status": analysis_task.status})

    study_plan_task = queue_ai_task(db, "study_plan_generate", "submission", submission.id, current_user.id, {"submission_id": submission.id})
    mark_ai_task_running(db, study_plan_task, progress=40)
    study_plan_result = generate_study_plan(db, submission, exam)
    complete_ai_task(db, study_plan_task, result_payload=study_plan_result)
    triggered_tasks.append({"task_id": study_plan_task.task_id, "type": study_plan_task.type, "status": study_plan_task.status})

    realtime_events.publish(
        submission_channel(exam.id, submission.id),
        "submission_submitted",
        {"submission": _serialize_submission(submission), "triggered_tasks": triggered_tasks},
    )
    return success_response({"submission": _serialize_submission(submission), "triggered_tasks": triggered_tasks})


@router.get("/student/dashboard/overview")
def student_dashboard(subject: str | None = None, current_user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    """
    学生主页概览接口
    
    请求学生的总览数据，包括近期待考数量、基于最近考试数据提取的薄弱知识点分析，
    以及系统生成的个性化待办学习任务等，驱动学生控制台面板的内容呈现。
    """
    started_at = perf_counter()
    now = datetime.now(UTC)
    _maybe_cleanup_invalid_study_artifacts_for_student(db, current_user.id, now)
    upcoming_count = db.scalar(
        select(func.count()).select_from(Exam)
        .join(ExamClass, ExamClass.exam_id == Exam.id)
        .join(ClassStudent, ClassStudent.class_id == ExamClass.class_id)
        .outerjoin(ExamSubmission, (ExamSubmission.exam_id == Exam.id) & (ExamSubmission.student_id == current_user.id))
        .where(
            ClassStudent.student_id == current_user.id, 
            Exam.status.in_(['published', 'ongoing']),
            Exam.start_time <= now,
            Exam.end_time >= now,
            (ExamSubmission.id == None) | (ExamSubmission.status != 'submitted')
        )
    ) or 0
    recent_exams = db.scalars(
        select(Exam)
        .join(ExamClass, ExamClass.exam_id == Exam.id)
        .join(ClassStudent, ClassStudent.class_id == ExamClass.class_id)
        .outerjoin(ExamSubmission, (ExamSubmission.exam_id == Exam.id) & (ExamSubmission.student_id == current_user.id))
        .where(
            ClassStudent.student_id == current_user.id, 
            Exam.status.in_(['published', 'ongoing']),
            Exam.end_time >= now,
            (ExamSubmission.id == None) | (ExamSubmission.status != 'submitted')
        ).order_by(Exam.start_time.asc()).limit(5)
    ).all()
    latest_submission = db.scalar(select(ExamSubmission).where(ExamSubmission.student_id == current_user.id).order_by(ExamSubmission.created_at.desc()))
    valid_plan_subquery = (
        select(StudyPlan.id)
        .outerjoin(Exam, Exam.id == StudyPlan.source_exam_id)
        .where(
            StudyPlan.student_id == current_user.id,
            (StudyPlan.source_exam_id == None)
            | (
                select(func.count())
                .select_from(ExamQuestion)
                .join(Question, Question.id == ExamQuestion.question_id)
                .where(ExamQuestion.exam_id == StudyPlan.source_exam_id)
                .scalar_subquery()
                > 0
            ),
        )
    )
    recommended_tasks = db.scalars(
        select(StudyTask)
        .where(
            StudyTask.student_id == current_user.id,
            StudyTask.plan_id.in_(valid_plan_subquery),
            StudyTask.status.in_(["pending", "in_progress"]),
            StudyTask.completed_at == None,
        )
        .order_by(StudyTask.priority.asc(), StudyTask.created_at.desc())
        .limit(5)
    ).all()

    stat_query = (
        select(func.count(SubmissionAnswer.id), func.max(SubmissionAnswer.updated_at))
        .select_from(SubmissionAnswer)
        .join(ExamSubmission, SubmissionAnswer.submission_id == ExamSubmission.id)
        .where(ExamSubmission.student_id == current_user.id)
        .where(ExamSubmission.status.in_(["submitted", "completed", "reviewed"]))
    )
    answer_count, latest_answer_at = db.execute(stat_query).first() or (0, None)
    fingerprint = f"{int(answer_count or 0)}:{latest_answer_at.isoformat() if latest_answer_at else 'none'}"

    cache_key = f"{current_user.id}:dashboard_overview"
    cached = _growth_profile_cache.get(cache_key)
    cache_hit = False
    growth_payload: dict[str, Any] = {}
    if cached:
        cache_time = cached.get("cached_at")
        if isinstance(cache_time, datetime) and now - cache_time <= GROWTH_PROFILE_CACHE_TTL and cached.get("fingerprint") == fingerprint:
            payload = cached.get("payload")
            if isinstance(payload, dict):
                growth_payload = payload
                cache_hit = True

    if not cache_hit:
        answer_rows = db.execute(
            select(SubmissionAnswer, Question, Subject)
            .join(ExamSubmission, SubmissionAnswer.submission_id == ExamSubmission.id)
            .join(Question, SubmissionAnswer.question_id == Question.id)
            .outerjoin(Subject, Question.subject_id == Subject.id)
            .where(ExamSubmission.student_id == current_user.id)
            .where(ExamSubmission.status.in_(["submitted", "completed", "reviewed"]))
            .order_by(SubmissionAnswer.updated_at.desc())
            .limit(180)
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
        growth_payload = build_growth_ability_profile(answer_records, refine_with_llm=False)
        _growth_profile_cache[cache_key] = {
            "fingerprint": fingerprint,
            "cached_at": now,
            "payload": growth_payload,
        }

    ability_profile = growth_payload.get("ability_profile") if isinstance(growth_payload, dict) else []
    if not isinstance(ability_profile, list):
        ability_profile = []
    ability_profile_summary = {
        str(item.get("name") or f"能力{i + 1}"): round(float(item.get("accuracy") or 0), 2)
        for i, item in enumerate(ability_profile[:3])
    }
    if not ability_profile_summary:
        ability_profile_summary = {"审题能力": 0.0, "计算能力": 0.0, "综合应用能力": 0.0}

    response_payload = success_response(
        {
            "upcoming_exam_count": upcoming_count,
            "recent_exams": [{"id": item.id, "title": item.title} for item in recent_exams],
            "latest_result_summary": _serialize_submission(latest_submission) if latest_submission else None,
            "ai_reminders": ["建议优先复习最近一次考试中的高频错题。"],
            "ability_profile_summary": ability_profile_summary,
            "recommended_tasks": [{"task_id": item.id, "title": item.title, "priority": item.priority} for item in recommended_tasks],
        }
    )
    elapsed_ms = int((perf_counter() - started_at) * 1000)
    logger.info(
        "API perf path=/student/dashboard/overview user_id=%s elapsed_ms=%d cache_hit=%s answer_count=%d",
        current_user.id,
        elapsed_ms,
        cache_hit,
        int(answer_count or 0),
    )
    return response_payload


def _maybe_cleanup_invalid_study_artifacts_for_student(db: Session, student_id: int, now: datetime) -> None:
    last_cleanup = _study_artifact_cleanup_cache.get(student_id)
    if isinstance(last_cleanup, datetime) and now - last_cleanup <= STUDY_ARTIFACT_CLEANUP_TTL:
        return
    _cleanup_invalid_study_artifacts_for_student(db, student_id)
    _study_artifact_cleanup_cache[student_id] = now


@router.get("/student/results/overview")
def result_overview(exam_id: int, current_user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    """
    处理 result overview 请求并返回结果。
    """
    submission = db.scalar(select(ExamSubmission).where(ExamSubmission.exam_id == exam_id, ExamSubmission.student_id == current_user.id))
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
    exam = db.get(Exam, exam_id)
    score_distribution = db.scalars(select(SubmissionAnswer).where(SubmissionAnswer.submission_id == submission.id)).all()
    return success_response(
        {
            "submission": _serialize_submission(submission),
            "score_summary": {"total_score": float(submission.total_score), "objective_score": float(submission.objective_score), "subjective_score": float(submission.subjective_score)},
            "ranking_summary": {"ranking_in_class": submission.ranking_in_class},
            "type_score_distribution": [{"question_id": item.question_id, "score": float(item.score)} for item in score_distribution],
            "ai_summary": f"《{exam.title if exam else '当前考试'}》已完成分析，建议重点复习错题。",
            "risk_alerts": ["若主观题得分偏低，建议查看教师复核结果。"],
        }
    )


@router.get("/student/results/question-analysis")
def get_question_analysis(
    exam_id: int,
    question_id: int,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """
    返回学生单题解析详情，包含题目、作答对比与复习建议。
    """
    submission = db.scalar(select(ExamSubmission).where(ExamSubmission.exam_id == exam_id, ExamSubmission.student_id == current_user.id))
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    answer = db.scalar(
        select(SubmissionAnswer).where(
            SubmissionAnswer.submission_id == submission.id,
            SubmissionAnswer.question_id == question_id,
        )
    )
    if not answer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question answer not found in submission")

    exam_item = db.scalar(
        select(ExamQuestion).where(ExamQuestion.exam_id == exam_id, ExamQuestion.question_id == question_id)
    )

    options = db.scalars(
        select(QuestionOption)
        .where(QuestionOption.question_id == question_id)
        .order_by(QuestionOption.sort_order.asc())
    ).all()

    standard_answer = parse_answer(question.answer_text)
    student_answer = parse_answer(answer.answer_content) if answer and answer.answer_content else (answer.answer_text if answer else None)
    full_score = float(exam_item.score) if exam_item else float(question.score or 0)
    gain_score = float(answer.score or 0) if answer else 0.0

    is_correct = answer.is_correct if answer else None
    if is_correct is None and question.type in OBJECTIVE_TYPES:
        is_correct, _ = compute_objective_score(question.type, standard_answer, student_answer, full_score)

    stem_text = str(question.stem or "").replace("\n", " ").strip()
    stem_excerpt = stem_text[:36] + ("..." if len(stem_text) > 36 else "")

    if student_answer is None or (isinstance(student_answer, str) and not student_answer.strip()):
        diagnosis_type = "未作答"
        diagnosis_reason = f"该题（{stem_excerpt}）没有提交有效答案，建议先完成一次独立作答再对照解析。"
    elif is_correct is False:
        diagnosis_type = "答题错误"
        diagnosis_reason = f"你的答案与标准答案不一致（你的答案：{student_answer}；标准答案：{standard_answer}），建议先定位审题还是概念问题。"
    elif is_correct is True:
        diagnosis_type = "已掌握"
        diagnosis_reason = f"该题作答正确（{stem_excerpt}），建议做1-2道同类变式题巩固。"
    else:
        diagnosis_type = "待复核"
        diagnosis_reason = "该题属于主观题，建议结合解析与教师批注进行结构化复盘。"

    if question.type in {"single_choice", "multiple_choice"}:
        fix_steps = [
            "先读题干关键词，再逐项排除明显错误选项。",
            "对每个选项写一句“为何选/不选”的理由。",
            "对照解析，记录本题错因标签（审题/概念/粗心）。",
        ]
    elif question.type == "judge":
        fix_steps = [
            "先找题干中的绝对化词语（一定/都/必然）。",
            "写出支持或反例，再做判断。",
            "对照解析，记录易混概念。",
        ]
    elif question.type == "blank":
        fix_steps = [
            "先根据题干回忆关键术语或公式。",
            "补全后检查单位、符号或术语拼写。",
            "对照解析，整理本题模板答案。",
        ]
    else:
        fix_steps = [
            "先重读题干，圈出限制条件与关键变量。",
            "独立再做一遍并写出完整步骤。",
            "对照标准答案与解析，记录错因标签。",
        ]

    return success_response(
        {
            "question": {
                "question_id": question.id,
                "question_type": question.type,
                "stem": question.stem,
                "analysis": question.analysis,
                "options": [{"key": item.option_key, "content": item.content} for item in options],
            },
            "answer": {
                "student_answer": student_answer,
                "standard_answer": standard_answer,
                "is_correct": is_correct,
                "gain_score": gain_score,
                "full_score": full_score,
            },
            "diagnosis": {
                "type": diagnosis_type,
                "reason": diagnosis_reason,
                "stem_focus": stem_excerpt,
                "fix_steps": fix_steps,
                "next_actions": [
                    "完成本题后，再练 2 道同类型题目。",
                    "将本题加入错题本并在 24 小时内进行二次回顾。",
                ],
            },
        }
    )


@router.post("/student/ai-chat/follow-up")
def student_ai_follow_up(
    payload: StudentAIFollowUpRequest,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """
    学生错题追问：基于单题上下文生成简短、有针对性的辅导回答。
    """
    submission = db.scalar(
        select(ExamSubmission).where(ExamSubmission.exam_id == payload.exam_id, ExamSubmission.student_id == current_user.id)
    )
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

    question = db.get(Question, payload.question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    answer = db.scalar(
        select(SubmissionAnswer).where(
            SubmissionAnswer.submission_id == submission.id,
            SubmissionAnswer.question_id == payload.question_id,
        )
    )

    standard_answer = parse_answer(question.answer_text)
    student_answer = parse_answer(answer.answer_content) if answer and answer.answer_content else (answer.answer_text if answer else None)

    normalized_msgs = [m for m in payload.messages if m.content and m.content.strip()]
    if not normalized_msgs:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="messages is required")

    latest_user_question = normalized_msgs[-1].content.strip()
    system_prompt = render_prompt("student_follow_up_system.jinja")
    user_prompt = render_prompt(
        "student_follow_up_user.jinja",
        question_type=question.type,
        stem=(question.stem or '')[:200],
        student_answer=student_answer if student_answer is not None else "未作答",
        standard_answer=standard_answer if standard_answer is not None else "无",
        analysis=(question.analysis or '')[:200],
        latest_user_question=latest_user_question,
    )

    reply_text = ""
    for cfg in settings.llm_configs:
        try:
            reply_text = request_chat_completion(
                cfg=cfg,
                scene="student_follow_up_chat",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
            )
            if reply_text:
                break
        except Exception:
            continue

    if not reply_text:
        if student_answer is None or (isinstance(student_answer, str) and not student_answer.strip()):
            reply_text = "你这题先别急看答案，先按题干写出已知条件，再尝试排除两个错误选项，最后再核对解析。"
        else:
            reply_text = f"先对比你的答案“{student_answer}”与标准答案“{standard_answer}”的差异，定位是审题还是概念错误，再做1道同类题验证。"

    return success_response(
        {
            "reply": reply_text,
            "context": {
                "exam_id": payload.exam_id,
                "question_id": payload.question_id,
            },
        }
    )


def _get_student_exam(db: Session, student_id: int, exam_id: int) -> Exam:
    """
    处理  get student exam 请求并返回结果。
    """
    class_ids = db.scalars(select(ClassStudent.class_id).where(ClassStudent.student_id == student_id, ClassStudent.status == "active")).all()
    exam = db.scalar(select(Exam).join(ExamClass, ExamClass.exam_id == Exam.id).where(Exam.id == exam_id, ExamClass.class_id.in_(class_ids)))
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    question_count = db.scalar(
        select(func.count())
        .select_from(ExamQuestion)
        .join(Question, Question.id == ExamQuestion.question_id)
        .where(ExamQuestion.exam_id == exam.id)
    ) or 0
    if question_count <= 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    return exam


def _get_student_submission(db: Session, student_id: int, submission_id: int) -> ExamSubmission:
    """
    处理  get student submission 请求并返回结果。
    """
    submission = db.scalar(select(ExamSubmission).where(ExamSubmission.id == submission_id, ExamSubmission.student_id == student_id))
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    return submission


def _as_utc(dt: datetime) -> datetime:
    """
    将数据库中可能出现的 naive/aware datetime 统一为 UTC aware。
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _as_utc_iso(dt: datetime) -> str:
    """
    将时间统一序列化为 UTC ISO 字符串并带 Z 后缀。
    """
    return _as_utc(dt).isoformat().replace("+00:00", "Z")


def _serialize_exam_list_item(db: Session, exam: Exam, student_id: int) -> dict:
    """
    序列化 exam list item 对象为字典。
    """
    subject = db.get(Subject, exam.subject_id)
    submission = db.scalar(
        select(ExamSubmission)
        .where(
            ExamSubmission.exam_id == exam.id,
            ExamSubmission.student_id == student_id,
            ExamSubmission.created_at >= exam.created_at,
        )
        .order_by(ExamSubmission.created_at.desc())
    )
    latest_retake_request = db.scalar(
        select(AITask)
        .where(
            AITask.type == "retake_request",
            AITask.resource_type == "exam",
            AITask.resource_id == exam.id,
            AITask.created_by == student_id,
        )
        .order_by(AITask.created_at.desc())
    )

    submitted_statuses = {"submitted", "completed", "reviewed"}
    answered_count = 0
    if submission:
        answered_count = db.scalar(
            select(func.count())
            .select_from(SubmissionAnswer)
            .where(
                SubmissionAnswer.submission_id == submission.id,
                (SubmissionAnswer.answer_content != None) | (SubmissionAnswer.answer_text != None),
            )
        ) or 0

    has_submission_evidence = False
    if submission:
        has_submission_evidence = bool(
            answered_count > 0
            or float(submission.total_score or 0) > 0
            or str(submission.review_status or "").lower() == "reviewed"
        )

    has_real_submission = bool(
        submission
        and str(submission.status or "").lower() in submitted_statuses
        and submission.submitted_at is not None
        and has_submission_evidence
    )

    return {
        "id": exam.id,
        "title": exam.title,
        "subject": subject.name if subject else None,
        "duration_minutes": exam.duration_minutes,
        "status": exam.status,
        "start_time": _as_utc_iso(exam.start_time),
        "end_time": _as_utc_iso(exam.end_time),
        "submission_status": submission.status if submission else None,
        "has_submitted": has_real_submission,
        "retake_request_status": latest_retake_request.status if latest_retake_request else None,
        "retake_request_created_at": latest_retake_request.created_at.isoformat() if latest_retake_request else None,
    }


def _serialize_exam_detail(db: Session, exam: Exam) -> dict:
    """
    序列化 exam detail 对象为字典。
    """
    subject = db.get(Subject, exam.subject_id)
    question_count = db.scalar(select(func.count()).select_from(ExamQuestion).where(ExamQuestion.exam_id == exam.id)) or 0
    return {
        "id": exam.id,
        "title": exam.title,
        "subject": subject.name if subject else None,
        "duration_minutes": exam.duration_minutes,
        "total_score": float(exam.total_score),
        "status": exam.status,
        "start_time": _as_utc_iso(exam.start_time),
        "end_time": _as_utc_iso(exam.end_time),
        "instructions": exam.instructions,
        "question_count": question_count,
    }


def _serialize_submission(submission: ExamSubmission | None) -> dict | None:
    """
    序列化 submission 对象为字典。
    """
    if submission is None:
        return None
    return {"id": submission.id, "exam_id": submission.exam_id, "student_id": submission.student_id, "status": submission.status, "started_at": submission.started_at.isoformat() if submission.started_at else None, "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None, "deadline_at": submission.deadline_at.isoformat() if submission.deadline_at else None, "objective_score": float(submission.objective_score), "subjective_score": float(submission.subjective_score), "total_score": float(submission.total_score), "correct_rate": submission.correct_rate, "ranking_in_class": submission.ranking_in_class}

@router.get("/student/knowledge-map")
def get_student_knowledge_map(subject: str | None = None, current_user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    """
    获取学生真实知识点图谱(基于错题统计)
    """
    answers = db.scalars(
        select(SubmissionAnswer)
        .join(ExamSubmission)
        .where(ExamSubmission.student_id == current_user.id)
    ).all()
    
    stats = {}
    for ans in answers:
        q = db.get(Question, ans.question_id)
        if not q or not q.type:
            continue
        node_name = q.type
        if node_name not in stats:
            stats[node_name] = {"total": 0, "correct": 0}
        stats[node_name]["total"] += 1
        if ans.is_correct:
            stats[node_name]["correct"] += 1
            
    nodes = []
    for i, (name, s) in enumerate(stats.items()):
        mastery = s["correct"] / s["total"] if s["total"] > 0 else 0
        status = "good" if mastery > 0.8 else ("average" if mastery > 0.6 else "weak")
        nodes.append({"id": f"k{i}", "name": f"{name}题型", "mastery": round(mastery, 2), "status": status})
        
    summary = "当前尚未积累足够的答题数据"
    if nodes:
        weakest = min(nodes, key=lambda x: x["mastery"])
        if weakest["mastery"] < 0.6:
            summary = f"{weakest['name']}掌握较弱，建议优先复习。"
        else:
            summary = "整体掌握情况良好！"
            
    return success_response({"nodes": nodes, "edges": [], "summary": summary})

@router.get("/student/study-tasks")
def list_study_tasks(current_user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    """
    获取学生学习任务列表
    """
    _cleanup_invalid_study_artifacts_for_student(db, current_user.id)

    valid_plan_subquery = (
        select(StudyPlan.id)
        .where(StudyPlan.student_id == current_user.id)
        .where(
            (StudyPlan.source_exam_id == None)
            | (
                select(func.count())
                .select_from(ExamQuestion)
                .join(Question, Question.id == ExamQuestion.question_id)
                .where(ExamQuestion.exam_id == StudyPlan.source_exam_id)
                .scalar_subquery()
                > 0
            )
        )
    )
    tasks = db.scalars(
        select(StudyTask)
        .where(
            StudyTask.student_id == current_user.id,
            StudyTask.plan_id.in_(valid_plan_subquery),
            StudyTask.status.in_(["pending", "in_progress"]),
            StudyTask.completed_at == None,
        )
        .order_by(StudyTask.priority.asc(), StudyTask.created_at.desc())
    ).all()
    ignored_tasks = db.scalars(
        select(StudyTask)
        .where(
            StudyTask.student_id == current_user.id,
            StudyTask.plan_id.in_(valid_plan_subquery),
            StudyTask.status == "ignored",
        )
        .order_by(StudyTask.completed_at.desc(), StudyTask.created_at.desc())
        .limit(50)
    ).all()
    completed_tasks = db.scalars(
        select(StudyTask)
        .where(
            StudyTask.student_id == current_user.id,
            StudyTask.plan_id.in_(valid_plan_subquery),
            StudyTask.status == "completed",
        )
        .order_by(StudyTask.completed_at.desc(), StudyTask.created_at.desc())
        .limit(100)
    ).all()
    serialized = []
    type_counter: dict[str, int] = {}
    pending_count = 0
    in_progress_count = 0
    completed_count = 0
    total_minutes = 0

    for t in tasks:
        task_type = t.task_type or ""
        task_type_label = _study_task_type_label(task_type)
        content = t.feedback or (f"任务类型：{task_type_label}" if task_type else "按优先顺序完成相关知识点复习")
        type_counter[task_type_label] = type_counter.get(task_type_label, 0) + 1
        if t.status == "completed":
            completed_count += 1
        elif t.status == "in_progress":
            in_progress_count += 1
            total_minutes += int(t.estimated_minutes or 0)
        else:
            pending_count += 1
            total_minutes += int(t.estimated_minutes or 0)
        serialized.append(
            {
                "id": t.id,
                "title": t.title,
                "content": content,
                "status": t.status,
                "priority": t.priority,
                "task_type": task_type,
                "task_type_label": task_type_label,
                "estimated_minutes": t.estimated_minutes,
                "created_at": t.created_at.isoformat(),
            }
        )

    ignored_serialized = []
    for t in ignored_tasks:
        task_type = t.task_type or ""
        task_type_label = _study_task_type_label(task_type)
        ignored_serialized.append(
            {
                "id": t.id,
                "title": t.title,
                "content": t.feedback or (f"任务类型：{task_type_label}" if task_type else "已忽略任务"),
                "status": t.status,
                "priority": t.priority,
                "task_type": task_type,
                "task_type_label": task_type_label,
                "estimated_minutes": t.estimated_minutes,
                "created_at": t.created_at.isoformat(),
                "ignored_at": t.completed_at.isoformat() if t.completed_at else None,
            }
        )

    completed_serialized = []
    for t in completed_tasks:
        task_type = t.task_type or ""
        task_type_label = _study_task_type_label(task_type)
        completed_serialized.append(
            {
                "id": t.id,
                "title": t.title,
                "content": t.feedback or (f"任务类型：{task_type_label}" if task_type else "已完成复习任务"),
                "status": t.status,
                "priority": t.priority,
                "task_type": task_type,
                "task_type_label": task_type_label,
                "estimated_minutes": t.estimated_minutes,
                "created_at": t.created_at.isoformat(),
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "feedback": t.feedback,
            }
        )

    focus_types = [item[0] for item in sorted(type_counter.items(), key=lambda item: item[1], reverse=True)[:3]]
    active_count = pending_count + in_progress_count
    readiness_score = max(45, min(95, 100 - active_count * 6 + completed_count * 4))
    suggested_session_minutes = 25 if active_count >= 4 else 20 if active_count >= 2 else 15
    estimated_completion_days = max(1, (total_minutes + 39) // 40) if active_count else 0

    ai_overview = {
        "readiness_score": readiness_score,
        "active_task_count": active_count,
        "completed_count": completed_count,
        "total_minutes": total_minutes,
        "suggested_session_minutes": suggested_session_minutes,
        "estimated_completion_days": estimated_completion_days,
        "focus_types": focus_types,
        "summary": (
            "当前任务节奏良好，建议保持每日固定复习窗口。"
            if active_count <= 2
            else "当前任务较密集，建议优先处理高优先级并按番茄时段推进。"
        ),
    }

    ai_actions = [
        f"今天先完成优先级最高的 {min(2, active_count)} 个任务。",
        f"每轮学习建议 {suggested_session_minutes} 分钟，轮间休息 5 分钟。",
    ]
    if focus_types:
        ai_actions.append(f"优先关注：{'、'.join(focus_types)}。")

    ai_overview["ignored_count"] = len(ignored_serialized)
    ai_overview["completed_count"] = len(completed_serialized)
    return success_response(
        {
            "tasks": serialized,
            "ignored_tasks": ignored_serialized,
            "completed_tasks": completed_serialized,
            "ai_overview": ai_overview,
            "ai_actions": ai_actions,
        }
    )


@router.post("/student/study-tasks/action")
def mutate_study_task(
    payload: StudyTaskActionRequest,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """
    学习任务交互动作：开始、暂停、完成、忽略、取消忽略、删除。
    """
    task = db.scalar(select(StudyTask).where(StudyTask.id == payload.task_id, StudyTask.student_id == current_user.id))
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    action = (payload.action or "").strip().lower()
    if action == "start":
        task.status = "in_progress"
        task.completed_at = None
    elif action == "pause":
        task.status = "pending"
        task.completed_at = None
    elif action == "complete":
        task.status = "completed"
        task.completed_at = datetime.now(UTC)
    elif action == "ignore":
        task.status = "ignored"
        task.completed_at = datetime.now(UTC)
    elif action == "unignore":
        task.status = "pending"
        task.completed_at = None
    elif action == "delete":
        removed_task_id = task.id
        db.delete(task)
        db.commit()
        return success_response({"task": {"id": removed_task_id, "status": "deleted", "completed_at": None, "feedback": None}})
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action")

    if payload.feedback:
        task.feedback = payload.feedback.strip()[:1000]

    db.add(task)
    db.commit()
    db.refresh(task)
    return success_response(
        {
            "task": {
                "id": task.id,
                "status": task.status,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "feedback": task.feedback,
            }
        }
    )


@router.get("/student/study-tasks/coaching")
def get_study_task_coaching(
    task_id: int,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """
    为学习任务返回可直接执行的复习包：步骤建议 + 针对题练习。
    """
    task = db.scalar(select(StudyTask).where(StudyTask.id == task_id, StudyTask.student_id == current_user.id))
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    target_question_count = _extract_target_question_count_from_title(task.title, default_count=6)

    plan = db.get(StudyPlan, task.plan_id)
    source_exam_id = int(plan.source_exam_id or 0) if plan else 0

    wrong_query = (
        select(SubmissionAnswer, Question, ExamSubmission)
        .join(ExamSubmission, SubmissionAnswer.submission_id == ExamSubmission.id)
        .join(Question, SubmissionAnswer.question_id == Question.id)
        .where(ExamSubmission.student_id == current_user.id)
        .where(SubmissionAnswer.is_correct == False)
        .order_by(SubmissionAnswer.updated_at.desc())
        .limit(max(80, target_question_count * 8))
    )
    if task.task_type == "wrong_question_review" and source_exam_id > 0:
        wrong_query = wrong_query.where(ExamSubmission.exam_id == source_exam_id)
    if task.knowledge_point_id:
        wrong_query = wrong_query.join(
            QuestionKnowledgePoint,
            (QuestionKnowledgePoint.question_id == Question.id)
            & (QuestionKnowledgePoint.knowledge_point_id == task.knowledge_point_id),
        )

    rows = db.execute(wrong_query).all()

    def classify_practice_status(answer_obj: SubmissionAnswer, student_answer: Any) -> str:
        if student_answer is None:
            return "unanswered"
        if isinstance(student_answer, str) and not student_answer.strip():
            return "unanswered"
        if isinstance(student_answer, list) and len(student_answer) == 0:
            return "unanswered"
        if answer_obj.is_correct is False:
            return "wrong"
        return "review"

    practice_items = []
    seen_question_ids: set[int] = set()
    for answer, question, submission in rows:
        if question.id in seen_question_ids:
            continue
        seen_question_ids.add(question.id)
        student_answer = parse_answer(answer.answer_content) if answer.answer_content else answer.answer_text
        practice_status = classify_practice_status(answer, student_answer)
        practice_items.append(
            {
                "question_id": question.id,
                "exam_id": submission.exam_id,
                "question_type": question.type,
                "stem": question.stem,
                "analysis": question.analysis,
                "standard_answer": parse_answer(question.answer_text),
                "last_student_answer": student_answer,
                "practice_status": practice_status,
            }
        )
        if len(practice_items) >= target_question_count:
            break

    if not practice_items:
        fallback_query = (
            select(SubmissionAnswer, Question, ExamSubmission)
            .join(ExamSubmission, SubmissionAnswer.submission_id == ExamSubmission.id)
            .join(Question, SubmissionAnswer.question_id == Question.id)
            .where(ExamSubmission.student_id == current_user.id)
            .order_by(SubmissionAnswer.updated_at.desc())
            .limit(max(20, target_question_count * 4))
        )
        if task.task_type == "wrong_question_review" and source_exam_id > 0:
            fallback_query = fallback_query.where(ExamSubmission.exam_id == source_exam_id)
        fallback_rows = db.execute(fallback_query).all()
        fallback_seen_question_ids: set[int] = set()
        for answer, question, submission in fallback_rows:
            if question.id in fallback_seen_question_ids:
                continue
            fallback_seen_question_ids.add(question.id)
            student_answer = parse_answer(answer.answer_content) if answer.answer_content else answer.answer_text
            practice_status = classify_practice_status(answer, student_answer)
            practice_items.append(
                {
                    "question_id": question.id,
                    "exam_id": submission.exam_id,
                    "question_type": question.type,
                    "stem": question.stem,
                    "analysis": question.analysis,
                    "standard_answer": parse_answer(question.answer_text),
                    "last_student_answer": student_answer,
                    "practice_status": practice_status,
                }
            )
            if len(practice_items) >= target_question_count:
                break

    estimated_minutes = int(task.estimated_minutes or 20)
    drill_steps = [
        "阅读任务目标并回顾最近同类错误。",
        f"计时 {estimated_minutes} 分钟完成针对题练习。",
        "每道题先独立作答，再核对答案与解析。",
        "记录1条错因与1条改进动作，提交复盘。",
    ]

    coach_summary = (
        f"本次任务聚焦{_study_task_type_label(task.task_type)}，"
        f"已为你挑选 {len(practice_items)} 道真实历史错题/近似题进行复练。"
    )

    return success_response(
        {
            "task": {
                "id": task.id,
                "title": task.title,
                "task_type": task.task_type,
                "task_type_label": _study_task_type_label(task.task_type),
                "target_question_count": target_question_count,
                "estimated_minutes": estimated_minutes,
                "status": task.status,
            },
            "coach_summary": coach_summary,
            "drill_steps": drill_steps,
            "practice_items": practice_items,
        }
    )


def _cleanup_invalid_study_artifacts_for_student(db: Session, student_id: int) -> None:
    """
    清理学生侧已失效的学习计划与任务：来源考试无有效题目时删除对应待办。
    """
    duplicate_plans = db.scalars(
        select(StudyPlan)
        .where(StudyPlan.student_id == student_id, StudyPlan.source_exam_id != None)
        .order_by(StudyPlan.source_exam_id.asc(), StudyPlan.created_at.desc(), StudyPlan.id.desc())
    ).all()
    seen_exam_ids: set[int] = set()
    duplicate_plan_ids: list[int] = []
    for plan in duplicate_plans:
        exam_id = int(plan.source_exam_id or 0)
        if exam_id <= 0:
            continue
        if exam_id in seen_exam_ids:
            duplicate_plan_ids.append(plan.id)
            continue
        seen_exam_ids.add(exam_id)

    if duplicate_plan_ids:
        db.query(StudyTask).filter(StudyTask.plan_id.in_(duplicate_plan_ids)).delete(synchronize_session=False)
        db.query(StudyPlan).filter(StudyPlan.id.in_(duplicate_plan_ids)).delete(synchronize_session=False)
        db.flush()

    student_tasks = db.scalars(
        select(StudyTask)
        .where(StudyTask.student_id == student_id)
        .order_by(StudyTask.plan_id.asc(), StudyTask.created_at.desc(), StudyTask.id.desc())
    ).all()
    seen_task_keys: set[tuple[int, str, int]] = set()
    duplicate_task_ids: list[int] = []
    wrong_review_counts: dict[int, int] = {}
    wrong_review_keepers: dict[int, StudyTask] = {}
    for task in student_tasks:
        key = (task.plan_id, task.task_type or "", int(task.knowledge_point_id or 0))
        if key in seen_task_keys:
            duplicate_task_ids.append(task.id)
            if task.task_type == "wrong_question_review":
                wrong_review_counts[task.plan_id] = wrong_review_counts.get(task.plan_id, 1) + 1
            continue
        seen_task_keys.add(key)
        if task.task_type == "wrong_question_review":
            wrong_review_keepers[task.plan_id] = task
            wrong_review_counts.setdefault(task.plan_id, 1)

    if duplicate_task_ids:
        db.query(StudyTask).filter(StudyTask.id.in_(duplicate_task_ids)).delete(synchronize_session=False)
        for plan_id, task in wrong_review_keepers.items():
            duplicate_count = wrong_review_counts.get(plan_id, 1)
            if duplicate_count <= 1:
                continue
            task.title = f"集中回顾错题（{duplicate_count}题）"
            task.feedback = f"该计划中原有 {duplicate_count} 条重复错题回顾任务，已合并为一次集中复盘。"
            db.add(task)
        db.flush()

    invalid_plan_ids = db.scalars(
        select(StudyPlan.id)
        .where(StudyPlan.student_id == student_id, StudyPlan.source_exam_id != None)
        .where(
            (
                select(func.count())
                .select_from(ExamQuestion)
                .join(Question, Question.id == ExamQuestion.question_id)
                .where(ExamQuestion.exam_id == StudyPlan.source_exam_id)
                .scalar_subquery()
            )
            <= 0
        )
    ).all()
    if not invalid_plan_ids:
        return
    db.query(StudyTask).filter(StudyTask.plan_id.in_(invalid_plan_ids)).delete(synchronize_session=False)
    db.query(StudyPlan).filter(StudyPlan.id.in_(invalid_plan_ids)).delete(synchronize_session=False)
    db.commit()

@router.get("/student/growth-trend")
def get_growth_trend(subject: str | None = None, current_user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    """
    获取学生真实成长趋势
    """
    # 获取学生有成绩的考试
    submissions = db.scalars(
        select(ExamSubmission)
        .where(ExamSubmission.student_id == current_user.id, ExamSubmission.status.in_(["submitted", "completed"]))
        .order_by(ExamSubmission.submitted_at.asc())
        .limit(10)
    ).all()
    
    exams_data = []
    for sub in submissions:
        exam = db.get(Exam, sub.exam_id)
        if not exam:
            continue
        # 获取改考试的班级所有提交，计算平均分
        all_subs = db.scalars(select(ExamSubmission).where(ExamSubmission.exam_id == exam.id, ExamSubmission.status.in_(["submitted", "completed"]))).all()
        class_avg = sum(float(s.total_score) for s in all_subs) / len(all_subs) if all_subs else 0
        
        exams_data.append({
            "date": sub.submitted_at.strftime("%Y-%m-%d") if sub.submitted_at else "未知日期",
            "score": float(sub.total_score),
            "class_avg": round(class_avg, 1)
        })
    
    insights = []
    if len(exams_data) >= 2:
        diff = exams_data[-1]["score"] - exams_data[-2]["score"]
        if diff > 0:
            insights.append(f"最近一次考试成绩提升了{diff}分，继续保持！")
        elif diff < 0:
            insights.append(f"最近一次考试分数有所波退，请注意错题回顾。")
            
    return success_response({
        "exams": exams_data,
        "insights": insights
    })


@router.get("/student/growth/ability-profile")
def get_growth_ability_profile(
    subject: str | None = None,
    force_refresh: bool = False,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """
    基于学生真实作答题目生成能力画像、AI建议与书籍推荐。
    """
    profile_key = f"{current_user.id}:{(subject or '').strip() or '*'}"

    stat_query = (
        select(func.count(SubmissionAnswer.id), func.max(SubmissionAnswer.updated_at))
        .select_from(SubmissionAnswer)
        .join(ExamSubmission, SubmissionAnswer.submission_id == ExamSubmission.id)
        .join(Question, SubmissionAnswer.question_id == Question.id)
        .outerjoin(Subject, Question.subject_id == Subject.id)
        .where(ExamSubmission.student_id == current_user.id)
        .where(ExamSubmission.status.in_(["submitted", "completed", "reviewed"]))
    )
    if subject:
        stat_query = stat_query.where(Subject.name == subject)

    answer_count, latest_answer_at = db.execute(stat_query).first() or (0, None)
    fingerprint = f"{int(answer_count or 0)}:{latest_answer_at.isoformat() if latest_answer_at else 'none'}"

    now = datetime.now(UTC)
    cached = _growth_profile_cache.get(profile_key)
    if cached and not force_refresh:
        cache_time = cached.get("cached_at")
        if isinstance(cache_time, datetime) and now - cache_time <= GROWTH_PROFILE_CACHE_TTL and cached.get("fingerprint") == fingerprint:
            payload = dict(cached.get("payload") or {})
            payload["cache"] = {
                "hit": True,
                "fingerprint": fingerprint,
                "cached_at": cache_time.isoformat(),
                "ttl_seconds": int(GROWTH_PROFILE_CACHE_TTL.total_seconds()),
            }
            return success_response(payload)

    query = (
        select(SubmissionAnswer, Question, Subject)
        .join(ExamSubmission, SubmissionAnswer.submission_id == ExamSubmission.id)
        .join(Question, SubmissionAnswer.question_id == Question.id)
        .outerjoin(Subject, Question.subject_id == Subject.id)
        .where(ExamSubmission.student_id == current_user.id)
        .where(ExamSubmission.status.in_(["submitted", "completed", "reviewed"]))
        .order_by(SubmissionAnswer.created_at.desc())
        .limit(400)
    )
    if subject:
        query = query.where(Subject.name == subject)

    rows = db.execute(query).all()
    answer_records = [
        {
            "subject": subject_row.name if subject_row else None,
            "question_type": question.type,
            "stem": question.stem,
            "analysis": question.analysis,
            "is_correct": answer.is_correct,
        }
        for answer, question, subject_row in rows
    ]

    payload = build_growth_ability_profile(answer_records)
    _growth_profile_cache[profile_key] = {
        "fingerprint": fingerprint,
        "cached_at": now,
        "payload": payload,
    }
    payload["cache"] = {
        "hit": False,
        "fingerprint": fingerprint,
        "cached_at": now.isoformat(),
        "ttl_seconds": int(GROWTH_PROFILE_CACHE_TTL.total_seconds()),
    }
    return success_response(payload)


@router.get("/student/classes")
def list_student_classes(current_user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    """
    获取学生加入的班级相关数据。
    """
    relations = db.scalars(
        select(ClassStudent)
        .where(ClassStudent.student_id == current_user.id, ClassStudent.status == "active")
    ).all()
    
    classes_data = []
    for rel in relations:
        classroom = db.get(ClassRoom, rel.class_id)
        if classroom:
            teacher = db.get(User, classroom.teacher_id)
            classes_data.append({
                "class_id": classroom.id,
                "name": classroom.name,
                "grade_name": classroom.grade_name,
                "subject": classroom.subject,
                "teacher_name": teacher.name if teacher else "未知的教师",
                "joined_at": rel.joined_at.isoformat()
            })
            
    return success_response({"classes": classes_data})

import json
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.core.response import success_response
from app.models.academic import ClassRoom, ClassStudent, Subject
from app.models.exam import Exam, ExamClass, ExamQuestion, ExamSubmission, SubmissionAnswer, SubmissionBehaviorEvent
from app.models.question import Question, QuestionOption
from app.models.user import ReviewItem, StudyTask, User
from app.schemas.student import BatchSaveAnswerRequest, BehaviorReportRequest, SaveAnswerRequest, StartExamRequest, SubmitExamRequest
from app.services.learning import build_submission_analysis, generate_study_plan
from app.services.realtime import realtime_events, submission_channel
from app.services.scoring import OBJECTIVE_TYPES, SUBJECTIVE_TYPES, compute_objective_score, parse_answer, serialize_answer
from app.services.tasks import complete_ai_task, mark_ai_task_running, queue_ai_task


router = APIRouter()


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
    query = select(Exam).join(ExamClass, ExamClass.exam_id == Exam.id).where(ExamClass.class_id.in_(class_ids))
    now = datetime.now(UTC)
    if status == "upcoming":
        query = query.where(Exam.start_time > now)
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
    return success_response({"items": [_serialize_exam_list_item(db, item) for item in items], "total": total})


@router.get("/student/exams/detail")
def get_student_exam_detail(exam_id: int, current_user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    """
    获取 student exam detail 相关数据。
    """
    exam = _get_student_exam(db, current_user.id, exam_id)
    now = datetime.now(UTC)
    return success_response({"exam": _serialize_exam_detail(db, exam), "can_start": exam.start_time <= now <= exam.end_time and exam.status in {"published", "ongoing"}, "rules": {"allow_review": exam.allow_review, "random_question_order": exam.random_question_order}})


@router.post("/student/exams/start")
def start_exam(payload: StartExamRequest, current_user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    """
    学生开始考试接口
    
    验证当前学生是否具备参加该考试的权限，若首次开始则在数据库中初始化一条 ExamSubmission 记录。
    生成初始的草稿数据并将状态设定为 in_progress。最终返回一个有效的 submission_id 供答题阶段使用。
    """
    exam = _get_student_exam(db, current_user.id, payload.exam_id)
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
    remaining_seconds = max(0, int((exam.end_time - datetime.now(UTC)).total_seconds()))
    return success_response({"exam": _serialize_exam_detail(db, exam), "questions": questions, "remaining_seconds": remaining_seconds})


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
    upcoming_count = db.scalar(
        select(func.count()).select_from(Exam).join(ExamClass, ExamClass.exam_id == Exam.id).join(ClassStudent, ClassStudent.class_id == ExamClass.class_id).where(ClassStudent.student_id == current_user.id, Exam.start_time > datetime.now(UTC))
    ) or 0
    recent_exams = db.scalars(
        select(Exam).join(ExamSubmission, ExamSubmission.exam_id == Exam.id).where(ExamSubmission.student_id == current_user.id).order_by(ExamSubmission.created_at.desc()).limit(5)
    ).all()
    latest_submission = db.scalar(select(ExamSubmission).where(ExamSubmission.student_id == current_user.id).order_by(ExamSubmission.created_at.desc()))
    recommended_tasks = db.scalars(
        select(StudyTask).where(StudyTask.student_id == current_user.id, StudyTask.status == "pending").order_by(StudyTask.priority.asc(), StudyTask.created_at.desc()).limit(5)
    ).all()
    return success_response(
        {
            "upcoming_exam_count": upcoming_count,
            "recent_exams": [{"id": item.id, "title": item.title} for item in recent_exams],
            "latest_result_summary": _serialize_submission(latest_submission) if latest_submission else None,
            "ai_reminders": ["建议优先复习最近一次考试中的高频错题。"],
            "ability_profile_summary": {"审题能力": 0.7, "计算能力": 0.68, "综合应用能力": 0.6},
            "recommended_tasks": [{"task_id": item.id, "title": item.title, "priority": item.priority} for item in recommended_tasks],
        }
    )


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


def _get_student_exam(db: Session, student_id: int, exam_id: int) -> Exam:
    """
    处理  get student exam 请求并返回结果。
    """
    class_ids = db.scalars(select(ClassStudent.class_id).where(ClassStudent.student_id == student_id, ClassStudent.status == "active")).all()
    exam = db.scalar(select(Exam).join(ExamClass, ExamClass.exam_id == Exam.id).where(Exam.id == exam_id, ExamClass.class_id.in_(class_ids)))
    if not exam:
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


def _serialize_exam_list_item(db: Session, exam: Exam) -> dict:
    """
    序列化 exam list item 对象为字典。
    """
    subject = db.get(Subject, exam.subject_id)
    return {"id": exam.id, "title": exam.title, "subject": subject.name if subject else None, "duration_minutes": exam.duration_minutes, "status": exam.status, "start_time": exam.start_time.isoformat(), "end_time": exam.end_time.isoformat()}


def _serialize_exam_detail(db: Session, exam: Exam) -> dict:
    """
    序列化 exam detail 对象为字典。
    """
    subject = db.get(Subject, exam.subject_id)
    question_count = db.scalar(select(func.count()).select_from(ExamQuestion).where(ExamQuestion.exam_id == exam.id)) or 0
    return {"id": exam.id, "title": exam.title, "subject": subject.name if subject else None, "duration_minutes": exam.duration_minutes, "total_score": float(exam.total_score), "status": exam.status, "start_time": exam.start_time.isoformat(), "end_time": exam.end_time.isoformat(), "instructions": exam.instructions, "question_count": question_count}


def _serialize_submission(submission: ExamSubmission | None) -> dict | None:
    """
    序列化 submission 对象为字典。
    """
    if submission is None:
        return None
    return {"id": submission.id, "exam_id": submission.exam_id, "student_id": submission.student_id, "status": submission.status, "started_at": submission.started_at.isoformat() if submission.started_at else None, "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None, "deadline_at": submission.deadline_at.isoformat() if submission.deadline_at else None, "objective_score": float(submission.objective_score), "subjective_score": float(submission.subjective_score), "total_score": float(submission.total_score), "correct_rate": submission.correct_rate, "ranking_in_class": submission.ranking_in_class}

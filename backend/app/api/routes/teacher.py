import json
from datetime import datetime, UTC
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.core.response import success_response
from app.models.academic import ClassRoom, ClassStudent, KnowledgePoint, Subject
from app.models.exam import Exam, ExamClass, ExamQuestion, ExamSubmission, SubmissionAnswer
from app.models.question import Question, QuestionKnowledgePoint, QuestionOption
from app.models.user import ReviewItem, ReviewLog, User
from app.schemas.teacher import AIQuestionGenerateRequest, AIQuestionReviewRequest, AIScoreRequest, ClassCreateRequest, DeleteRequest, ExamActionRequest, ExamCreateRequest, ExamUpdateRequest, ImportQuestionsRequest, QuestionCreateRequest, QuestionUpdateRequest, ReviewSubmitRequest
from app.services.realtime import realtime_events, submission_channel
from app.services.scoring import SUBJECTIVE_TYPES, serialize_answer
from app.services.tasks import complete_ai_task, create_ai_task, mark_ai_task_running, queue_ai_task


router = APIRouter()


@router.get("/teacher/classes")
def list_classes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
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
            "grade_name": item.grade_name,
            "risk_level": risk_level or "unknown",
        })
    return success_response({"items": serialized, "total": total})


@router.get("/teacher/students/detail")
def get_student_detail(student_id: int, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    student = db.get(User, student_id)
    if not student or student.role != "student":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    relation = db.scalar(select(ClassStudent).where(ClassStudent.student_id == student_id, ClassStudent.teacher_id == current_user.id, ClassStudent.status == "active"))
    if not relation:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission for this student")
    classroom = db.get(ClassRoom, relation.class_id)
    latest_submission = db.scalar(select(ExamSubmission).where(ExamSubmission.student_id == student_id).order_by(ExamSubmission.created_at.desc()))
    return success_response(
        {
            "student": {"id": student.id, "name": student.name, "email": student.email, "grade_name": student.grade_name},
            "class": _serialize_class(classroom) if classroom else None,
            "latest_summary": {
                "latest_exam_id": latest_submission.exam_id if latest_submission else None,
                "latest_total_score": float(latest_submission.total_score) if latest_submission else None,
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


@router.post("/teacher/questions/create")
def create_question(payload: QuestionCreateRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
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
    if payload.question_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="question_id is required")
    question = db.get(Question, payload.question_id)
    if not question or question.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    db.query(QuestionOption).filter(QuestionOption.question_id == question.id).delete()
    db.query(QuestionKnowledgePoint).filter(QuestionKnowledgePoint.question_id == question.id).delete()
    db.delete(question)
    db.commit()
    return success_response({"success": True}, "question deleted")


@router.post("/teacher/questions/import")
def import_questions(payload: ImportQuestionsRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
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
    task = queue_ai_task(
        db,
        task_type="ai_generate_question",
        resource_type="question",
        resource_id=None,
        created_by=current_user.id,
        request_payload=payload.model_dump(),
    )
    mark_ai_task_running(db, task, progress=35)
    complete_ai_task(
        db,
        task,
        result_payload={
            "questions": [
                {
                    "subject": payload.subject,
                    "type": payload.question_type,
                    "stem": f"AI 生成示例题：{payload.knowledge_points[0] if payload.knowledge_points else '综合题'}",
                    "analysis": "当前为第一阶段占位结果，后续接入大模型。",
                }
            ]
        },
    )
    return success_response({"questions": task.result_payload["questions"], "task_id": task.task_id})


@router.post("/teacher/questions/ai-review")
def ai_review_question(payload: AIQuestionReviewRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
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
    subject_obj = _get_subject_by_name(db, payload.subject)
    exam = Exam(
        created_by=current_user.id,
        subject_id=subject_obj.id,
        title=payload.title,
        duration_minutes=payload.duration_minutes,
        total_score=sum(item.score for item in payload.question_items),
        status="draft",
        instructions=payload.instructions,
        allow_review=payload.allow_review,
        random_question_order=payload.random_question_order,
        start_time=payload.start_time,
        end_time=payload.end_time,
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
    exam = _get_teacher_exam(db, current_user.id, exam_id)
    question_items = db.scalars(select(ExamQuestion).where(ExamQuestion.exam_id == exam.id).order_by(ExamQuestion.order_no.asc())).all()
    classes = db.scalars(select(ClassRoom).join(ExamClass, ExamClass.class_id == ClassRoom.id).where(ExamClass.exam_id == exam.id)).all()
    return success_response({"exam": _serialize_exam(db, exam), "question_items": [_serialize_exam_question(db, item) for item in question_items], "classes": [_serialize_class(item) for item in classes]})


@router.post("/teacher/exams/update")
def update_exam(payload: ExamUpdateRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    exam = _get_teacher_exam(db, current_user.id, payload.exam_id)
    data = payload.model_dump(exclude_none=True)
    class_ids = data.pop("class_ids", None)
    question_items = data.pop("question_items", None)
    data.pop("exam_id", None)
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
    exam = _get_teacher_exam(db, current_user.id, payload.exam_id)
    exam.status = "published"
    exam.published_at = datetime.now(UTC)
    db.add(exam)
    db.commit()
    return success_response({"exam_id": exam.id, "status": exam.status}, "exam published")


@router.post("/teacher/exams/pause")
def pause_exam(payload: ExamActionRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    exam = _get_teacher_exam(db, current_user.id, payload.exam_id)
    exam.status = "draft"
    db.add(exam)
    db.commit()
    return success_response({"exam_id": exam.id, "status": exam.status}, "exam paused")


@router.post("/teacher/exams/finish")
def finish_exam(payload: ExamActionRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    exam = _get_teacher_exam(db, current_user.id, payload.exam_id)
    exam.status = "finished"
    exam.finished_at = datetime.now(UTC)
    db.add(exam)
    db.commit()
    return success_response({"exam_id": exam.id, "status": exam.status}, "exam finished")


@router.post("/teacher/exams/delete")
def delete_exam(payload: DeleteRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
    if payload.exam_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="exam_id is required")
    exam = _get_teacher_exam(db, current_user.id, payload.exam_id)
    db.query(ExamQuestion).filter(ExamQuestion.exam_id == exam.id).delete()
    db.query(ExamClass).filter(ExamClass.exam_id == exam.id).delete()
    db.delete(exam)
    db.commit()
    return success_response({"success": True}, "exam deleted")


@router.post("/teacher/exams/ai-evaluate")
def ai_evaluate_exam(payload: ExamActionRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
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
    _get_teacher_exam(db, current_user.id, exam_id)
    submission = db.get(ExamSubmission, submission_id)
    if not submission or submission.exam_id != exam_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    answers = db.scalars(select(SubmissionAnswer).where(SubmissionAnswer.submission_id == submission_id)).all()
    return success_response({"submission_id": submission_id, "objective_score": float(submission.objective_score), "question_scores": [{"question_id": item.question_id, "score": float(item.score)} for item in answers]})


@router.post("/teacher/review/ai-score")
def ai_score(payload: AIScoreRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
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
    _get_teacher_exam(db, current_user.id, exam_id)
    query = select(ReviewItem).where(ReviewItem.exam_id == exam_id)
    if review_status:
        query = query.where(ReviewItem.review_status == review_status)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return success_response({"items": [_serialize_review_item(item) for item in items], "total": total})


@router.post("/teacher/review/submit")
def submit_review(payload: ReviewSubmitRequest, current_user: User = Depends(require_role("teacher")), db: Session = Depends(get_db)):
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
    subject = db.get(Subject, exam.subject_id)
    class_ids = db.scalars(select(ExamClass.class_id).where(ExamClass.exam_id == exam.id)).all()
    question_count = db.scalar(select(func.count()).select_from(ExamQuestion).where(ExamQuestion.exam_id == exam.id)) or 0
    return {
        "id": exam.id,
        "title": exam.title,
        "subject": subject.name if subject else None,
        "duration_minutes": exam.duration_minutes,
        "total_score": float(exam.total_score),
        "status": exam.status,
        "start_time": exam.start_time.isoformat(),
        "end_time": exam.end_time.isoformat(),
        "instructions": exam.instructions,
        "allow_review": exam.allow_review,
        "random_question_order": exam.random_question_order,
        "question_count": question_count,
        "class_ids": class_ids,
        "created_by": exam.created_by,
        "created_at": exam.created_at.isoformat(),
    }


def _serialize_exam_question(db: Session, item: ExamQuestion) -> dict:
    question = db.get(Question, item.question_id)
    return {
        "question_id": item.question_id,
        "score": float(item.score),
        "order_no": item.order_no,
        "section_name": item.section_name,
        "question": _serialize_question(db, question) if question else None,
    }


def _serialize_review_item(item: ReviewItem) -> dict:
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


def _get_subject_by_name(db: Session, subject_name: str) -> Subject:
    subject_obj = db.scalar(select(Subject).where(Subject.name == subject_name))
    if not subject_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    return subject_obj


def _get_teacher_class(db: Session, teacher_id: int, class_id: int) -> ClassRoom:
    classroom = db.scalar(select(ClassRoom).where(ClassRoom.id == class_id, ClassRoom.teacher_id == teacher_id))
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    return classroom


def _get_teacher_exam(db: Session, teacher_id: int, exam_id: int) -> Exam:
    exam = db.scalar(select(Exam).where(Exam.id == exam_id, Exam.created_by == teacher_id))
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    return exam


def _replace_question_relations(db: Session, question_id: int, options, knowledge_point_ids) -> None:
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
    if class_ids is not None:
        db.query(ExamClass).filter(ExamClass.exam_id == exam_id).delete()
        for class_id in class_ids:
            db.add(ExamClass(exam_id=exam_id, class_id=class_id))
    if question_items is not None:
        db.query(ExamQuestion).filter(ExamQuestion.exam_id == exam_id).delete()
        for item in question_items:
            db.add(ExamQuestion(exam_id=exam_id, question_id=item.question_id, score=item.score, order_no=item.order_no, section_name=item.section_name))
    db.commit()

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import KnowledgePoint, Subject
from app.models.exam import Exam, ExamSubmission, SubmissionAnswer
from app.models.question import QuestionKnowledgePoint
from app.models.user import StudentProfileSnapshot, StudyPlan, StudyTask


def build_submission_analysis(db: Session, submission: ExamSubmission, exam: Exam) -> dict:
    """
    处理 build submission analysis 请求并返回结果。
    """
    answers = db.scalars(select(SubmissionAnswer).where(SubmissionAnswer.submission_id == submission.id)).all()
    wrong_answers = [item for item in answers if item.is_correct is False]
    knowledge_counter: dict[int, int] = {}
    for answer in wrong_answers:
        for relation in db.scalars(select(QuestionKnowledgePoint).where(QuestionKnowledgePoint.question_id == answer.question_id)).all():
            knowledge_counter[relation.knowledge_point_id] = knowledge_counter.get(relation.knowledge_point_id, 0) + 1

    weak_knowledge_points = []
    for knowledge_id, wrong_count in sorted(knowledge_counter.items(), key=lambda item: item[1], reverse=True)[:5]:
        knowledge = db.get(KnowledgePoint, knowledge_id)
        weak_knowledge_points.append({"id": knowledge_id, "name": knowledge.name if knowledge else None, "wrong_count": wrong_count})

    analysis = {
        "exam_id": exam.id,
        "submission_id": submission.id,
        "total_questions": len(answers),
        "wrong_question_count": len(wrong_answers),
        "correct_rate": submission.correct_rate,
        "weak_knowledge_points": weak_knowledge_points,
    }
    snapshot = StudentProfileSnapshot(
        student_id=submission.student_id,
        subject_id=exam.subject_id,
        source_exam_id=exam.id,
        profile_json=analysis,
        ai_summary="AI 已根据错题与知识点分布生成本次学情快照。",
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    analysis["snapshot_id"] = snapshot.id
    return analysis


def generate_study_plan(db: Session, submission: ExamSubmission, exam: Exam) -> dict:
    """
    处理 generate study plan 请求并返回结果。
    """
    subject = db.get(Subject, exam.subject_id)
    wrong_answers = db.scalars(
        select(SubmissionAnswer).where(SubmissionAnswer.submission_id == submission.id, SubmissionAnswer.is_correct.is_(False))
    ).all()

    plan = StudyPlan(
        student_id=submission.student_id,
        subject_id=exam.subject_id,
        source_exam_id=exam.id,
        plan_type="post_exam_recovery",
        title=f"{subject.name if subject else '学科'}考后补强计划",
        summary=f"基于考试《{exam.title}》生成的个性化补强任务，共覆盖 {max(1, len(wrong_answers))} 个重点训练点。",
        status="active",
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    created_tasks: list[dict] = []
    dedup_knowledge_ids: set[int] = set()
    for answer in wrong_answers[:5]:
        relation = db.scalar(select(QuestionKnowledgePoint).where(QuestionKnowledgePoint.question_id == answer.question_id))
        knowledge = db.get(KnowledgePoint, relation.knowledge_point_id) if relation else None
        if relation and relation.knowledge_point_id in dedup_knowledge_ids:
            continue
        if relation:
            dedup_knowledge_ids.add(relation.knowledge_point_id)
        task = StudyTask(
            plan_id=plan.id,
            student_id=submission.student_id,
            title=f"复习知识点：{knowledge.name}" if knowledge else f"回顾错题 #{answer.question_id}",
            task_type="knowledge_review" if knowledge else "wrong_question_review",
            knowledge_point_id=knowledge.id if knowledge else None,
            priority=1,
            estimated_minutes=20,
            status="pending",
            feedback="AI 建议先看解析，再完成 2 道同类型训练题。",
        )
        db.add(task)
        db.flush()
        created_tasks.append({"task_id": task.id, "title": task.title, "knowledge_point_id": task.knowledge_point_id})

    if not created_tasks:
        task = StudyTask(
            plan_id=plan.id,
            student_id=submission.student_id,
            title="保持状态训练",
            task_type="consolidation",
            priority=1,
            estimated_minutes=15,
            status="pending",
            feedback="本次客观题表现稳定，建议继续保持每日小练。",
        )
        db.add(task)
        db.flush()
        created_tasks.append({"task_id": task.id, "title": task.title, "knowledge_point_id": None})

    db.commit()
    return {"plan_id": plan.id, "title": plan.title, "tasks": created_tasks}
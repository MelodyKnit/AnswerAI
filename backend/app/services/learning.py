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
    existing_snapshots = db.scalars(
        select(StudentProfileSnapshot).where(
            StudentProfileSnapshot.student_id == submission.student_id,
            StudentProfileSnapshot.source_exam_id == exam.id,
        )
    ).all()
    for item in existing_snapshots:
        db.delete(item)
    db.flush()

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

    existing_plan_ids = db.scalars(
        select(StudyPlan.id).where(
            StudyPlan.student_id == submission.student_id,
            StudyPlan.source_exam_id == exam.id,
        )
    ).all()
    if existing_plan_ids:
        db.query(StudyTask).filter(StudyTask.plan_id.in_(existing_plan_ids)).delete(synchronize_session=False)
        db.query(StudyPlan).filter(StudyPlan.id.in_(existing_plan_ids)).delete(synchronize_session=False)
        db.flush()

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
    knowledge_counter: dict[int, int] = {}
    unmatched_wrong_count = 0
    for answer in wrong_answers:
        relation_ids = db.scalars(
            select(QuestionKnowledgePoint.knowledge_point_id).where(QuestionKnowledgePoint.question_id == answer.question_id)
        ).all()
        if not relation_ids:
            unmatched_wrong_count += 1
            continue
        for knowledge_id in relation_ids:
            knowledge_counter[knowledge_id] = knowledge_counter.get(knowledge_id, 0) + 1

    sorted_knowledge_ids = sorted(knowledge_counter.items(), key=lambda item: item[1], reverse=True)[:3]
    for index, (knowledge_id, wrong_count) in enumerate(sorted_knowledge_ids, start=1):
        knowledge = db.get(KnowledgePoint, knowledge_id)
        task = StudyTask(
            plan_id=plan.id,
            student_id=submission.student_id,
            title=f"复习知识点：{knowledge.name}" if knowledge else "知识点复习",
            task_type="knowledge_review",
            knowledge_point_id=knowledge_id,
            priority=index,
            estimated_minutes=min(35, 15 + wrong_count * 5),
            status="pending",
            feedback=(
                f"本次考试在“{knowledge.name}”相关题上出现 {wrong_count} 次错误，建议先看解析，再完成 2 道同类型训练题。"
                if knowledge
                else "AI 建议先看解析，再完成 2 道同类型训练题。"
            ),
        )
        db.add(task)
        db.flush()
        created_tasks.append({"task_id": task.id, "title": task.title, "knowledge_point_id": task.knowledge_point_id})

    if wrong_answers:
        aggregated_wrong_task = StudyTask(
            plan_id=plan.id,
            student_id=submission.student_id,
            title=f"集中回顾错题（{len(wrong_answers)}题）",
            task_type="wrong_question_review",
            knowledge_point_id=None,
            priority=max(1, len(created_tasks) + 1),
            estimated_minutes=min(40, max(15, len(wrong_answers) * 6)),
            status="pending",
            feedback=(
                f"本次考试共有 {len(wrong_answers)} 道错题，建议先完成解析复盘，再做 2-3 道同类变式题。"
                if unmatched_wrong_count <= 0
                else f"本次考试共有 {len(wrong_answers)} 道错题，其中 {unmatched_wrong_count} 题未归入知识点，请优先做集中错题回顾。"
            ),
        )
        db.add(aggregated_wrong_task)
        db.flush()
        created_tasks.append({"task_id": aggregated_wrong_task.id, "title": aggregated_wrong_task.title, "knowledge_point_id": None})

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
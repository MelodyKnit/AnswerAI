from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import Subject
from app.models.exam import Exam, ExamSubmission, SubmissionAnswer
from app.models.question import Question
from app.models.user import StudentProfileSnapshot, StudyPlan, StudyTask


def build_submission_analysis(db: Session, submission: ExamSubmission, exam: Exam) -> dict:
    """
    基于真实错题生成学情快照（知识点=subject维度）。
    """
    answers = db.scalars(
        select(SubmissionAnswer).where(SubmissionAnswer.submission_id == submission.id)
    ).all()
    wrong_answers = [item for item in answers if item.is_correct is False]

    wrong_subject_counter: dict[str, int] = {}
    for answer in wrong_answers:
        question = db.get(Question, int(answer.question_id))
        subject_name = ""
        if question and question.subject_id:
            subject_obj = db.get(Subject, int(question.subject_id))
            subject_name = str(subject_obj.name or "").strip() if subject_obj else ""
        label = subject_name or "未分类知识点"
        wrong_subject_counter[label] = wrong_subject_counter.get(label, 0) + 1

    weak_knowledge_points = [
        {"id": index + 1, "name": name, "wrong_count": count}
        for index, (name, count) in enumerate(
            sorted(wrong_subject_counter.items(), key=lambda item: item[1], reverse=True)[:5]
        )
    ]

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
        ai_summary="AI 已根据错题分布生成本次学情快照。",
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    analysis["snapshot_id"] = snapshot.id
    return analysis


def generate_study_plan(db: Session, submission: ExamSubmission, exam: Exam) -> dict:
    """
    基于错题生成考后补强学习计划（知识点=subject维度，不依赖知识点表）。
    """
    subject = db.get(Subject, exam.subject_id)
    wrong_answers = db.scalars(
        select(SubmissionAnswer).where(
            SubmissionAnswer.submission_id == submission.id,
            SubmissionAnswer.is_correct.is_(False),
        )
    ).all()

    existing_plan_ids = db.scalars(
        select(StudyPlan.id).where(
            StudyPlan.student_id == submission.student_id,
            StudyPlan.source_exam_id == exam.id,
        )
    ).all()
    if existing_plan_ids:
        db.query(StudyTask).filter(StudyTask.plan_id.in_(existing_plan_ids)).delete(
            synchronize_session=False
        )
        db.query(StudyPlan).filter(StudyPlan.id.in_(existing_plan_ids)).delete(
            synchronize_session=False
        )
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
    wrong_subject_counter: dict[str, int] = {}
    for answer in wrong_answers:
        question = db.get(Question, int(answer.question_id))
        subject_name = ""
        if question and question.subject_id:
            subject_obj = db.get(Subject, int(question.subject_id))
            subject_name = str(subject_obj.name or "").strip() if subject_obj else ""
        key = subject_name or "未分类知识点"
        wrong_subject_counter[key] = wrong_subject_counter.get(key, 0) + 1

    sorted_subjects = sorted(wrong_subject_counter.items(), key=lambda item: item[1], reverse=True)[:3]
    for index, (subject_label, wrong_count) in enumerate(sorted_subjects, start=1):
        task = StudyTask(
            plan_id=plan.id,
            student_id=submission.student_id,
            title=f"复习知识点：{subject_label}",
            task_type="knowledge_review",
            priority=index,
            estimated_minutes=min(35, 15 + wrong_count * 5),
            status="pending",
            feedback=f"本次考试在“{subject_label}”上出现 {wrong_count} 次错误，建议先看解析，再完成 2 道同类型训练题。",
        )
        db.add(task)
        db.flush()
        created_tasks.append({"task_id": task.id, "title": task.title})

    if wrong_answers:
        aggregated_wrong_task = StudyTask(
            plan_id=plan.id,
            student_id=submission.student_id,
            title=f"集中回顾错题（{len(wrong_answers)}题）",
            task_type="wrong_question_review",
            priority=max(1, len(created_tasks) + 1),
            estimated_minutes=min(40, max(15, len(wrong_answers) * 6)),
            status="pending",
            feedback=f"本次考试共有 {len(wrong_answers)} 道错题，建议先完成解析复盘，再做 2-3 道同类变式题。",
        )
        db.add(aggregated_wrong_task)
        db.flush()
        created_tasks.append({"task_id": aggregated_wrong_task.id, "title": aggregated_wrong_task.title})

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
        created_tasks.append({"task_id": task.id, "title": task.title})

    db.commit()
    return {"plan_id": plan.id, "title": plan.title, "tasks": created_tasks}

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.academic import ClassRoom, Subject
from app.models.exam import Exam, ExamClass, ExamSubmission
from app.models.user import Report, User


def build_report_payload(
    db: Session,
    report_type: str,
    exam_id: int | None = None,
    class_id: int | None = None,
    student_id: int | None = None,
    title: str | None = None,
) -> tuple[str, str, dict]:
    """
    处理 build report payload 请求并返回结果。
    """
    if report_type == "exam":
        exam = db.get(Exam, exam_id)
        if not exam:
            raise ValueError("Exam not found")
        submissions = db.scalars(select(ExamSubmission).where(ExamSubmission.exam_id == exam.id)).all()
        scores = [float(item.total_score) for item in submissions]
        subject = db.get(Subject, exam.subject_id)
        report_title = title or f"{exam.title} AI 试卷分析报告"
        summary = f"共统计 {len(submissions)} 份作答，平均分 {round(sum(scores) / len(scores), 2) if scores else 0} 分。"
        content = {
            "overview": {
                "exam_id": exam.id,
                "exam_title": exam.title,
                "subject": subject.name if subject else None,
                "submission_count": len(submissions),
                "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
                "highest_score": max(scores) if scores else 0,
                "lowest_score": min(scores) if scores else 0,
            },
            "sections": [
                {"title": "试卷概览", "content": summary},
                {"title": "教学建议", "content": "建议围绕失分较多题型进行二次讲评，并跟踪薄弱学生的订正完成情况。"},
            ],
        }
        return report_title, summary, content

    if report_type == "class":
        classroom = db.get(ClassRoom, class_id)
        if not classroom:
            raise ValueError("Class not found")
        submissions_query = select(ExamSubmission).where(ExamSubmission.class_id == classroom.id)
        if exam_id is not None:
            submissions_query = submissions_query.where(ExamSubmission.exam_id == exam_id)
        submissions = db.scalars(submissions_query).all()
        scores = [float(item.total_score) for item in submissions]
        report_title = title or f"{classroom.name} 班级学情分析报告"
        summary = f"班级当前统计 {len(submissions)} 份成绩，平均分 {round(sum(scores) / len(scores), 2) if scores else 0} 分。"
        content = {
            "overview": {
                "class_id": classroom.id,
                "class_name": classroom.name,
                "student_count": classroom.student_count,
                "submission_count": len(submissions),
                "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
            },
            "sections": [
                {"title": "班级整体表现", "content": summary},
                {"title": "班级建议", "content": "建议按风险等级分层布置巩固任务，并优先跟进低分段学生。"},
            ],
        }
        return report_title, summary, content

    if report_type == "student":
        student = db.get(User, student_id)
        if not student or student.role != "student":
            raise ValueError("Student not found")
        submission_query = select(ExamSubmission).where(ExamSubmission.student_id == student.id).order_by(ExamSubmission.created_at.desc())
        if exam_id is not None:
            submission_query = select(ExamSubmission).where(ExamSubmission.student_id == student.id, ExamSubmission.exam_id == exam_id)
        submission = db.scalar(submission_query)
        report_title = title or f"{student.name} 个体学习分析报告"
        total_score = float(submission.total_score) if submission else 0
        summary = f"学生 {student.name} 最近一次分析成绩为 {total_score} 分，建议围绕错题开展针对性补强。"
        content = {
            "overview": {
                "student_id": student.id,
                "student_name": student.name,
                "latest_exam_id": submission.exam_id if submission else None,
                "latest_total_score": total_score,
            },
            "sections": [
                {"title": "个体表现", "content": summary},
                {"title": "辅导建议", "content": "建议优先完成 AI 推荐学习任务，并结合教师点评复盘主观题。"},
            ],
        }
        return report_title, summary, content

    report_title = title or "知识专题分析报告"
    summary = "当前阶段生成的是知识专题占位报告，可用于后续扩展到知识图谱分析。"
    content = {
        "overview": {"report_type": report_type, "exam_id": exam_id, "class_id": class_id, "student_id": student_id},
        "sections": [{"title": "专题概述", "content": summary}],
    }
    return report_title, summary, content


def serialize_report(report: Report) -> dict:
    """
    处理 serialize report 请求并返回结果。
    """
    return {
        "id": report.id,
        "report_type": report.report_type,
        "title": report.title,
        "exam_id": report.exam_id,
        "class_id": report.class_id,
        "student_id": report.student_id,
        "status": report.status,
        "summary": report.summary,
        "content_json": report.content_json,
        "file_url": report.file_url,
        "version_no": report.version_no,
        "generated_by_task_id": report.generated_by_task_id,
        "created_by": report.created_by,
        "created_at": report.created_at.isoformat(),
    }
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.response import success_response
from app.models.academic import ClassRoom, ClassStudent
from app.models.exam import Exam
from app.models.user import Report, User
from app.schemas.ai import ReportActionRequest, ReportGenerateRequest
from app.services.reports import build_report_payload, serialize_report
from app.services.tasks import complete_ai_task, mark_ai_task_running, queue_ai_task


router = APIRouter()


def _assert_report_scope(payload: ReportGenerateRequest, current_user: User, db: Session) -> tuple[int | None, int | None, int | None]:
    exam_id = payload.exam_id
    class_id = payload.class_id
    student_id = payload.student_id

    if current_user.role == "student":
        if payload.report_type != "student":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students can only generate personal reports")
        if student_id is not None and student_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return exam_id, None, current_user.id

    if current_user.role == "teacher":
        if class_id is not None:
            classroom = db.scalar(select(ClassRoom).where(ClassRoom.id == class_id, ClassRoom.teacher_id == current_user.id))
            if not classroom:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission for this class")

        if exam_id is not None:
            exam = db.scalar(select(Exam).where(Exam.id == exam_id, Exam.created_by == current_user.id))
            if not exam:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission for this exam")

        if student_id is not None:
            relation = db.scalar(
                select(ClassStudent).where(ClassStudent.student_id == student_id, ClassStudent.teacher_id == current_user.id)
            )
            if not relation:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission for this student")

        return exam_id, class_id, student_id

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


@router.get("/reports")
def list_reports(
    report_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    列出 reports 的数据列表。
    """
    query = select(Report).where((Report.created_by == current_user.id) | (Report.student_id == current_user.id))
    if report_type:
        query = query.where(Report.report_type == report_type)
    items = db.scalars(query.order_by(Report.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return success_response({"items": [serialize_report(item) for item in items], "total": len(items)})


@router.get("/reports/detail")
def get_report_detail(report_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    获取 report detail 相关数据。
    """
    report = db.get(Report, report_id)
    if not report or (report.created_by != current_user.id and report.student_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    content_json = report.content_json or {}
    return success_response({"report": serialize_report(report), "sections": content_json.get("sections", [])})


@router.post("/reports/generate")
def generate_report(payload: ReportGenerateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    处理 generate report 请求并返回结果。
    """
    safe_exam_id, safe_class_id, safe_student_id = _assert_report_scope(payload, current_user, db)

    task = queue_ai_task(
        db,
        task_type="report_generate",
        resource_type="report",
        resource_id=None,
        created_by=current_user.id,
        request_payload={
            **payload.model_dump(),
            "exam_id": safe_exam_id,
            "class_id": safe_class_id,
            "student_id": safe_student_id,
        },
    )
    mark_ai_task_running(db, task, progress=25)
    report_title, summary, content = build_report_payload(
        db,
        report_type=payload.report_type,
        exam_id=safe_exam_id,
        class_id=safe_class_id,
        student_id=safe_student_id,
        title=payload.title,
    )
    report = Report(
        report_type=payload.report_type,
        title=report_title,
        exam_id=safe_exam_id,
        class_id=safe_class_id,
        student_id=safe_student_id,
        status="ready",
        summary=summary,
        content_json=content,
        generated_by_task_id=task.id,
        created_by=current_user.id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    complete_ai_task(db, task, result_payload={"report_id": report.id, "status": report.status})
    return success_response({"task_id": task.task_id, "status": task.status, "report": serialize_report(report)})


@router.post("/reports/export")
def export_report(payload: ReportActionRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    处理 export report 请求并返回结果。
    """
    report = db.get(Report, payload.report_id)
    if not report or (report.created_by != current_user.id and report.student_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    report.file_url = f"/exports/reports/{report.id}.json"
    db.add(report)
    db.commit()
    db.refresh(report)
    return success_response({"report": serialize_report(report)})


@router.post("/reports/share")
def share_report(payload: ReportActionRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    处理 share report 请求并返回结果。
    """
    report = db.get(Report, payload.report_id)
    if not report or (report.created_by != current_user.id and report.student_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return success_response({"report_id": report.id, "share_url": f"https://example.local/reports/share/{report.id}"})
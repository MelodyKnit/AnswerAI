from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.user import AITask
from app.services.realtime import realtime_events, task_channel


def create_ai_task(
    db: Session,
    task_type: str,
    resource_type: str | None,
    resource_id: int | None,
    created_by: int | None,
    request_payload: dict | None = None,
    result_payload: dict | None = None,
    status: str = "success",
    progress: int = 100,
) -> AITask:
    task = AITask(
        task_id=f"task_{uuid4().hex[:12]}",
        type=task_type,
        status=status,
        progress=progress,
        resource_type=resource_type,
        resource_id=resource_id,
        created_by=created_by,
        request_payload=request_payload,
        result_payload=result_payload,
        finished_at=datetime.now(UTC) if status in {"success", "failed"} else None,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    realtime_events.publish(task_channel(task.task_id), "task_progress", serialize_ai_task(task))
    return task


def queue_ai_task(
    db: Session,
    task_type: str,
    resource_type: str | None,
    resource_id: int | None,
    created_by: int | None,
    request_payload: dict | None = None,
) -> AITask:
    return create_ai_task(
        db,
        task_type=task_type,
        resource_type=resource_type,
        resource_id=resource_id,
        created_by=created_by,
        request_payload=request_payload,
        result_payload=None,
        status="pending",
        progress=0,
    )


def mark_ai_task_running(db: Session, task: AITask, progress: int = 10) -> AITask:
    task.status = "processing"
    task.progress = progress
    task.finished_at = None
    db.add(task)
    db.commit()
    db.refresh(task)
    realtime_events.publish(task_channel(task.task_id), "task_progress", serialize_ai_task(task))
    return task


def complete_ai_task(db: Session, task: AITask, result_payload: dict | None = None, progress: int = 100) -> AITask:
    task.status = "success"
    task.progress = progress
    task.result_payload = result_payload
    task.finished_at = datetime.now(UTC)
    db.add(task)
    db.commit()
    db.refresh(task)
    realtime_events.publish(task_channel(task.task_id), "task_progress", serialize_ai_task(task))
    return task


def fail_ai_task(db: Session, task: AITask, error_message: str) -> AITask:
    task.status = "failed"
    task.error_message = error_message
    task.finished_at = datetime.now(UTC)
    db.add(task)
    db.commit()
    db.refresh(task)
    realtime_events.publish(task_channel(task.task_id), "task_progress", serialize_ai_task(task))
    return task


def serialize_ai_task(task: AITask) -> dict:
    return {
        "task_id": task.task_id,
        "type": task.type,
        "status": task.status,
        "progress": task.progress,
        "resource_type": task.resource_type,
        "resource_id": task.resource_id,
        "request_payload": task.request_payload,
        "result_payload": task.result_payload,
        "error_message": task.error_message,
        "created_by": task.created_by,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }

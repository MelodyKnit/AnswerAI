from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.response import success_response
from app.models.user import AITask, User
from app.schemas.ai import TaskStatusBatchRequest
from app.services.tasks import serialize_ai_task


router = APIRouter()


@router.get("/ai/tasks/status")
def get_task_status(task_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.scalar(select(AITask).where(AITask.task_id == task_id, AITask.created_by == current_user.id))
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return success_response({"task": serialize_ai_task(task)})


@router.post("/ai/tasks/status/batch")
def get_task_status_batch(payload: TaskStatusBatchRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tasks = db.scalars(select(AITask).where(AITask.task_id.in_(payload.task_ids), AITask.created_by == current_user.id)).all()
    return success_response({"tasks": [serialize_ai_task(task) for task in tasks]})
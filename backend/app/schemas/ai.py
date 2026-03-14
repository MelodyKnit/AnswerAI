from pydantic import BaseModel, Field


class TaskStatusBatchRequest(BaseModel):
    task_ids: list[str] = Field(min_length=1)


class ReportGenerateRequest(BaseModel):
    report_type: str = Field(pattern="^(exam|class|student|knowledge_topic)$")
    exam_id: int | None = None
    class_id: int | None = None
    student_id: int | None = None
    title: str | None = None


class ReportActionRequest(BaseModel):
    report_id: int
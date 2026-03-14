from datetime import datetime

from pydantic import BaseModel


class StartExamRequest(BaseModel):
    exam_id: int


class SaveAnswerRequest(BaseModel):
    exam_id: int
    submission_id: int
    question_id: int
    answer: list[str] | str | None = None
    answer_text: str | None = None
    spent_seconds: int = 0
    mark_difficult: bool = False
    favorite: bool = False


class BatchAnswerItem(BaseModel):
    question_id: int
    answer: list[str] | str | None = None
    answer_text: str | None = None
    spent_seconds: int = 0


class BatchSaveAnswerRequest(BaseModel):
    exam_id: int
    submission_id: int
    answers: list[BatchAnswerItem]


class BehaviorEventInput(BaseModel):
    question_id: int | None = None
    event_type: str
    occurred_at: datetime
    payload: dict | None = None


class BehaviorReportRequest(BaseModel):
    exam_id: int
    submission_id: int
    events: list[BehaviorEventInput]


class SubmitExamRequest(BaseModel):
    exam_id: int
    submission_id: int
    confirm_submit: bool

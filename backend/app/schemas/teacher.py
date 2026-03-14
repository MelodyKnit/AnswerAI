from datetime import datetime

from pydantic import BaseModel


class ClassCreateRequest(BaseModel):
    name: str
    grade_name: str
    subject: str


class QuestionOptionInput(BaseModel):
    key: str
    content: str


class QuestionCreateRequest(BaseModel):
    subject: str
    type: str
    stem: str
    options: list[QuestionOptionInput] = []
    answer: list[str] | str
    analysis: str | None = None
    score: float
    difficulty: float | None = None
    knowledge_point_ids: list[int] = []
    ability_tags: list[str] = []


class QuestionUpdateRequest(BaseModel):
    question_id: int
    subject: str | None = None
    type: str | None = None
    stem: str | None = None
    options: list[QuestionOptionInput] | None = None
    answer: list[str] | str | None = None
    analysis: str | None = None
    score: float | None = None
    difficulty: float | None = None
    knowledge_point_ids: list[int] | None = None
    ability_tags: list[str] | None = None


class DeleteRequest(BaseModel):
    question_id: int | None = None
    exam_id: int | None = None


class ImportQuestionsRequest(BaseModel):
    file_url: str | None = None
    import_type: str
    subject: str


class AIQuestionGenerateRequest(BaseModel):
    subject: str
    grade_name: str | None = None
    question_type: str
    requirement: str
    knowledge_points: list[str] = []
    difficulty: float | None = None
    count: int = 1
    with_analysis: bool = True


class AIQuestionReviewRequest(BaseModel):
    question_id: int


class ExamQuestionItemInput(BaseModel):
    question_id: int
    score: float
    order_no: int
    section_name: str | None = None


class ExamCreateRequest(BaseModel):
    title: str
    subject: str
    duration_minutes: int
    start_time: datetime
    end_time: datetime
    instructions: str | None = None
    allow_review: bool = True
    random_question_order: bool = False
    class_ids: list[int]
    question_items: list[ExamQuestionItemInput]


class ExamUpdateRequest(BaseModel):
    exam_id: int
    title: str | None = None
    duration_minutes: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    instructions: str | None = None
    allow_review: bool | None = None
    random_question_order: bool | None = None
    class_ids: list[int] | None = None
    question_items: list[ExamQuestionItemInput] | None = None


class ExamActionRequest(BaseModel):
    exam_id: int


class ReviewSubmitRequest(BaseModel):
    review_item_id: int
    final_score: float
    review_comment: str | None = None


class AIScoreRequest(BaseModel):
    exam_id: int
    submission_id: int

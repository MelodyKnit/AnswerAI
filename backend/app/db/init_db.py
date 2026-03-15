from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.db.session import engine

from app.models.academic import Subject


DEFAULT_SUBJECTS = [
    ("math", "数学"),
    ("chinese", "语文"),
    ("english", "英语"),
    ("physics", "物理"),
    ("chemistry", "化学"),
    ("biology", "生物"),
]


def seed_subjects(db: Session) -> None:
    """
    处理 seed subjects 请求并返回结果。
    """
    if not inspect(engine).has_table("subjects"):
        return

    exists = db.scalar(select(Subject.id).limit(1))
    if exists:
        return

    for index, (code, name) in enumerate(DEFAULT_SUBJECTS, start=1):
        db.add(Subject(code=code, name=name, sort_order=index, status="active"))
    db.commit()

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.response import success_response
from app.models.academic import Subject


router = APIRouter()

QUESTION_TYPES = [
    {"code": "single_choice", "name": "单选题"},
    {"code": "multiple_choice", "name": "多选题"},
    {"code": "judge", "name": "判断题"},
    {"code": "blank", "name": "填空题"},
    {"code": "essay", "name": "简答题"},
    {"code": "material", "name": "材料题"},
]

GRADES = [
    {"code": "grade7", "name": "初一"},
    {"code": "grade8", "name": "初二"},
    {"code": "grade9", "name": "初三"},
    {"code": "grade10", "name": "高一"},
    {"code": "grade11", "name": "高二"},
    {"code": "grade12", "name": "高三"},
]


@router.get("/meta/subjects")
def get_subjects(db: Session = Depends(get_db)):
    """
    获取 subjects 相关数据。
    """
    items = db.scalars(select(Subject).where(Subject.status == "active").order_by(Subject.sort_order.asc())).all()
    return success_response({"items": [{"id": item.id, "code": item.code, "name": item.name} for item in items]})


@router.get("/meta/grades")
def get_grades():
    """
    获取 grades 相关数据。
    """
    return success_response({"items": GRADES})


@router.get("/meta/question-types")
def get_question_types():
    """
    获取 question types 相关数据。
    """
    return success_response({"items": QUESTION_TYPES})


@router.get("/meta/knowledge-points/tree")
def get_knowledge_tree(subject: str, db: Session = Depends(get_db)):
    """
    获取知识点树（当前按知识点名=subject名返回一层节点）。
    """
    subject_obj = db.scalar(select(Subject).where(Subject.name == subject))
    if not subject_obj:
        return success_response({"items": []})

    return success_response(
        {
            "items": [
                {
                    "id": subject_obj.id,
                    "name": subject_obj.name,
                    "path": subject_obj.name,
                    "level": 1,
                    "children": [],
                }
            ]
        }
    )

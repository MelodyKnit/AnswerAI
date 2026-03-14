from fastapi import APIRouter

from app.api.routes import ai, auth, meta, reports, student, teacher, ws


api_router = APIRouter()
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(meta.router, tags=["meta"])
api_router.include_router(teacher.router, tags=["teacher"])
api_router.include_router(student.router, tags=["student"])
api_router.include_router(ai.router, tags=["ai"])
api_router.include_router(reports.router, tags=["reports"])

ws_router = APIRouter()
ws_router.include_router(ws.router)

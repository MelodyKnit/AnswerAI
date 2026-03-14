from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router, ws_router
from app.core.config import settings
from app.core.response import success_response
from app.db.init_db import seed_subjects
from app.db.session import SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        seed_subjects(db)
    finally:
        db.close()
    yield


app = FastAPI(title=settings.project_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return success_response({"status": "ok"})


app.include_router(api_router, prefix=settings.api_v1_prefix)
app.include_router(ws_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
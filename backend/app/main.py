import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.admin import routes as admin_pages
from app.api.v1 import admin, ai, auth, bookmarks, content, practice, progress, questions
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="1.0.0", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    auth.router,
    content.router,
    questions.router,
    practice.router,
    progress.router,
    bookmarks.router,
    ai.router,
    admin.router,
):
    app.include_router(router, prefix=settings.api_v1_prefix)

app.include_router(admin_pages.router)

os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "ai_configured": settings.ai_enabled}

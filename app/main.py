"""SupportPilot — AI helpdesk SaaS for online stores (FastAPI + SQLite)."""
import os

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import models
from .auth import get_current_user
from .db import Base, engine, get_db
from .routers import analytics, auth, billing, kb, tickets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SupportPilot API",
    version="1.0.0",
    description="AI helpdesk SaaS for online stores. AI drafts need human approval; billing is MOCK in this build.",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(kb.router)
app.include_router(billing.router)
app.include_router(analytics.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "SupportPilot API", "version": "1.0.0"}


@app.get("/api")
def api_root():
    return {
        "service": "SupportPilot API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "app": "/app",
        "help_center": "/help",
    }


@app.get("/")
def landing():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/app")
def dashboard():
    return FileResponse(os.path.join(STATIC_DIR, "app.html"))


@app.get("/help")
def help_center():
    return FileResponse(os.path.join(STATIC_DIR, "help.html"))


@app.get("/public/kb")
def public_kb(workspace_id: int, db: Session = Depends(get_db)):
    """Public help center for ONE workspace (workspace_id required) — a
    workspace's published articles are never mixed with another's."""
    articles = (
        db.query(models.KBArticle)
        .filter(
            models.KBArticle.workspace_id == workspace_id,
            models.KBArticle.published == True,  # noqa: E712
        )
        .order_by(models.KBArticle.created_at.desc())
        .limit(50)
        .all()
    )
    return {
        "articles": [
            {"id": a.id, "title": a.title, "category": a.category, "body": a.body}
            for a in articles
        ]
    }

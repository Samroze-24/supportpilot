"""Knowledge base router: CRUD + public help-center listing."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..models import KBArticle, User
from ..schemas import KBCreate, KBUpdate

router = APIRouter(prefix="/kb", tags=["kb"])


def _get_article_or_404(db: Session, workspace_id: int, article_id: int) -> KBArticle:
    article = (
        db.query(KBArticle)
        .filter(KBArticle.id == article_id, KBArticle.workspace_id == workspace_id)
        .first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


def _out(a: KBArticle) -> dict:
    return {"id": a.id, "title": a.title, "body": a.body, "category": a.category, "published": a.published}


@router.get("")
def list_kb(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    articles = db.query(KBArticle).filter(KBArticle.workspace_id == user.workspace_id).order_by(KBArticle.created_at.desc()).all()
    return {"articles": [_out(a) for a in articles]}


@router.post("", status_code=201)
def create_kb(payload: KBCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    article = KBArticle(workspace_id=user.workspace_id, title=payload.title, body=payload.body, category=payload.category, published=payload.published)
    db.add(article)
    db.commit()
    db.refresh(article)
    return _out(article)


@router.get("/{article_id}")
def get_kb(article_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _out(_get_article_or_404(db, user.workspace_id, article_id))


@router.patch("/{article_id}")
def update_kb(article_id: int, payload: KBUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    a = _get_article_or_404(db, user.workspace_id, article_id)
    if payload.title is not None:
        a.title = payload.title
    if payload.body is not None:
        a.body = payload.body
    if payload.category is not None:
        a.category = payload.category
    if payload.published is not None:
        a.published = payload.published
    db.commit()
    db.refresh(a)
    return _out(a)


@router.delete("/{article_id}")
def delete_kb(article_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    a = _get_article_or_404(db, user.workspace_id, article_id)
    db.delete(a)
    db.commit()
    return {"deleted": True}

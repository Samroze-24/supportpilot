"""Tickets router: shared inbox, replies, notes, AI drafts, KB suggestions.
Every query is scoped to the caller's workspace (strict isolation)."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..ai import generate_draft, suggest_kb_articles, triage
from ..auth import get_current_user
from ..db import get_db
from ..models import Draft, KBArticle, Ticket, TicketNote, TicketReply, User, Workspace
from ..schemas import (DraftCreate, DraftUpdate, NoteCreate, ReplyCreate,
                       ResolveIn, TicketCreate, TicketUpdate)
from ..services import can_create_ticket, plan_config

router = APIRouter(prefix="/tickets", tags=["tickets"])

VALID_STATUSES = {"open", "pending", "resolved"}
VALID_PRIORITIES = {"low", "normal", "high", "urgent"}
VALID_CHANNELS = {"email", "chat", "whatsapp"}


def _get_ticket_or_404(db: Session, workspace_id: int, ticket_id: int) -> Ticket:
    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id, Ticket.workspace_id == workspace_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


def _ticket_dict(t: Ticket) -> dict:
    return {
        "id": t.id,
        "number": t.number,
        "subject": t.subject,
        "body": t.body,
        "customer_name": t.customer_name,
        "customer_email": t.customer_email,
        "customer_country": t.customer_country,
        "channel": t.channel,
        "status": t.status,
        "priority": t.priority,
        "tags": t.tags,
        "assignee_id": t.assignee_id,
        "ai_intent": t.ai_intent,
        "ai_sentiment": t.ai_sentiment,
        "ai_priority": t.ai_priority,
        "ai_confidence": t.ai_confidence,
        "ai_accepted": t.ai_accepted,
        "sla_hours": t.sla_hours,
        "csat_rating": t.csat_rating,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


@router.get("")
def list_tickets(
    status: str = Query(default=None),
    channel: str = Query(default=None),
    intent: str = Query(default=None),
    search: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Ticket).filter(Ticket.workspace_id == user.workspace_id)
    if status:
        q = q.filter(Ticket.status == status)
    if channel:
        q = q.filter(Ticket.channel == channel)
    if intent:
        q = q.filter(Ticket.ai_intent == intent)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(Ticket.subject.ilike(like), Ticket.body.ilike(like), Ticket.customer_name.ilike(like), Ticket.number.ilike(like)))
    total = q.count()
    tickets = q.order_by(Ticket.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return {"total": total, "page": page, "per_page": per_page, "tickets": [_ticket_dict(t) for t in tickets]}


@router.post("", status_code=201)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    workspace = db.query(Workspace).filter(Workspace.id == user.workspace_id).first()
    allowed, reason = can_create_ticket(db, workspace)
    if not allowed:
        raise HTTPException(status_code=402, detail=reason)
    if payload.channel not in VALID_CHANNELS:
        raise HTTPException(status_code=400, detail="channel must be email, chat or whatsapp")
    result = triage(f"{payload.subject}. {payload.body}")
    priority = payload.priority if payload.priority in VALID_PRIORITIES else result["priority"]
    count = db.query(Ticket).filter(Ticket.workspace_id == user.workspace_id).count()
    ticket = Ticket(
        workspace_id=user.workspace_id,
        number=f"SP-{1001 + count}",
        subject=payload.subject,
        body=payload.body,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        customer_country=payload.customer_country,
        channel=payload.channel,
        status="open",
        priority=priority,
        tags=payload.tags,
        ai_intent=result["intent"],
        ai_sentiment=result["sentiment"],
        ai_priority=result["priority"],
        ai_confidence=str(result["confidence"]),
        sla_hours=plan_config(workspace.plan)["sla_hours"],
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    # Auto-create an AI draft reply (drafted — never sent automatically).
    draft = Draft(
        ticket_id=ticket.id,
        workspace_id=user.workspace_id,
        body=generate_draft(result["intent"], payload.customer_name, payload.body),
        status="drafted",
        created_by_id=user.id,
    )
    db.add(draft)
    db.commit()
    return {**_ticket_dict(ticket), "draft_id": draft.id}


@router.get("/{ticket_id}")
def get_ticket(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = _get_ticket_or_404(db, user.workspace_id, ticket_id)
    replies = db.query(TicketReply).filter(TicketReply.ticket_id == t.id).order_by(TicketReply.created_at).all()
    notes = db.query(TicketNote).filter(TicketNote.ticket_id == t.id).order_by(TicketNote.created_at).all()
    drafts = db.query(Draft).filter(Draft.ticket_id == t.id).order_by(Draft.created_at).all()
    return {
        **_ticket_dict(t),
        "replies": [{"id": r.id, "author_name": r.author_name, "body": r.body, "internal": r.internal, "created_at": r.created_at.isoformat() if r.created_at else None} for r in replies],
        "notes": [{"id": n.id, "author_name": n.author_name, "body": n.body, "created_at": n.created_at.isoformat() if n.created_at else None} for n in notes],
        "drafts": [{"id": d.id, "body": d.body, "status": d.status, "created_at": d.created_at.isoformat() if d.created_at else None} for d in drafts],
    }


@router.patch("/{ticket_id}")
def update_ticket(ticket_id: int, payload: TicketUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = _get_ticket_or_404(db, user.workspace_id, ticket_id)
    if payload.status is not None:
        if payload.status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status")
        t.status = payload.status
        if payload.status == "resolved" and not t.resolved_at:
            t.resolved_at = datetime.utcnow()
    if payload.priority is not None:
        if payload.priority not in VALID_PRIORITIES:
            raise HTTPException(status_code=400, detail="Invalid priority")
        t.priority = payload.priority
    if payload.assignee_id is not None:
        assignee = db.query(User).filter(User.id == payload.assignee_id, User.workspace_id == user.workspace_id).first()
        if not assignee:
            raise HTTPException(status_code=400, detail="Assignee must belong to this workspace")
        t.assignee_id = payload.assignee_id
    if payload.tags is not None:
        t.tags = payload.tags
    if payload.ai_accepted is not None:
        t.ai_accepted = payload.ai_accepted
    db.commit()
    db.refresh(t)
    return _ticket_dict(t)


@router.post("/{ticket_id}/resolve")
def resolve_ticket(ticket_id: int, payload: ResolveIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = _get_ticket_or_404(db, user.workspace_id, ticket_id)
    t.status = "resolved"
    t.resolved_at = datetime.utcnow()
    if payload.csat_rating is not None:
        t.csat_rating = payload.csat_rating
    db.commit()
    db.refresh(t)
    return _ticket_dict(t)


@router.post("/{ticket_id}/replies", status_code=201)
def add_reply(ticket_id: int, payload: ReplyCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = _get_ticket_or_404(db, user.workspace_id, ticket_id)
    reply = TicketReply(ticket_id=t.id, author_id=user.id, author_name=user.name, body=payload.body, internal=payload.internal)
    db.add(reply)
    if not t.first_response_at and not payload.internal:
        t.first_response_at = datetime.utcnow()
    if t.status == "open":
        t.status = "pending"
    db.commit()
    db.refresh(reply)
    return {"id": reply.id, "author_name": reply.author_name, "body": reply.body, "internal": reply.internal}


@router.post("/{ticket_id}/notes", status_code=201)
def add_note(ticket_id: int, payload: NoteCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = _get_ticket_or_404(db, user.workspace_id, ticket_id)
    note = TicketNote(ticket_id=t.id, author_id=user.id, author_name=user.name, body=payload.body)
    db.add(note)
    db.commit()
    db.refresh(note)
    return {"id": note.id, "author_name": note.author_name, "body": note.body}


@router.post("/{ticket_id}/drafts", status_code=201)
def create_draft(ticket_id: int, payload: DraftCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = _get_ticket_or_404(db, user.workspace_id, ticket_id)
    body = payload.body or generate_draft(t.ai_intent or "other", t.customer_name, t.body)
    draft = Draft(ticket_id=t.id, workspace_id=user.workspace_id, body=body, status="drafted", created_by_id=user.id)
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return {"id": draft.id, "body": draft.body, "status": draft.status}


@router.patch("/drafts/{draft_id}")
def update_draft(draft_id: int, payload: DraftUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    draft = db.query(Draft).filter(Draft.id == draft_id, Draft.workspace_id == user.workspace_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if payload.status not in ("approved", "sent"):
        raise HTTPException(status_code=400, detail="status must be approved or sent")
    if payload.status == "sent" and draft.status not in ("approved", "drafted"):
        raise HTTPException(status_code=400, detail="Only an approved or drafted reply can be sent")
    if payload.body is not None:
        draft.body = payload.body
    draft.status = payload.status
    db.commit()
    if payload.status == "sent":
        # Sending is a mock action: the reply is recorded on the ticket thread,
        # nothing is actually emailed or messaged to the customer.
        ticket = db.query(Ticket).filter(Ticket.id == draft.ticket_id).first()
        reply = TicketReply(ticket_id=ticket.id, author_id=user.id, author_name=user.name, body=draft.body, internal=False)
        db.add(reply)
        if not ticket.first_response_at:
            ticket.first_response_at = datetime.utcnow()
        if ticket.status == "open":
            ticket.status = "pending"
        db.commit()
    db.refresh(draft)
    return {"id": draft.id, "body": draft.body, "status": draft.status}


@router.get("/{ticket_id}/suggest-kb")
def suggest_kb(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = _get_ticket_or_404(db, user.workspace_id, ticket_id)
    articles = db.query(KBArticle).filter(KBArticle.workspace_id == user.workspace_id, KBArticle.published == True).all()  # noqa: E712
    suggestions = suggest_kb_articles(f"{t.subject} {t.body}", articles)
    return {"suggestions": [{"id": a.id, "title": a.title, "category": a.category, "score": s} for a, s in suggestions]}

"""Analytics router: ticket breakdowns, response time, resolution rate, CSAT."""
from collections import Counter
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..models import Ticket, User

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def analytics_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tickets = db.query(Ticket).filter(Ticket.workspace_id == user.workspace_id).all()
    total = len(tickets)
    by_status = dict(Counter(t.status for t in tickets))
    by_intent = dict(Counter(t.ai_intent or "unknown" for t in tickets))
    by_channel = dict(Counter(t.channel for t in tickets))
    resolved = [t for t in tickets if t.status == "resolved"]
    resolution_rate = round(len(resolved) / total, 3) if total else 0.0
    response_hours = []
    for t in tickets:
        if t.first_response_at and t.created_at:
            delta = (t.first_response_at - t.created_at).total_seconds() / 3600
            response_hours.append(max(delta, 0.01))
    avg_first_response_hours = round(sum(response_hours) / len(response_hours), 2) if response_hours else None
    ratings = [t.csat_rating for t in resolved if t.csat_rating]
    avg_csat = round(sum(ratings) / len(ratings), 2) if ratings else None
    return {
        "total_tickets": total,
        "by_status": by_status,
        "by_intent": by_intent,
        "by_channel": by_channel,
        "resolution_rate": resolution_rate,
        "avg_first_response_hours": avg_first_response_hours,
        "avg_csat": avg_csat,
        "csat_responses": len(ratings),
        "generated_at": datetime.utcnow().isoformat(),
    }

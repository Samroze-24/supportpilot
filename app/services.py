"""Billing plans, usage limits and SLA rules (server-side enforced)."""
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func

from .models import Ticket, User, Workspace

PLANS = {
    "free": {
        "name": "Free",
        "price_usd": 0,
        "tickets_per_month": 50,
        "max_agents": 1,
        "sla_hours": 24,
    },
    "pro": {
        "name": "Pro",
        "price_usd": 19,
        "tickets_per_month": 500,
        "max_agents": 5,
        "sla_hours": 4,
    },
    "business": {
        "name": "Business",
        "price_usd": 49,
        "tickets_per_month": None,  # unlimited
        "max_agents": None,  # unlimited
        "sla_hours": 1,
    },
}


def plan_config(plan: str) -> dict:
    return PLANS.get(plan, PLANS["free"])


def tickets_this_month(db: Session, workspace_id: int) -> int:
    now = datetime.utcnow()
    return (
        db.query(func.count(Ticket.id))
        .filter(
            Ticket.workspace_id == workspace_id,
            func.strftime("%Y-%m", Ticket.created_at) == now.strftime("%Y-%m"),
        )
        .scalar()
        or 0
    )


def agents_count(db: Session, workspace_id: int) -> int:
    return db.query(func.count(User.id)).filter(User.workspace_id == workspace_id).scalar() or 0


def can_create_ticket(db: Session, workspace: Workspace) -> tuple:
    """Returns (allowed, reason). Enforces the monthly ticket cap."""
    cfg = plan_config(workspace.plan)
    limit = cfg["tickets_per_month"]
    if limit is None:
        return True, ""
    used = tickets_this_month(db, workspace.id)
    if used >= limit:
        return False, (
            f"Monthly ticket limit reached ({used}/{limit} on the {cfg['name']} plan). "
            "Upgrade your plan to create more tickets."
        )
    return True, ""


def can_add_agent(db: Session, workspace: Workspace) -> tuple:
    cfg = plan_config(workspace.plan)
    limit = cfg["max_agents"]
    if limit is None:
        return True, ""
    count = agents_count(db, workspace.id)
    if count >= limit:
        return False, (
            f"Agent limit reached ({count}/{limit} on the {cfg['name']} plan). "
            "Upgrade your plan to invite more agents."
        )
    return True, ""

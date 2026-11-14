"""Billing router: plan status, usage, MOCK checkout (no real Stripe, no real money)."""
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_role
from ..db import get_db
from ..models import BillingRecord, User, Workspace
from ..schemas import CheckoutIn
from ..services import agents_count, plan_config, tickets_this_month

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("")
def billing_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    workspace = db.query(Workspace).filter(Workspace.id == user.workspace_id).first()
    cfg = plan_config(workspace.plan)
    payments = (
        db.query(BillingRecord)
        .filter(BillingRecord.workspace_id == user.workspace_id)
        .order_by(BillingRecord.created_at.desc())
        .all()
    )
    return {
        "plan": workspace.plan,
        "plan_name": cfg["name"],
        "price_usd": cfg["price_usd"],
        "sla_hours": cfg["sla_hours"],
        "tickets_per_month": cfg["tickets_per_month"],
        "tickets_used_this_month": tickets_this_month(db, user.workspace_id),
        "max_agents": cfg["max_agents"],
        "agents": agents_count(db, user.workspace_id),
        "mock": True,
        "payments": [
            {"id": p.id, "plan": p.plan, "amount_usd": p.amount_usd, "reference": p.reference, "status": p.status}
            for p in payments
        ],
    }


@router.post("/checkout")
def checkout(payload: CheckoutIn, db: Session = Depends(get_db), user: User = Depends(require_role("owner", "admin"))):
    if payload.plan not in ("pro", "business"):
        raise HTTPException(status_code=400, detail="plan must be pro or business (Free is the default)")
    cfg = plan_config(payload.plan)
    workspace = db.query(Workspace).filter(Workspace.id == user.workspace_id).first()
    # MOCK checkout: no real payment gateway is called, no real money moves.
    reference = f"MOCK-STRIPE-{secrets.token_hex(6).upper()}"
    record = BillingRecord(
        workspace_id=user.workspace_id,
        plan=payload.plan,
        amount_usd=cfg["price_usd"],
        reference=reference,
        status="paid",
    )
    db.add(record)
    workspace.plan = payload.plan
    db.commit()
    db.refresh(record)
    return {
        "plan": payload.plan,
        "amount_usd": cfg["price_usd"],
        "reference": reference,
        "status": "paid",
        "mock": True,
        "message": f"Upgraded to {cfg['name']} (MOCK payment — no real money was charged).",
    }

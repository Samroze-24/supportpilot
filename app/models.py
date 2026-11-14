"""SQLAlchemy models for SupportPilot.

Multi-tenant: every row that belongs to a store carries workspace_id.
No query may return rows from another workspace — all routers filter on it.
"""
from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer,
                        String, Text)

from .db import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    plan = Column(String(20), nullable=False, default="free")  # free | pro | business
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False, unique=True, index=True)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False, default="agent")  # owner | admin | agent
    created_at = Column(DateTime, default=datetime.utcnow)


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    number = Column(String(20), nullable=False, index=True)  # e.g. SP-1001
    subject = Column(String(300), nullable=False)
    body = Column(Text, nullable=False)
    customer_name = Column(String(200), nullable=False, default="Customer")
    customer_email = Column(String(200), nullable=False, default="")
    customer_country = Column(String(100), nullable=False, default="")
    channel = Column(String(20), nullable=False, default="email")  # email | chat | whatsapp
    status = Column(String(20), nullable=False, default="open")  # open | pending | resolved
    priority = Column(String(20), nullable=False, default="normal")  # low | normal | high | urgent
    tags = Column(String(300), nullable=False, default="")
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # AI triage suggestions (agent may accept or override)
    ai_intent = Column(String(50), nullable=True)
    ai_sentiment = Column(String(20), nullable=True)
    ai_priority = Column(String(20), nullable=True)
    ai_confidence = Column(String(20), nullable=True)
    ai_accepted = Column(Boolean, nullable=False, default=False)
    sla_hours = Column(Integer, nullable=False, default=24)
    first_response_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    csat_rating = Column(Integer, nullable=True)  # 1-5, given on resolution
    created_at = Column(DateTime, default=datetime.utcnow)


class TicketReply(Base):
    __tablename__ = "ticket_replies"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    author_name = Column(String(200), nullable=False, default="Agent")
    body = Column(Text, nullable=False)
    internal = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class TicketNote(Base):
    __tablename__ = "ticket_notes"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    author_name = Column(String(200), nullable=False, default="Agent")
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Draft(Base):
    __tablename__ = "drafts"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    body = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="drafted")  # drafted | approved | sent
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class KBArticle(Base):
    __tablename__ = "kb_articles"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    body = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, default="General")
    published = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BillingRecord(Base):
    __tablename__ = "billing_records"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    plan = Column(String(20), nullable=False)
    amount_usd = Column(Integer, nullable=False)
    reference = Column(String(100), nullable=False)  # MOCK-STRIPE-... (no real money)
    status = Column(String(20), nullable=False, default="paid")
    created_at = Column(DateTime, default=datetime.utcnow)

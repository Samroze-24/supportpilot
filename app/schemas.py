"""Pydantic schemas (request/response shapes)."""
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class SignupIn(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=6)
    workspace_name: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class InviteIn(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=6)
    role: str = "agent"


class UserOut(BaseModel):
    id: int
    workspace_id: int
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class TicketCreate(BaseModel):
    subject: str
    body: str
    customer_name: str = "Customer"
    customer_email: str = ""
    customer_country: str = ""
    channel: str = "email"
    priority: Optional[str] = None
    tags: str = ""


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[int] = None
    tags: Optional[str] = None
    ai_accepted: Optional[bool] = None


class ReplyCreate(BaseModel):
    body: str
    internal: bool = False


class NoteCreate(BaseModel):
    body: str


class DraftCreate(BaseModel):
    body: Optional[str] = None


class DraftUpdate(BaseModel):
    status: str  # approved | sent
    body: Optional[str] = None


class ResolveIn(BaseModel):
    csat_rating: Optional[int] = Field(default=None, ge=1, le=5)


class KBCreate(BaseModel):
    title: str
    body: str
    category: str = "General"
    published: bool = True


class KBUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    category: Optional[str] = None
    published: Optional[bool] = None


class CheckoutIn(BaseModel):
    plan: str  # pro | business


class TicketOut(BaseModel):
    id: int
    number: str
    subject: str
    body: str
    customer_name: str
    customer_email: str
    customer_country: str
    channel: str
    status: str
    priority: str
    tags: str
    assignee_id: Optional[int]
    ai_intent: Optional[str]
    ai_sentiment: Optional[str]
    ai_priority: Optional[str]
    ai_confidence: Optional[str]
    ai_accepted: bool
    sla_hours: int
    csat_rating: Optional[int]
    created_at: Optional[str]

    class Config:
        from_attributes = True

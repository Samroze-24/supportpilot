"""Auth router: signup (creates workspace + owner), JSON login, form login
(for Swagger Authorize), invite agent, me."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..auth import (create_access_token, get_current_user, get_password_hash,
                    require_role, verify_password)
from ..db import get_db
from ..models import User, Workspace
from ..schemas import InviteIn, LoginIn, SignupIn, TokenOut, UserOut
from ..services import can_add_agent

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user: User) -> TokenOut:
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.from_orm(user))


@router.post("/signup", response_model=TokenOut)
def signup(payload: SignupIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    workspace = Workspace(name=payload.workspace_name, plan="free")
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    user = User(
        workspace_id=workspace.id,
        name=payload.name,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role="owner",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.post("/login", response_model=TokenOut)
def login_json(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _token_response(user)


@router.post("/login-form", response_model=TokenOut)
def login_form(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Form login used by Swagger Authorize (OAuth2 password flow)."""
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _token_response(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/invite", response_model=UserOut)
def invite(payload: InviteIn, db: Session = Depends(get_db), user: User = Depends(require_role("owner", "admin"))):
    workspace = db.query(Workspace).filter(Workspace.id == user.workspace_id).first()
    allowed, reason = can_add_agent(db, workspace)
    if not allowed:
        raise HTTPException(status_code=402, detail=reason)
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if payload.role not in ("agent", "admin"):
        raise HTTPException(status_code=400, detail="Role must be agent or admin")
    new_user = User(
        workspace_id=user.workspace_id,
        name=payload.name,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

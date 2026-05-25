from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.deps import get_current_user, get_user_roles
from app.models import RefreshToken, User
from app.schemas import LoginRequest, LogoutRequest, RefreshRequest, TokenResponse, UserOut
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    token_hash,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _build_user_out(db: Session, user: User) -> UserOut:
    return UserOut(
        user_id=user.user_id,
        username=user.username,
        roles=get_user_roles(db, user.user_id),
        is_active=user.is_active,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    roles = get_user_roles(db, user.user_id)
    access_token = create_access_token(user.user_id, roles)
    refresh_token, expires_at = create_refresh_token(user.user_id)
    db.add(
        RefreshToken(
            user_id=user.user_id,
            token_hash=token_hash(refresh_token),
            expires_at=expires_at,
        )
    )
    db.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in_seconds=settings.access_token_expire_minutes * 60,
        roles=roles,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        decoded = decode_token(payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    current_hash = token_hash(payload.refresh_token)
    token_row = db.query(RefreshToken).filter(RefreshToken.token_hash == current_hash).first()
    if not token_row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token not found")
    if token_row.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
    expires_at = token_row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(tz=timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

    user = db.get(User, token_row.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")

    token_row.revoked_at = datetime.now(tz=timezone.utc)
    roles = get_user_roles(db, user.user_id)
    new_access = create_access_token(user.user_id, roles)
    new_refresh, expires_at = create_refresh_token(user.user_id)
    db.add(RefreshToken(user_id=user.user_id, token_hash=token_hash(new_refresh), expires_at=expires_at))
    db.commit()

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in_seconds=settings.access_token_expire_minutes * 60,
        roles=roles,
    )


@router.post("/logout")
def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> dict[str, bool]:
    token_row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash(payload.refresh_token)).first()
    if token_row and token_row.revoked_at is None:
        token_row.revoked_at = datetime.now(tz=timezone.utc)
        db.commit()
    return {"success": True}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserOut:
    return _build_user_out(db, current_user)

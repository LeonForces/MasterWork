from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_roles
from app.models import Role, User, UserRole
from app.schemas import UserCreate, UserOut
from app.security import get_password_hash

router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _serialize_user(db: Session, user: User) -> UserOut:
    user_roles = db.query(UserRole).filter(UserRole.user_id == user.user_id).all()
    roles = [row.role_name for row in user_roles]
    return UserOut(user_id=user.user_id, username=user.username, roles=roles, is_active=user.is_active)


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> list[UserOut]:
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [_serialize_user(db, user) for user in users]


@router.post("", response_model=UserOut)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> UserOut:
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    requested_roles = set(payload.roles)
    if not requested_roles:
        requested_roles = {"viewer"}

    available_roles = {row.role_name for row in db.query(Role).all()}
    unknown = requested_roles - available_roles
    if unknown:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown roles: {sorted(unknown)}")

    user = User(username=payload.username, hashed_password=get_password_hash(payload.password), is_active=True)
    db.add(user)
    db.flush()

    for role in requested_roles:
        db.add(UserRole(user_id=user.user_id, role_name=role))

    db.commit()
    db.refresh(user)
    return _serialize_user(db, user)

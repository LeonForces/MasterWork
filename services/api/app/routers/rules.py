from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_roles
from app.models import Camera, Rule, User
from app.schemas import RuleCreate, RuleOut, RulePatch
from app.validation import validate_rule_params

router = APIRouter(prefix="/api/v1/rules", tags=["rules"])


@router.get("", response_model=list[RuleOut])
def list_rules(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "operator", "viewer")),
) -> list[Rule]:
    return db.query(Rule).order_by(Rule.created_at.desc()).all()


@router.post("", response_model=RuleOut)
def create_rule(
    payload: RuleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "operator")),
) -> Rule:
    camera = db.get(Camera, payload.camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    params_error = validate_rule_params(payload.rule_type, payload.params)
    if params_error:
        raise HTTPException(status_code=400, detail=params_error)
    rule = Rule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.patch("/{rule_id}", response_model=RuleOut)
def patch_rule(
    rule_id: str,
    payload: RulePatch,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "operator")),
) -> Rule:
    rule = db.get(Rule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    next_params = payload.params if payload.params is not None else rule.params
    params_error = validate_rule_params(rule.rule_type, next_params)
    if params_error:
        raise HTTPException(status_code=400, detail=params_error)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
def delete_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "operator")),
) -> Response:
    rule = db.get(Rule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
    return Response(status_code=204)

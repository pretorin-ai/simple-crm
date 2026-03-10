"""Router for audit log endpoints (admin-only)."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.database import get_db
from app.models.models import AuditLog, User
from app.schemas.schemas import AuditLogResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Audit"])


def create_audit_entry(
    db: Session,
    *,
    user_id: Optional[str],
    action: str,
    entity_type: str,
    entity_id: str,
    details: str = "",
):
    """Create an audit log entry."""
    from app.utils import generate_id

    entry = AuditLog(
        id=generate_id(),
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/audit-log", response_model=list[AuditLogResponse])
def get_audit_log(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get audit log entries. Admin only."""
    if current_user.role != "admin":
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Admin access required")
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    if action:
        query = query.filter(AuditLog.action == action)
    return query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

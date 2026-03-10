from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.database import get_db
from app.models.models import Compliance, User
from app.schemas.schemas import (
    Compliance as ComplianceSchema,
)
from app.schemas.schemas import (
    ComplianceCreate,
    CompliancePatch,
    ComplianceUpdate,
)
from app.utils import generate_id

router = APIRouter(prefix="/compliance", tags=["compliance"])


def _check_compliance_authorization(record: Compliance, current_user: User):
    """Only creator or admin can modify/delete a compliance record."""
    if record.created_by_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this compliance record",
        )


@router.get("", response_model=List[ComplianceSchema])
def get_compliance_records(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    compliance_status: str = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(Compliance)
    if compliance_status:
        query = query.filter(Compliance.status == compliance_status)
    return query.order_by(Compliance.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/expiring", response_model=List[ComplianceSchema])
def get_expiring_certifications(
    days_ahead: int = Query(default=90, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    cutoff = datetime.now(timezone.utc) + timedelta(days=days_ahead)
    now = datetime.now(timezone.utc)
    return (
        db.query(Compliance)
        .filter(
            Compliance.expiration_date.isnot(None),
            Compliance.expiration_date <= cutoff,
            Compliance.expiration_date >= now,
        )
        .order_by(Compliance.expiration_date)
        .all()
    )


@router.get("/{compliance_id}", response_model=ComplianceSchema)
def get_compliance(
    compliance_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    record = db.query(Compliance).filter(Compliance.id == compliance_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Compliance record not found"
        )
    return record


@router.post("", response_model=ComplianceSchema, status_code=status.HTTP_201_CREATED)
def create_compliance(
    compliance: ComplianceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    new_record = Compliance(
        id=generate_id(),
        certification_type=compliance.certification_type,
        issued_by=compliance.issued_by,
        issue_date=compliance.issue_date,
        expiration_date=compliance.expiration_date,
        status=compliance.status,
        notes=compliance.notes,
        created_by_user_id=current_user.id,
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record


@router.put("/{compliance_id}", response_model=ComplianceSchema)
def update_compliance(
    compliance_id: str,
    compliance_update: ComplianceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    record = db.query(Compliance).filter(Compliance.id == compliance_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Compliance record not found"
        )

    _check_compliance_authorization(record, current_user)

    record.certification_type = compliance_update.certification_type
    record.issued_by = compliance_update.issued_by
    record.issue_date = compliance_update.issue_date
    record.expiration_date = compliance_update.expiration_date
    record.status = compliance_update.status
    record.notes = compliance_update.notes

    db.commit()
    db.refresh(record)
    return record


@router.patch("/{compliance_id}", response_model=ComplianceSchema)
def patch_compliance(
    compliance_id: str,
    updates: CompliancePatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    record = db.query(Compliance).filter(Compliance.id == compliance_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Compliance record not found"
        )

    _check_compliance_authorization(record, current_user)

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)
    return record


@router.delete("/{compliance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_compliance(
    compliance_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    record = db.query(Compliance).filter(Compliance.id == compliance_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Compliance record not found"
        )

    _check_compliance_authorization(record, current_user)

    db.delete(record)
    db.commit()
    return None

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.database import get_db
from app.models.models import CaptureNote, Opportunity, User
from app.schemas.schemas import (
    CaptureNote as CaptureNoteSchema,
)
from app.schemas.schemas import (
    CaptureNoteUpdate,
)
from app.utils import generate_id

router = APIRouter(prefix="/opportunities", tags=["capture-notes"])

VALID_SECTIONS = [
    "customer_intel",
    "incumbent",
    "competitors",
    "partners",
    "risks",
    "strategy",
]


@router.get(
    "/{opportunity_id}/capture-notes",
    response_model=List[CaptureNoteSchema],
)
def get_capture_notes(
    opportunity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    opp = (
        db.query(Opportunity)
        .filter(Opportunity.id == opportunity_id, Opportunity.deleted_at.is_(None))
        .first()
    )
    if not opp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found",
        )
    return db.query(CaptureNote).filter(CaptureNote.opportunity_id == opportunity_id).all()


@router.put(
    "/{opportunity_id}/capture-notes/{section}",
    response_model=CaptureNoteSchema,
)
def upsert_capture_note(
    opportunity_id: str,
    section: str,
    update: CaptureNoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create or update a capture note section."""
    if section not in VALID_SECTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid section. Must be one of: {VALID_SECTIONS}",
        )

    opp = (
        db.query(Opportunity)
        .filter(Opportunity.id == opportunity_id, Opportunity.deleted_at.is_(None))
        .first()
    )
    if not opp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found",
        )

    note = (
        db.query(CaptureNote)
        .filter(
            CaptureNote.opportunity_id == opportunity_id,
            CaptureNote.section == section,
        )
        .first()
    )

    if note:
        note.content = update.content
    else:
        note = CaptureNote(
            id=generate_id(),
            opportunity_id=opportunity_id,
            section=section,
            content=update.content,
        )
        db.add(note)

    db.commit()
    db.refresh(note)
    return note

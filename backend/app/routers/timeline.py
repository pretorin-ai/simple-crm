from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.database import get_db
from app.models.models import Opportunity, OpportunityEvent, User
from app.schemas.schemas import (
    OpportunityEvent as EventSchema,
)
from app.schemas.schemas import (
    OpportunityEventCreate,
    OpportunityEventUpdate,
)
from app.utils import generate_id

router = APIRouter(prefix="/opportunities", tags=["timeline"])


@router.get(
    "/{opportunity_id}/timeline",
    response_model=List[EventSchema],
)
def get_timeline(
    opportunity_id: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
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
    return (
        db.query(OpportunityEvent)
        .filter(OpportunityEvent.opportunity_id == opportunity_id)
        .order_by(OpportunityEvent.date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post(
    "/{opportunity_id}/timeline",
    response_model=EventSchema,
    status_code=status.HTTP_201_CREATED,
)
def create_event(
    opportunity_id: str,
    event: OpportunityEventCreate,
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

    new_event = OpportunityEvent(
        id=generate_id(),
        opportunity_id=opportunity_id,
        date=event.date,
        event_type=event.event_type,
        description=event.description,
        created_by_user_id=current_user.id,
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event


@router.patch(
    "/{opportunity_id}/timeline/{event_id}",
    response_model=EventSchema,
)
def update_event(
    opportunity_id: str,
    event_id: str,
    updates: OpportunityEventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    event = (
        db.query(OpportunityEvent)
        .filter(
            OpportunityEvent.id == event_id,
            OpportunityEvent.opportunity_id == opportunity_id,
        )
        .first()
    )
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    # Only creator or admin can update
    if event.created_by_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this event",
        )

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)
    return event


@router.delete(
    "/{opportunity_id}/timeline/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_event(
    opportunity_id: str,
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    event = (
        db.query(OpportunityEvent)
        .filter(
            OpportunityEvent.id == event_id,
            OpportunityEvent.opportunity_id == opportunity_id,
        )
        .first()
    )
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    # Only creator or admin can delete
    if event.created_by_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this event",
        )

    db.delete(event)
    db.commit()
    return None

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta, UTC
from app.database import get_db
from app.models.models import Contact, User
from app.schemas.schemas import Contact as ContactSchema
from app.auth import get_current_user

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("/follow-ups/due", response_model=List[ContactSchema])
def get_due_follow_ups(
    days_ahead: int = Query(default=7, description="Number of days to look ahead"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get contacts with follow-ups due within the specified number of days for the current user"""
    today = datetime.now(UTC).date()
    future_date = today + timedelta(days=days_ahead)

    contacts = db.query(Contact).filter(
        Contact.assigned_user_id == current_user.id,
        Contact.follow_up_date.isnot(None),
        Contact.follow_up_date <= datetime.combine(future_date, datetime.min.time())
    ).order_by(Contact.follow_up_date.asc()).all()

    return [
        {
            **contact.__dict__,
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "contact_type": contact.contact_type,
            "needs_follow_up": contact.needs_follow_up,
            "follow_up_date": contact.follow_up_date,
            "created_at": contact.created_at,
            "last_contacted_at": contact.last_contacted_at
        }
        for contact in contacts
    ]


@router.get("/follow-ups/overdue", response_model=List[ContactSchema])
def get_overdue_follow_ups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get contacts with overdue follow-ups for the current user"""
    today = datetime.now(UTC).date()

    contacts = db.query(Contact).filter(
        Contact.assigned_user_id == current_user.id,
        Contact.follow_up_date.isnot(None),
        Contact.follow_up_date < datetime.combine(today, datetime.min.time())
    ).order_by(Contact.follow_up_date.asc()).all()

    return [
        {
            **contact.__dict__,
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "contact_type": contact.contact_type,
            "needs_follow_up": contact.needs_follow_up,
            "follow_up_date": contact.follow_up_date,
            "created_at": contact.created_at,
            "last_contacted_at": contact.last_contacted_at
        }
        for contact in contacts
    ]

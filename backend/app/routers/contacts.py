from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.models import Contact, User
from app.schemas.schemas import Contact as ContactSchema, ContactCreate, ContactUpdate
from app.auth import get_current_user, get_current_user_or_api_key
from app.seed_data import generate_id

security = HTTPBearer()

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=List[ContactSchema])
def get_contacts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all contacts for the current user"""
    contacts = db.query(Contact).filter(Contact.assigned_user_id == current_user.id).all()
    # Convert to schema format
    return [
        {
            **contact.__dict__,
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "contact_type": contact.contact_type,
            "needs_follow_up": contact.needs_follow_up,
            "created_at": contact.created_at,
            "last_contacted_at": contact.last_contacted_at,
            "assigned_user_id": contact.assigned_user_id,
            "assigned_user": contact.assigned_user
        }
        for contact in contacts
    ]


@router.get("/{contact_id}", response_model=ContactSchema)
def get_contact(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific contact"""
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.assigned_user_id == current_user.id
    ).first()
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )

    return {
        **contact.__dict__,
        "first_name": contact.first_name,
        "last_name": contact.last_name,
        "contact_type": contact.contact_type,
        "needs_follow_up": contact.needs_follow_up,
        "created_at": contact.created_at,
        "last_contacted_at": contact.last_contacted_at,
        "assigned_user_id": contact.assigned_user_id,
        "assigned_user": contact.assigned_user
    }


@router.post("", response_model=ContactSchema, status_code=status.HTTP_201_CREATED)
def create_contact(
    contact: ContactCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Create a new contact. Accepts both JWT tokens and API keys."""
    # Use provided assigned_user_id or default to current user
    assigned_user_id = contact.assigned_user_id if contact.assigned_user_id else current_user.id

    # Detect if request came from API key (starts with "crm_")
    is_api_request = credentials.credentials.startswith("crm_")

    new_contact = Contact(
        id=generate_id(),
        first_name=contact.first_name,
        last_name=contact.last_name,
        email=contact.email,
        phone=contact.phone,
        organization=contact.organization,
        contact_type=contact.contact_type,
        status=contact.status,
        needs_follow_up=contact.needs_follow_up,
        follow_up_date=contact.follow_up_date,
        notes=contact.notes,
        assigned_user_id=assigned_user_id,
        created_via="api" if is_api_request else "user",
        is_claimed=False if is_api_request else True
    )

    db.add(new_contact)
    db.commit()
    db.refresh(new_contact)

    return {
        **new_contact.__dict__,
        "first_name": new_contact.first_name,
        "last_name": new_contact.last_name,
        "contact_type": new_contact.contact_type,
        "needs_follow_up": new_contact.needs_follow_up,
        "created_at": new_contact.created_at,
        "last_contacted_at": new_contact.last_contacted_at,
        "assigned_user_id": new_contact.assigned_user_id,
        "assigned_user": new_contact.assigned_user
    }


@router.put("/{contact_id}", response_model=ContactSchema)
def update_contact(
    contact_id: str,
    contact_update: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a contact"""
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.assigned_user_id == current_user.id
    ).first()
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )

    # Check if assigned_user_id is changing to a different user
    is_reassignment = (
        contact_update.assigned_user_id != current_user.id and
        contact_update.assigned_user_id != contact.assigned_user_id
    )

    # Update fields
    contact.first_name = contact_update.first_name
    contact.last_name = contact_update.last_name
    contact.email = contact_update.email
    contact.phone = contact_update.phone
    contact.organization = contact_update.organization
    contact.contact_type = contact_update.contact_type
    contact.status = contact_update.status
    contact.needs_follow_up = contact_update.needs_follow_up
    contact.follow_up_date = contact_update.follow_up_date
    contact.notes = contact_update.notes
    contact.assigned_user_id = contact_update.assigned_user_id
    if contact_update.last_contacted_at:
        contact.last_contacted_at = contact_update.last_contacted_at

    # If reassigning to another user, set pending acceptance
    if is_reassignment:
        contact.pending_acceptance = True
        contact.reassigned_by_user_id = current_user.id

    db.commit()
    db.refresh(contact)

    return {
        **contact.__dict__,
        "first_name": contact.first_name,
        "last_name": contact.last_name,
        "contact_type": contact.contact_type,
        "needs_follow_up": contact.needs_follow_up,
        "created_at": contact.created_at,
        "last_contacted_at": contact.last_contacted_at,
        "assigned_user_id": contact.assigned_user_id,
        "assigned_user": contact.assigned_user
    }


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a contact"""
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.assigned_user_id == current_user.id
    ).first()
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )

    db.delete(contact)
    db.commit()
    return None

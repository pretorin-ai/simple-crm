from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_active_user
from app.database import get_db
from app.models.models import Contact, User
from app.schemas.schemas import (
    Contact as ContactSchema,
)
from app.schemas.schemas import (
    ContactCreate,
    ContactPatch,
    ContactUpdate,
)
from app.utils import generate_id

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=List[ContactSchema])
def get_contacts(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get all contacts for the current user"""
    return (
        db.query(Contact)
        .options(joinedload(Contact.assigned_user))
        .filter(Contact.assigned_user_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{contact_id}", response_model=ContactSchema)
def get_contact(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a specific contact"""
    contact = (
        db.query(Contact)
        .options(joinedload(Contact.assigned_user))
        .filter(Contact.id == contact_id, Contact.assigned_user_id == current_user.id)
        .first()
    )
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact


@router.post("", response_model=ContactSchema, status_code=status.HTTP_201_CREATED)
def create_contact(
    contact: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new contact"""
    # Use provided assigned_user_id or default to current user
    assigned_user_id = contact.assigned_user_id if contact.assigned_user_id else current_user.id

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
    )

    db.add(new_contact)
    db.commit()
    db.refresh(new_contact)
    return new_contact


@router.put("/{contact_id}", response_model=ContactSchema)
def update_contact(
    contact_id: str,
    contact_update: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a contact"""
    contact = (
        db.query(Contact)
        .filter(Contact.id == contact_id, Contact.assigned_user_id == current_user.id)
        .first()
    )
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

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

    db.commit()
    db.refresh(contact)
    return contact


@router.patch("/{contact_id}", response_model=ContactSchema)
def patch_contact(
    contact_id: str,
    updates: ContactPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Partially update a contact"""
    contact = (
        db.query(Contact)
        .filter(Contact.id == contact_id, Contact.assigned_user_id == current_user.id)
        .first()
    )
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)

    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a contact"""
    contact = (
        db.query(Contact)
        .filter(Contact.id == contact_id, Contact.assigned_user_id == current_user.id)
        .first()
    )
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    from app.routers.audit import create_audit_entry

    db.delete(contact)
    db.commit()

    create_audit_entry(
        db,
        user_id=current_user.id,
        action="delete",
        entity_type="contact",
        entity_id=contact_id,
        details=f"Deleted contact: {contact.first_name} {contact.last_name}",
    )
    return None

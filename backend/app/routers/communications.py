from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.models import Communication, Contact, User
from app.schemas.schemas import Communication as CommunicationSchema, CommunicationCreate
from app.auth import get_current_user
from app.seed_data import generate_id

router = APIRouter(prefix="/communications", tags=["communications"])


@router.get("", response_model=List[CommunicationSchema])
def get_communications(
    contact_id: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all communications for the current user's contacts, optionally filtered by contact_id"""
    query = db.query(Communication).join(Contact).filter(Contact.assigned_user_id == current_user.id)
    if contact_id:
        query = query.filter(Communication.contact_id == contact_id)

    communications = query.all()
    return [
        {
            **comm.__dict__,
            "contact_id": comm.contact_id,
            "created_at": comm.created_at
        }
        for comm in communications
    ]


@router.get("/{communication_id}", response_model=CommunicationSchema)
def get_communication(
    communication_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific communication"""
    communication = db.query(Communication).join(Contact).filter(
        Communication.id == communication_id,
        Contact.assigned_user_id == current_user.id
    ).first()
    if not communication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Communication not found"
        )

    return {
        **communication.__dict__,
        "contact_id": communication.contact_id,
        "created_at": communication.created_at
    }


@router.post("", response_model=CommunicationSchema, status_code=status.HTTP_201_CREATED)
def create_communication(
    communication: CommunicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new communication"""
    # Verify contact exists and belongs to current user
    contact = db.query(Contact).filter(
        Contact.id == communication.contact_id,
        Contact.assigned_user_id == current_user.id
    ).first()
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )

    new_communication = Communication(
        id=generate_id(),
        contact_id=communication.contact_id,
        date=communication.date,
        type=communication.type,
        notes=communication.notes
    )

    db.add(new_communication)

    # Update last_contacted_at on the contact
    contact.last_contacted_at = communication.date

    db.commit()
    db.refresh(new_communication)

    return {
        **new_communication.__dict__,
        "contact_id": new_communication.contact_id,
        "created_at": new_communication.created_at
    }


@router.delete("/{communication_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_communication(
    communication_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a communication"""
    communication = db.query(Communication).join(Contact).filter(
        Communication.id == communication_id,
        Contact.assigned_user_id == current_user.id
    ).first()
    if not communication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Communication not found"
        )

    db.delete(communication)
    db.commit()
    return None

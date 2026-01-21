from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.models import Contact, Contract, User
from app.schemas.schemas import (
    Contact as ContactSchema,
    Contract as ContractSchema,
    QueueCounts,
    ClaimRequest
)
from app.auth import get_current_user

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("/counts", response_model=QueueCounts)
def get_queue_counts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get counts for queue badges"""
    unclaimed_contacts = db.query(Contact).filter(
        Contact.is_claimed == False,
        Contact.created_via == "api"
    ).count()

    unclaimed_contracts = db.query(Contract).filter(
        Contract.is_claimed == False,
        Contract.created_via == "api"
    ).count()

    pending_reassignments = db.query(Contact).filter(
        Contact.assigned_user_id == current_user.id,
        Contact.pending_acceptance == True
    ).count()

    return QueueCounts(
        unclaimed_contacts=unclaimed_contacts,
        unclaimed_contracts=unclaimed_contracts,
        pending_reassignments=pending_reassignments
    )


@router.get("/contacts/unclaimed", response_model=List[ContactSchema])
def get_unclaimed_contacts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List API-created contacts not yet claimed"""
    contacts = db.query(Contact).filter(
        Contact.is_claimed == False,
        Contact.created_via == "api"
    ).all()

    return [
        {
            **contact.__dict__,
            "assigned_user": contact.assigned_user,
            "reassigned_by_user": contact.reassigned_by_user
        }
        for contact in contacts
    ]


@router.get("/contracts/unclaimed", response_model=List[ContractSchema])
def get_unclaimed_contracts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List API-created contracts not yet claimed"""
    contracts = db.query(Contract).filter(
        Contract.is_claimed == False,
        Contract.created_via == "api"
    ).all()

    return [
        {
            **contract.__dict__,
            "assigned_contact_ids": [c.id for c in contract.assigned_contacts]
        }
        for contract in contracts
    ]


@router.post("/contacts/{contact_id}/claim", response_model=ContactSchema)
def claim_contact(
    contact_id: str,
    claim_request: ClaimRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Claim a contact (assign to self or specified user)"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )

    if contact.is_claimed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contact is already claimed"
        )

    # Assign to specified user or current user
    assigned_user_id = current_user.id
    if claim_request and claim_request.assigned_user_id:
        # Verify the target user exists
        target_user = db.query(User).filter(User.id == claim_request.assigned_user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target user not found"
            )
        assigned_user_id = claim_request.assigned_user_id

    contact.assigned_user_id = assigned_user_id
    contact.is_claimed = True

    db.commit()
    db.refresh(contact)

    return {
        **contact.__dict__,
        "assigned_user": contact.assigned_user,
        "reassigned_by_user": contact.reassigned_by_user
    }


@router.post("/contracts/{contract_id}/claim", response_model=ContractSchema)
def claim_contract(
    contract_id: str,
    claim_request: ClaimRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Claim a contract"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )

    if contract.is_claimed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contract is already claimed"
        )

    # Assign to specified user or current user
    claimed_by_user_id = current_user.id
    if claim_request and claim_request.assigned_user_id:
        # Verify the target user exists
        target_user = db.query(User).filter(User.id == claim_request.assigned_user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target user not found"
            )
        claimed_by_user_id = claim_request.assigned_user_id

    contract.claimed_by_user_id = claimed_by_user_id
    contract.is_claimed = True

    db.commit()
    db.refresh(contract)

    return {
        **contract.__dict__,
        "assigned_contact_ids": [c.id for c in contract.assigned_contacts]
    }


@router.get("/contacts/pending-acceptance", response_model=List[ContactSchema])
def get_pending_acceptance_contacts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List contacts pending current user's acceptance"""
    contacts = db.query(Contact).filter(
        Contact.assigned_user_id == current_user.id,
        Contact.pending_acceptance == True
    ).all()

    return [
        {
            **contact.__dict__,
            "assigned_user": contact.assigned_user,
            "reassigned_by_user": contact.reassigned_by_user
        }
        for contact in contacts
    ]


@router.post("/contacts/{contact_id}/accept", response_model=ContactSchema)
def accept_contact_reassignment(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Accept a reassigned contact"""
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.assigned_user_id == current_user.id,
        Contact.pending_acceptance == True
    ).first()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found or not pending your acceptance"
        )

    contact.pending_acceptance = False
    contact.reassigned_by_user_id = None

    db.commit()
    db.refresh(contact)

    return {
        **contact.__dict__,
        "assigned_user": contact.assigned_user,
        "reassigned_by_user": contact.reassigned_by_user
    }


@router.post("/contacts/{contact_id}/reject", response_model=ContactSchema)
def reject_contact_reassignment(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject and return contact to previous owner"""
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.assigned_user_id == current_user.id,
        Contact.pending_acceptance == True
    ).first()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found or not pending your acceptance"
        )

    # Return to the user who reassigned it
    if contact.reassigned_by_user_id:
        contact.assigned_user_id = contact.reassigned_by_user_id

    contact.pending_acceptance = False
    contact.reassigned_by_user_id = None

    db.commit()
    db.refresh(contact)

    return {
        **contact.__dict__,
        "assigned_user": contact.assigned_user,
        "reassigned_by_user": contact.reassigned_by_user
    }

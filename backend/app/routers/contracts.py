from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import delete
from typing import List
from datetime import datetime
from app.database import get_db
from app.models.models import Contract, Contact, User, contract_acknowledgments
from app.schemas.schemas import (
    Contract as ContractSchema,
    ContractCreate,
    ContractUpdate,
    SAMGovImportRequest,
    SAMGovImportResponse
)
from app.auth import get_current_user, get_current_user_or_api_key
from app.seed_data import generate_id

router = APIRouter(prefix="/contracts", tags=["contracts"])


def build_contract_response(contract: Contract, current_user_id: str) -> dict:
    """Build contract response dict with acknowledgment data"""
    acknowledged_user_ids = [user.id for user in contract.acknowledged_by_users]
    return {
        **contract.__dict__,
        "submission_link": contract.submission_link,
        "created_at": contract.created_at,
        "assigned_contact_ids": [contact.id for contact in contract.assigned_contacts],
        "acknowledged_by_current_user": current_user_id in acknowledged_user_ids,
        "acknowledged_by_user_ids": acknowledged_user_ids
    }


@router.get("", response_model=List[ContractSchema])
def get_contracts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get all contracts - contracts are shared across all users"""
    contracts = db.query(Contract).all()
    return [
        {
            **contract.__dict__,
            "submission_link": contract.submission_link,
            "created_at": contract.created_at,
            "assigned_contact_ids": [contact.id for contact in contract.assigned_contacts]
        }
        for contract in contracts
    ]


@router.get("/{contract_id}", response_model=ContractSchema)
def get_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific contract - contracts are shared across all users"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )

    return {
        **contract.__dict__,
        "submission_link": contract.submission_link,
        "created_at": contract.created_at,
        "assigned_contact_ids": [contact.id for contact in contract.assigned_contacts]
    }


@router.post("", response_model=ContractSchema, status_code=status.HTTP_201_CREATED)
def create_contract(
    contract: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new contract"""
    new_contract = Contract(
        id=generate_id(),
        title=contract.title,
        description=contract.description,
        source=contract.source,
        deadline=contract.deadline,
        status=contract.status,
        submission_link=contract.submission_link,
        notes=contract.notes
    )

    # Add assigned contacts - can assign any contacts
    if contract.assigned_contact_ids:
        contacts = db.query(Contact).filter(
            Contact.id.in_(contract.assigned_contact_ids)
        ).all()
        new_contract.assigned_contacts = contacts

    db.add(new_contract)
    db.commit()
    db.refresh(new_contract)

    return {
        **new_contract.__dict__,
        "submission_link": new_contract.submission_link,
        "created_at": new_contract.created_at,
        "assigned_contact_ids": [contact.id for contact in new_contract.assigned_contacts]
    }


@router.put("/{contract_id}", response_model=ContractSchema)
def update_contract(
    contract_id: str,
    contract_update: ContractUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a contract - contracts are shared across all users"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )

    # Update fields
    contract.title = contract_update.title
    contract.description = contract_update.description
    contract.source = contract_update.source
    contract.deadline = contract_update.deadline
    contract.status = contract_update.status
    contract.submission_link = contract_update.submission_link
    contract.notes = contract_update.notes

    # Update assigned contacts - can assign any contacts
    if contract_update.assigned_contact_ids is not None:
        contacts = db.query(Contact).filter(
            Contact.id.in_(contract_update.assigned_contact_ids)
        ).all()
        contract.assigned_contacts = contacts

    db.commit()
    db.refresh(contract)

    return {
        **contract.__dict__,
        "submission_link": contract.submission_link,
        "created_at": contract.created_at,
        "assigned_contact_ids": [contact.id for contact in contract.assigned_contacts]
    }


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a contract - contracts are shared across all users"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )

    db.delete(contract)
    db.commit()
    return None


@router.post("/import/samgov", response_model=SAMGovImportResponse)
def import_samgov_opportunities(
    import_request: SAMGovImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """
    Import contract opportunities from SAM.gov

    This endpoint accepts opportunities scraped from SAM.gov and creates:
    - Contract records for each opportunity
    - Contact records from point-of-contact information (if auto_create_contacts is True)

    Duplicate opportunities (by noticeId) are skipped automatically.
    """
    contracts_created = 0
    contracts_skipped = 0
    contacts_created = 0
    errors = []

    for opp in import_request.opportunities:
        try:
            # Check if contract already exists by noticeId (stored in notes)
            existing_contract = db.query(Contract).filter(
                Contract.notes.contains(f"SAM.gov Notice ID: {opp.noticeId}")
            ).first()

            if existing_contract:
                contracts_skipped += 1
                continue

            # Parse deadline
            deadline = None
            if opp.responseDeadLine:
                try:
                    deadline = datetime.fromisoformat(opp.responseDeadLine.replace('Z', '+00:00'))
                except:
                    # Try alternate format
                    try:
                        deadline = datetime.strptime(opp.responseDeadLine[:10], "%Y-%m-%d")
                    except:
                        errors.append(f"Could not parse deadline for {opp.title}")
                        continue

            if not deadline:
                errors.append(f"No deadline provided for {opp.title}")
                continue

            # Create contacts from point of contact if requested
            contact_ids = []
            if import_request.auto_create_contacts and opp.pointOfContact:
                for poc in opp.pointOfContact:
                    if poc.email and poc.fullName:
                        # Check if contact already exists
                        existing_contact = db.query(Contact).filter(
                            Contact.email == poc.email
                        ).first()

                        if existing_contact:
                            contact_ids.append(existing_contact.id)
                        else:
                            # Parse name
                            name_parts = poc.fullName.strip().split()
                            first_name = name_parts[0] if name_parts else "Unknown"
                            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

                            new_contact = Contact(
                                id=generate_id(),
                                first_name=first_name,
                                last_name=last_name,
                                email=poc.email,
                                phone=poc.phone or "",
                                organization=opp.title[:100] if opp.title else "SAM.gov Contact",
                                contact_type="government",
                                status="warm",
                                needs_follow_up=True,
                                notes=f"Auto-imported from SAM.gov opportunity: {opp.title}",
                                assigned_user_id=current_user.id,
                                created_via="api",
                                is_claimed=False
                            )
                            db.add(new_contact)
                            db.flush()
                            contact_ids.append(new_contact.id)
                            contacts_created += 1

            # Build notes with SAM.gov metadata
            notes_parts = [f"SAM.gov Notice ID: {opp.noticeId}"]
            if opp.solicitationNumber:
                notes_parts.append(f"Solicitation #: {opp.solicitationNumber}")
            if opp.naicsCode:
                notes_parts.append(f"NAICS Code: {opp.naicsCode}")
            if opp.notes:
                notes_parts.append(opp.notes)

            # Create contract
            # Use the SAM.gov UI link as the description so users can easily access the opportunity
            new_contract = Contract(
                id=generate_id(),
                title=opp.title[:200],  # Truncate if too long
                description=opp.uiLink or "",
                source=opp.source,
                deadline=deadline,
                status="prospective",  # Default to prospective
                submission_link=opp.uiLink,
                notes="\n".join(notes_parts),
                created_via="api",
                is_claimed=False
            )

            # Assign contacts
            if contact_ids:
                contacts = db.query(Contact).filter(Contact.id.in_(contact_ids)).all()
                new_contract.assigned_contacts = contacts

            db.add(new_contract)
            contracts_created += 1

        except Exception as e:
            errors.append(f"Error importing {opp.title}: {str(e)}")
            continue

    # Commit all changes
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save imports: {str(e)}"
        )

    return SAMGovImportResponse(
        contracts_created=contracts_created,
        contracts_skipped=contracts_skipped,
        contacts_created=contacts_created,
        errors=errors
    )

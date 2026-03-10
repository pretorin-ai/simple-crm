from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_active_user, get_current_user_or_api_key
from app.database import get_db
from app.models.models import Contact, Contract, User
from app.schemas.schemas import (
    Contract as ContractSchema,
)
from app.schemas.schemas import (
    ContractCreate,
    ContractPatch,
    ContractUpdate,
    SAMGovImportRequest,
    SAMGovImportResponse,
)
from app.services.import_service import import_opportunities
from app.utils import generate_id

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.get("", response_model=List[ContractSchema])
def get_contracts(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_api_key),
):
    """Get all contracts - contracts are shared across all users"""
    return (
        db.query(Contract)
        .options(selectinload(Contract.assigned_contacts))
        .order_by(Contract.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{contract_id}", response_model=ContractSchema)
def get_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a specific contract"""
    contract = (
        db.query(Contract)
        .options(selectinload(Contract.assigned_contacts))
        .filter(Contract.id == contract_id)
        .first()
    )
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    return contract


def _check_contract_authorization(contract: Contract, current_user: User):
    """Check if user is authorized to modify/delete a contract."""
    if contract.created_by_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this contract",
        )


def _resolve_owned_contacts(contact_ids: List[str], current_user: User, db: Session) -> list:
    """Resolve contact IDs, filtering to only contacts owned by the current user."""
    if not contact_ids:
        return []
    return (
        db.query(Contact)
        .filter(Contact.id.in_(contact_ids), Contact.assigned_user_id == current_user.id)
        .all()
    )


@router.post("", response_model=ContractSchema, status_code=status.HTTP_201_CREATED)
def create_contract(
    contract: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
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
        notes=contract.notes,
        created_by_user_id=current_user.id,
    )

    # Add assigned contacts (only those owned by current user)
    new_contract.assigned_contacts = _resolve_owned_contacts(
        contract.assigned_contact_ids, current_user, db
    )

    db.add(new_contract)
    db.commit()
    db.refresh(new_contract)
    return new_contract


@router.put("/{contract_id}", response_model=ContractSchema)
def update_contract(
    contract_id: str,
    contract_update: ContractUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a contract - only creator or admin can modify"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

    _check_contract_authorization(contract, current_user)

    # Update fields
    contract.title = contract_update.title
    contract.description = contract_update.description
    contract.source = contract_update.source
    contract.deadline = contract_update.deadline
    contract.status = contract_update.status
    contract.submission_link = contract_update.submission_link
    contract.notes = contract_update.notes

    # Update assigned contacts (only those owned by current user)
    if contract_update.assigned_contact_ids is not None:
        contract.assigned_contacts = _resolve_owned_contacts(
            contract_update.assigned_contact_ids, current_user, db
        )

    db.commit()
    db.refresh(contract)
    return contract


@router.patch("/{contract_id}", response_model=ContractSchema)
def patch_contract(
    contract_id: str,
    updates: ContractPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Partially update a contract"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

    _check_contract_authorization(contract, current_user)

    update_data = updates.model_dump(exclude_unset=True)

    # Handle assigned_contact_ids separately (relationship, not a column)
    if "assigned_contact_ids" in update_data:
        contact_ids = update_data.pop("assigned_contact_ids")
        contract.assigned_contacts = _resolve_owned_contacts(contact_ids, current_user, db)

    for field, value in update_data.items():
        setattr(contract, field, value)

    db.commit()
    db.refresh(contract)
    return contract


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a contract - only creator or admin can delete"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

    _check_contract_authorization(contract, current_user)

    from app.routers.audit import create_audit_entry

    db.delete(contract)
    db.commit()

    create_audit_entry(
        db,
        user_id=current_user.id,
        action="delete",
        entity_type="contract",
        entity_id=contract_id,
        details=f"Deleted contract: {contract.title}",
    )
    return None


@router.post("/import/samgov", response_model=SAMGovImportResponse)
def import_samgov_opportunities(
    import_request: SAMGovImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_api_key),
):
    """
    Import contract opportunities from SAM.gov

    This endpoint accepts opportunities scraped from SAM.gov and creates:
    - Contract records for each opportunity
    - Contact records from point-of-contact information (if auto_create_contacts is True)

    Duplicate opportunities (by noticeId) are skipped automatically.
    Uses savepoints so individual failures don't roll back the entire batch.
    """
    # Convert Pydantic models to dicts for the shared import service
    opps_as_dicts = [opp.model_dump() for opp in import_request.opportunities]
    result = import_opportunities(
        opportunities=opps_as_dicts,
        auto_create_contacts=import_request.auto_create_contacts,
        current_user=current_user,
        db=db,
    )
    return SAMGovImportResponse(**result)

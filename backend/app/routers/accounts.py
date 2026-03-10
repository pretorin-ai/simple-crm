# Authorization model: All authenticated users can read all accounts.
# This is intentional — Pretorin CRM is a shared team workspace where every
# user is created by an admin. Write operations (create/update/delete) are
# restricted to the creator or an admin.
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.database import get_db
from app.models.models import Account, User
from app.schemas.schemas import (
    Account as AccountSchema,
)
from app.schemas.schemas import (
    AccountCreate,
    AccountPatch,
    AccountUpdate,
)
from app.utils import generate_id

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _check_account_authorization(account: Account, current_user: User):
    """Only creator or admin can modify/delete an account."""
    if account.created_by_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this account",
        )


@router.get("", response_model=List[AccountSchema])
def get_accounts(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    account_type: str = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(Account)
    if account_type:
        query = query.filter(Account.account_type == account_type)
    return query.order_by(Account.name).offset(skip).limit(limit).all()


@router.get("/{account_id}", response_model=AccountSchema)
def get_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account


@router.post("", response_model=AccountSchema, status_code=status.HTTP_201_CREATED)
def create_account(
    account: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    new_account = Account(
        id=generate_id(),
        name=account.name,
        account_type=account.account_type,
        parent_agency=account.parent_agency,
        office=account.office,
        location=account.location,
        website=account.website,
        notes=account.notes,
        created_by_user_id=current_user.id,
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    return new_account


@router.put("/{account_id}", response_model=AccountSchema)
def update_account(
    account_id: str,
    account_update: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    _check_account_authorization(account, current_user)

    account.name = account_update.name
    account.account_type = account_update.account_type
    account.parent_agency = account_update.parent_agency
    account.office = account_update.office
    account.location = account_update.location
    account.website = account_update.website
    account.notes = account_update.notes

    db.commit()
    db.refresh(account)
    return account


@router.patch("/{account_id}", response_model=AccountSchema)
def patch_account(
    account_id: str,
    updates: AccountPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    _check_account_authorization(account, current_user)

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)

    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    _check_account_authorization(account, current_user)

    from app.routers.audit import create_audit_entry

    db.delete(account)
    db.commit()

    create_audit_entry(
        db,
        user_id=current_user.id,
        action="delete",
        entity_type="account",
        entity_id=account_id,
        details=f"Deleted account: {account.name}",
    )
    return None

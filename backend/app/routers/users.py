# Authorization model: All authenticated users can list users (names, roles).
# This is intentional — the user list is needed for contact/opportunity
# assignment. User creation/mutation is admin-only. No sensitive fields
# (password hashes, API keys) are exposed in the response schema.
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import (
    generate_api_key,
    get_current_active_user,
    get_current_admin_user,
    get_password_hash,
    hash_api_key,
    validate_password,
)
from app.database import get_db
from app.models.models import User
from app.schemas.schemas import User as UserSchema
from app.schemas.schemas import UserCreateByAdmin, UserUpdate
from app.utils import generate_id

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=List[UserSchema])
def get_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get all users - available to all authenticated users"""
    return db.query(User).order_by(User.name).offset(skip).limit(limit).all()


@router.get("/{user_id}", response_model=UserSchema)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get specific user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("", response_model=UserSchema)
def create_user(
    user_create: UserCreateByAdmin,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Create new user - admin only"""
    validate_password(user_create.password)

    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_create.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create user
    new_user = User(
        id=generate_id(),
        email=user_create.email,
        name=user_create.name,
        hashed_password=get_password_hash(user_create.password),
        role=user_create.role,
        is_active=True,
        created_by=current_user.id,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.put("/{user_id}", response_model=UserSchema)
def update_user(
    user_id: str,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Update user - admin only"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Update fields if provided
    if user_update.name is not None:
        user.name = user_update.name

    if user_update.email is not None:
        # Check if new email is already in use
        existing = (
            db.query(User).filter(User.email == user_update.email, User.id != user_id).first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use"
            )
        user.email = user_update.email

    if user_update.role is not None:
        user.role = user_update.role

    if user_update.is_active is not None:
        user.is_active = user_update.is_active

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Delete user - admin only. Cannot delete yourself."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Check if user has assigned contacts
    if user.assigned_contacts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot delete user with {len(user.assigned_contacts)}"
                " assigned contacts. Reassign them first."
            ),
        )

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}


@router.post("/me/api-key/generate")
def generate_user_api_key(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Generate or regenerate API key for current user"""
    # Generate new API key
    new_api_key = generate_api_key()

    # Store only the hash and a prefix for display
    current_user.api_key_hash = hash_api_key(new_api_key)
    current_user.api_key_prefix = new_api_key[:12] + "..."
    db.commit()

    return {
        "api_key": new_api_key,
        "message": "API key generated successfully. Store it securely - it won't be shown again.",
    }


@router.delete("/me/api-key")
def revoke_user_api_key(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Revoke API key for current user"""
    if not current_user.api_key_hash:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No API key found")

    current_user.api_key_hash = None
    current_user.api_key_prefix = None
    db.commit()

    return {"message": "API key revoked successfully"}


@router.get("/me/api-key/status")
def get_api_key_status(current_user: User = Depends(get_current_active_user)):
    """Check if current user has an API key (doesn't return the actual key)"""
    return {
        "has_api_key": current_user.api_key_hash is not None,
        "api_key_prefix": current_user.api_key_prefix,
    }

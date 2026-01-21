from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.models import User
from app.schemas.schemas import (
    User as UserSchema,
    UserCreateByAdmin,
    UserUpdate
)
from app.auth import (
    get_current_active_user,
    get_current_admin_user,
    generate_api_key
)
from app.seed_data import generate_id

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=List[UserSchema])
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all users - available to all authenticated users"""
    users = db.query(User).all()
    return users


@router.get("/{user_id}", response_model=UserSchema)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get specific user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.post("", response_model=UserSchema)
def create_user(
    user_create: UserCreateByAdmin,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Pre-provision a new user - admin only.

    Creates a user account that will be linked when the user first signs in
    via Google OAuth. The user's email must match their Google Workspace email.
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_create.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Validate role
    if user_create.role not in ["admin", "user"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'admin' or 'user'"
        )

    # Create user (SSO-only - no password)
    new_user = User(
        id=generate_id(),
        email=user_create.email,
        name=user_create.name,
        hashed_password="",
        auth_provider="google",
        role=user_create.role,
        is_active=True,
        created_by=current_user.id
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
    current_user: User = Depends(get_current_admin_user)
):
    """Update user - admin only"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update fields if provided
    if user_update.name is not None:
        user.name = user_update.name

    if user_update.email is not None:
        # Check if new email is already in use
        existing = db.query(User).filter(
            User.email == user_update.email,
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        user.email = user_update.email

    if user_update.role is not None:
        if user_update.role not in ["admin", "user"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role"
            )
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
    current_user: User = Depends(get_current_admin_user)
):
    """Delete user - admin only. Cannot delete yourself."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if user has assigned contacts
    if user.assigned_contacts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete user with {len(user.assigned_contacts)} assigned contacts. Reassign them first."
        )

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}


@router.post("/me/api-key/generate")
def generate_user_api_key(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate or regenerate API key for current user"""
    # Generate new API key
    new_api_key = generate_api_key()

    # Update user
    current_user.api_key = new_api_key
    db.commit()

    return {
        "api_key": new_api_key,
        "message": "API key generated successfully. Store it securely - it won't be shown again."
    }


@router.delete("/me/api-key")
def revoke_user_api_key(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Revoke API key for current user"""
    if not current_user.api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No API key found"
        )

    current_user.api_key = None
    db.commit()

    return {"message": "API key revoked successfully"}


@router.get("/me/api-key/status")
def get_api_key_status(
    current_user: User = Depends(get_current_active_user)
):
    """Check if current user has an API key (doesn't return the actual key)"""
    return {
        "has_api_key": current_user.api_key is not None,
        "api_key_prefix": current_user.api_key[:12] + "..." if current_user.api_key else None
    }

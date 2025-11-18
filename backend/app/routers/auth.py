from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import User
from app.schemas.schemas import (
    LoginRequest, Token, User as UserSchema, UserCreate,
    PasswordResetRequest, PasswordReset, PasswordChange
)
from app.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user,
    get_current_active_user,
    get_current_user_or_api_key,
    create_password_reset_token,
    verify_reset_token
)
from app.seed_data import generate_id
from app.email import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=Token)
def login(login_request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token"""
    user = db.query(User).filter(User.email == login_request.email).first()

    if not user or not verify_password(login_request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact an administrator."
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserSchema)
def get_me(current_user: User = Depends(get_current_user_or_api_key)):
    """Get current user information"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    return current_user


@router.post("/password-reset-request")
async def request_password_reset(
    request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Request password reset - always returns success to prevent email enumeration"""
    user = db.query(User).filter(User.email == request.email).first()

    if user and user.is_active:
        token = create_password_reset_token(user, db)
        # Send email with reset link
        await send_password_reset_email(user.email, user.name, token)

    # Always return success to prevent email enumeration
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/password-reset")
def reset_password(
    reset: PasswordReset,
    db: Session = Depends(get_db)
):
    """Reset password using token"""
    user = verify_reset_token(reset.token, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Update password
    user.hashed_password = get_password_hash(reset.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.commit()

    return {"message": "Password successfully reset"}


@router.post("/password-change")
def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change password for currently logged in user"""
    # Verify current password
    if not verify_password(password_change.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )

    # Update password
    current_user.hashed_password = get_password_hash(password_change.new_password)
    db.commit()

    return {"message": "Password successfully changed"}

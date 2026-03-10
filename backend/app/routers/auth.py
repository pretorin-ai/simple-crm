import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_refresh_token,
    get_current_active_user,
    get_current_admin_user,
    get_current_user_or_api_key,
    get_password_hash,
    validate_password,
    verify_google_id_token,
    verify_password,
    verify_reset_token,
)
from app.database import get_db
from app.email import send_password_reset_email
from app.models.models import User
from app.schemas.schemas import (
    GoogleAuthRequest,
    LoginRequest,
    PasswordChange,
    PasswordReset,
    PasswordResetRequest,
    RefreshRequest,
    Token,
    UserCreate,
)
from app.schemas.schemas import (
    User as UserSchema,
)
from app.utils import generate_id

router = APIRouter(prefix="/auth", tags=["authentication"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, login_request: LoginRequest, db: Session = Depends(get_db)):
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
            detail="Account is inactive. Please contact an administrator.",
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    refresh = create_refresh_token(data={"sub": user.email})

    return {"access_token": access_token, "refresh_token": refresh, "token_type": "bearer"}


@router.post("/google", response_model=Token)
@limiter.limit("10/minute")
def google_login(request: Request, google_auth: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Authenticate with Google ID token and return JWT token"""
    id_info = verify_google_id_token(google_auth.credential)

    google_id = id_info["sub"]
    email = id_info["email"]
    name = id_info.get("name", email.split("@")[0])

    # Find user by Google ID first
    user = db.query(User).filter(User.google_id == google_id).first()

    if not user:
        # Try to find by email to link existing account
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.google_id = google_id
            if not user.auth_provider:
                user.auth_provider = "google"
            db.commit()
        else:
            # Create new user
            user = User(
                id=generate_id(),
                email=email,
                name=name,
                hashed_password=get_password_hash(secrets.token_hex(32)),
                role="user",
                auth_provider="google",
                google_id=google_id,
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact an administrator.",
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    refresh = create_refresh_token(data={"sub": user.email})

    return {"access_token": access_token, "refresh_token": refresh, "token_type": "bearer"}


@router.post("/register", response_model=UserSchema)
@limiter.limit("5/minute")
def register(
    request: Request,
    user_create: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Register a new user (admin only)"""
    validate_password(user_create.password)

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_create.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create new user
    new_user = User(
        id=generate_id(),
        email=user_create.email,
        name=user_create.name,
        hashed_password=get_password_hash(user_create.password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.get("/me", response_model=UserSchema)
def get_me(current_user: User = Depends(get_current_user_or_api_key)):
    """Get current user information"""
    if not current_user.is_active:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account")
    return current_user


@router.post("/refresh", response_model=Token)
@limiter.limit("30/minute")
def refresh_token(request: Request, body: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a refresh token for a new access token + refresh token pair."""
    email = decode_refresh_token(body.refresh_token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    new_refresh = create_refresh_token(data={"sub": user.email})

    return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer"}


@router.post("/password-reset-request")
@limiter.limit("3/minute")
async def request_password_reset(
    request: Request, body: PasswordResetRequest, db: Session = Depends(get_db)
):
    """Request password reset - always returns success to prevent email enumeration"""
    user = db.query(User).filter(User.email == body.email).first()

    if user and user.is_active:
        token = create_password_reset_token(user, db)
        # Send email with reset link
        await send_password_reset_email(user.email, user.name, token)

    # Always return success to prevent email enumeration
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/password-reset")
@limiter.limit("5/minute")
def reset_password(request: Request, reset: PasswordReset, db: Session = Depends(get_db)):
    """Reset password using token"""
    user = verify_reset_token(reset.token, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    validate_password(reset.new_password)

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
    db: Session = Depends(get_db),
):
    """Change password for currently logged in user"""
    # Verify current password
    if not verify_password(password_change.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password"
        )

    validate_password(password_change.new_password)

    # Update password
    current_user.hashed_password = get_password_hash(password_change.new_password)
    db.commit()

    return {"message": "Password successfully changed"}

"""
Authentication router - SSO only mode.

All authentication is handled via Google OAuth (see oidc_auth.py).
This router only provides the /auth/me endpoint for getting current user info.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.models import User
from app.schemas.schemas import User as UserSchema
from app.auth import get_current_user_or_api_key

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/me", response_model=UserSchema)
def get_me(current_user: User = Depends(get_current_user_or_api_key)):
    """Get current user information"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    return current_user

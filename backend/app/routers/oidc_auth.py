"""
OIDC Authentication Router for Google OAuth
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import httpx
from jose import JWTError

from app.database import get_db
from app.models.models import User
from app.schemas.schemas import OIDCAuthRequest, OIDCAuthResponse, OIDCConfigResponse, User as UserSchema
from app.auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.oidc_config import get_oidc_config, is_oidc_configured
from app.oidc_service import get_oidc_service
from app.seed_data import generate_id

router = APIRouter(prefix="/auth/oidc", tags=["oidc-authentication"])


@router.get("/config", response_model=OIDCConfigResponse)
def get_config():
    """
    Get OIDC configuration for frontend.

    Returns the necessary configuration for the frontend to initiate
    the OAuth 2.0 authorization flow with Google.
    """
    config = get_oidc_config()
    return OIDCConfigResponse(
        client_id=config.client_id,
        authorization_endpoint=config.authorization_endpoint,
        redirect_uri=config.redirect_uri,
        enabled=is_oidc_configured(),
    )


@router.post("/callback", response_model=OIDCAuthResponse)
async def oidc_callback(
    request: OIDCAuthRequest,
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from Google.

    Exchanges the authorization code for tokens, validates the ID token,
    and creates/updates the user in the local database. Returns an
    application JWT for subsequent API requests.
    """
    if not is_oidc_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OIDC authentication is not configured"
        )

    oidc_service = get_oidc_service()

    try:
        # Exchange authorization code for tokens
        tokens = await oidc_service.exchange_code_for_tokens(
            code=request.code,
            code_verifier=request.code_verifier,
        )

        # Validate ID token and get claims
        claims = await oidc_service.validate_id_token(tokens["id_token"])

    except httpx.HTTPStatusError as e:
        error_detail = "Failed to exchange authorization code"
        if e.response.status_code == 400:
            try:
                error_body = e.response.json()
                error_detail = error_body.get("error_description", error_detail)
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_detail
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )

    # Extract user info from claims
    # Google uses 'sub' as the unique user identifier
    google_id = claims.get("sub")
    # Google provides 'email' claim directly
    email = claims.get("email")
    name = claims.get("name")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID token missing email claim. Ensure 'email' scope is included."
        )

    if not google_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID token missing subject (sub) claim."
        )

    # Default name from email if not provided
    if not name:
        name = email.split("@")[0] if email else "Unknown"

    # Find user by Google ID first (handles email changes)
    user = db.query(User).filter(User.google_id == google_id).first()

    if not user:
        # Check if email exists with local auth (for account linking)
        existing_user = db.query(User).filter(User.email == email).first()

        if existing_user:
            # Link existing local user to Google
            existing_user.google_id = google_id
            existing_user.auth_provider = "google"
            # Update name if different
            if existing_user.name != name:
                existing_user.name = name
            user = existing_user
        else:
            # Check if this is the first user (make them admin)
            user_count = db.query(User).count()
            is_first_user = user_count == 0

            # Create new user
            user = User(
                id=generate_id(),
                email=email,
                name=name,
                google_id=google_id,
                auth_provider="google",
                hashed_password="",  # No password for OIDC users
                role="admin" if is_first_user else "user",
            )
            db.add(user)

        db.commit()
        db.refresh(user)
    else:
        # Update user info if changed
        updated = False
        if user.email != email:
            # Check if new email conflicts
            email_conflict = db.query(User).filter(User.email == email, User.id != user.id).first()
            if not email_conflict:
                user.email = email
                updated = True
        if user.name != name:
            user.name = name
            updated = True
        if updated:
            db.commit()
            db.refresh(user)

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact an administrator."
        )

    # Create application JWT
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return OIDCAuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserSchema.model_validate(user)
    )

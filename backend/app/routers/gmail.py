import asyncio
import base64
import json
import logging
import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.database import get_db
from app.encryption import encrypt_value
from app.models.models import Contact, GmailIntegration, User
from app.schemas.schemas import (
    Communication as CommunicationSchema,
)
from app.schemas.schemas import (
    GmailAuthUrl,
    GmailIntegrationStatus,
    GmailSendRequest,
    GoogleContactImportRequest,
    GoogleContactImportResponse,
    GoogleContactPreview,
    GoogleContactsPreviewResponse,
)
from app.services import gmail_service
from app.services.gmail_service import (
    exchange_code,
    fetch_google_contacts,
    get_auth_url,
    get_gmail_address,
    initial_sync,
    process_history_update,
    send_email,
    start_watch,
    stop_watch,
)
from app.utils import generate_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gmail", tags=["gmail"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
GMAIL_WEBHOOK_TOKEN = os.getenv("GMAIL_WEBHOOK_TOKEN", "")


@router.get("/status", response_model=GmailIntegrationStatus)
def gmail_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Check if Gmail is connected for the current user."""
    integration = (
        db.query(GmailIntegration).filter(GmailIntegration.user_id == current_user.id).first()
    )
    if not integration:
        return GmailIntegrationStatus(connected=False)
    return GmailIntegrationStatus(
        connected=True,
        gmail_address=integration.gmail_address,
        last_sync_at=integration.last_sync_at,
    )


@router.get("/auth-url", response_model=GmailAuthUrl)
def gmail_auth_url(
    current_user: User = Depends(get_current_active_user),
):
    """Get the Google OAuth2 authorization URL."""
    if not gmail_service.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gmail integration not configured. Set GOOGLE_CLIENT_ID/SECRET.",
        )
    auth_url = get_auth_url(state=current_user.id)
    return GmailAuthUrl(auth_url=auth_url)


@router.get("/callback")
async def gmail_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """Handle the OAuth2 callback from Google."""
    user_id = state
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(
            url=f"{FRONTEND_URL}/api-settings?gmail=error&reason=invalid_state",
            status_code=302,
        )

    try:
        tokens = await asyncio.to_thread(exchange_code, code)
    except Exception:
        logger.exception("Failed to exchange OAuth code")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/api-settings?gmail=error&reason=auth_failed",
            status_code=302,
        )

    # Get the Gmail address
    from google.oauth2.credentials import Credentials

    creds = Credentials(token=tokens["access_token"])
    try:
        gmail_address = await asyncio.to_thread(get_gmail_address, creds)
    except Exception:
        logger.exception("Failed to get Gmail address")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/api-settings?gmail=error&reason=email_lookup_failed",
            status_code=302,
        )

    # Upsert the integration
    integration = db.query(GmailIntegration).filter(GmailIntegration.user_id == user_id).first()
    if integration:
        integration.access_token = encrypt_value(tokens["access_token"])
        integration.refresh_token = encrypt_value(tokens["refresh_token"])
        integration.token_expiry = tokens.get("token_expiry")
        integration.gmail_address = gmail_address
    else:
        integration = GmailIntegration(
            id=generate_id(),
            user_id=user_id,
            access_token=encrypt_value(tokens["access_token"]),
            refresh_token=encrypt_value(tokens["refresh_token"]),
            token_expiry=tokens.get("token_expiry"),
            gmail_address=gmail_address,
        )
        db.add(integration)

    db.commit()
    db.refresh(integration)

    # Start Pub/Sub watch on INBOX
    try:
        await asyncio.to_thread(start_watch, integration)
        db.commit()
    except Exception:
        logger.warning("Could not start Gmail watch (GOOGLE_PUBSUB_TOPIC may not be set)")

    # Run initial sync of existing emails across all contacts
    try:
        await asyncio.to_thread(initial_sync, db, integration)
    except Exception:
        logger.exception("Initial Gmail sync failed")

    return RedirectResponse(
        url=f"{FRONTEND_URL}/api-settings?gmail=connected",
        status_code=302,
    )


@router.delete("/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def gmail_disconnect(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Disconnect Gmail integration."""
    integration = (
        db.query(GmailIntegration).filter(GmailIntegration.user_id == current_user.id).first()
    )
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gmail not connected",
        )

    await asyncio.to_thread(stop_watch, integration)
    db.delete(integration)
    db.commit()
    return None


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def gmail_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """Receive Gmail Pub/Sub push notifications.

    Google sends a POST with:
    {
      "message": {
        "data": "<base64 of {emailAddress, historyId}>",
        ...
      },
      ...
    }

    Set GMAIL_WEBHOOK_TOKEN to require a Bearer token for verification.
    """
    # Verify webhook authenticity if a shared secret is configured
    if GMAIL_WEBHOOK_TOKEN:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Missing webhook token"
            )
        token = auth_header.removeprefix("Bearer ").strip()
        if not secrets.compare_digest(token, GMAIL_WEBHOOK_TOKEN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook token"
            )

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    message = body.get("message", {})
    data_b64 = message.get("data", "")
    if not data_b64:
        return {"status": "ignored", "reason": "no data"}

    try:
        data = json.loads(base64.urlsafe_b64decode(data_b64))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid data")

    email_address = data.get("emailAddress", "")
    new_history_id = str(data.get("historyId", ""))

    if not email_address or not new_history_id:
        return {"status": "ignored", "reason": "missing fields"}

    integration = (
        db.query(GmailIntegration).filter(GmailIntegration.gmail_address == email_address).first()
    )
    if not integration:
        return {"status": "ignored", "reason": "unknown account"}

    try:
        synced = process_history_update(db, integration, new_history_id)
    except Exception:
        logger.exception("Failed to process history update for %s", email_address)
        return {"status": "error"}

    return {"status": "ok", "synced": synced}


@router.post("/send", response_model=CommunicationSchema, status_code=status.HTTP_201_CREATED)
async def gmail_send(
    request: GmailSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Send an email via Gmail."""
    integration = (
        db.query(GmailIntegration).filter(GmailIntegration.user_id == current_user.id).first()
    )
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail is not connected",
        )

    contact = (
        db.query(Contact)
        .filter(
            Contact.id == request.contact_id,
            Contact.assigned_user_id == current_user.id,
        )
        .first()
    )
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    try:
        comm = await asyncio.to_thread(
            send_email,
            db=db,
            integration=integration,
            contact=contact,
            to=request.to,
            subject=request.subject,
            body=request.body,
            reply_to_message_id=request.reply_to_message_id,
            thread_id=request.thread_id,
        )
    except Exception:
        logger.exception("Failed to send email")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to send email via Gmail",
        )

    return comm


@router.get("/contacts/preview", response_model=GoogleContactsPreviewResponse)
async def gmail_contacts_preview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Fetch Google Contacts for preview before import."""
    integration = (
        db.query(GmailIntegration).filter(GmailIntegration.user_id == current_user.id).first()
    )
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail is not connected. Please connect Gmail first.",
        )

    try:
        raw_contacts = await asyncio.to_thread(fetch_google_contacts, integration)
        db.commit()  # persist any refreshed tokens
    except Exception:
        logger.exception("Failed to fetch Google Contacts")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch contacts from Google. "
            "You may need to reconnect Gmail to grant contacts permission.",
        )

    # Check which emails already exist in the user's contacts
    existing_emails = {
        row[0].lower()
        for row in db.query(Contact.email).filter(Contact.assigned_user_id == current_user.id).all()
    }

    previews = [
        GoogleContactPreview(
            google_resource_name=c["google_resource_name"],
            first_name=c["first_name"],
            last_name=c["last_name"],
            email=c["email"],
            phone=c["phone"],
            organization=c["organization"],
            title=c["title"],
            already_exists=c["email"].lower() in existing_emails,
        )
        for c in raw_contacts
    ]

    return GoogleContactsPreviewResponse(
        contacts=previews,
        total_fetched=len(previews),
    )


@router.post(
    "/contacts/import",
    response_model=GoogleContactImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def gmail_contacts_import(
    request: GoogleContactImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Import selected Google Contacts into the CRM."""
    integration = (
        db.query(GmailIntegration).filter(GmailIntegration.user_id == current_user.id).first()
    )
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail is not connected",
        )

    existing_emails = {
        row[0].lower()
        for row in db.query(Contact.email).filter(Contact.assigned_user_id == current_user.id).all()
    }

    imported = 0
    skipped = 0
    errors: list[str] = []

    for item in request.contacts:
        if item.email.lower() in existing_emails:
            skipped += 1
            continue

        try:
            contact = Contact(
                id=generate_id(),
                first_name=item.first_name,
                last_name=item.last_name,
                email=item.email,
                phone=item.phone,
                organization=item.organization,
                title=item.title or None,
                contact_type=item.contact_type,
                status=item.status,
                notes="",
                assigned_user_id=current_user.id,
            )
            db.add(contact)
            existing_emails.add(item.email.lower())
            imported += 1
        except Exception as e:
            errors.append(f"Failed to import {item.email}: {str(e)}")

    if imported > 0:
        db.commit()

    return GoogleContactImportResponse(
        imported=imported,
        skipped=skipped,
        errors=errors,
    )

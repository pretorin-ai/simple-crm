import base64
import logging
import os
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from typing import Optional

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.encryption import decrypt_value, encrypt_value
from app.models.models import Communication, Contact, GmailIntegration
from app.sanitize import sanitize_html
from app.utils import generate_id

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/contacts.readonly",
]

# These must be set as environment variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
_frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI") or f"{_frontend_url}/api/gmail/callback"
GOOGLE_PUBSUB_TOPIC = os.getenv("GOOGLE_PUBSUB_TOPIC", "")


def _get_client_config():
    return {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [GOOGLE_REDIRECT_URI],
        }
    }


def get_auth_url(state: str) -> str:
    flow = Flow.from_client_config(_get_client_config(), scopes=SCOPES)
    flow.redirect_uri = GOOGLE_REDIRECT_URI
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return auth_url


def exchange_code(code: str) -> dict:
    # Google often returns additional scopes (openid, userinfo.profile) beyond
    # what was requested, causing oauthlib to raise a scope-change Warning.
    # Setting this env var tells oauthlib to accept the changed scopes.
    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")
    flow = Flow.from_client_config(_get_client_config(), scopes=SCOPES)
    flow.redirect_uri = GOOGLE_REDIRECT_URI
    flow.fetch_token(code=code)
    credentials = flow.credentials
    return {
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_expiry": credentials.expiry,
    }


def _get_credentials(integration: GmailIntegration) -> Credentials:
    creds = Credentials(
        token=decrypt_value(integration.access_token),
        refresh_token=decrypt_value(integration.refresh_token),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleRequest())
        integration.access_token = encrypt_value(creds.token)
        if creds.expiry:
            integration.token_expiry = creds.expiry.replace(tzinfo=timezone.utc)
    return creds


def get_gmail_address(credentials: Credentials) -> str:
    service = build("oauth2", "v2", credentials=credentials)
    user_info = service.userinfo().get().execute()
    return user_info["email"]


def _build_gmail_service(integration: GmailIntegration):
    creds = _get_credentials(integration)
    return build("gmail", "v1", credentials=creds)


def start_watch(integration: GmailIntegration) -> None:
    """Start Gmail push notifications via Pub/Sub, watching INBOX only."""
    if not GOOGLE_PUBSUB_TOPIC:
        logger.warning("GOOGLE_PUBSUB_TOPIC not set, skipping watch setup")
        return
    service = _build_gmail_service(integration)
    result = (
        service.users()
        .watch(
            userId="me",
            body={
                "topicName": GOOGLE_PUBSUB_TOPIC,
                "labelIds": ["INBOX"],
                "labelFilterBehavior": "INCLUDE",
            },
        )
        .execute()
    )
    integration.history_id = str(result["historyId"])
    integration.watch_expiry = datetime.fromtimestamp(
        int(result["expiration"]) / 1000, tz=timezone.utc
    )


def stop_watch(integration: GmailIntegration) -> None:
    """Stop Gmail push notifications."""
    try:
        service = _build_gmail_service(integration)
        service.users().stop(userId="me").execute()
    except Exception:
        logger.warning("Failed to stop Gmail watch (may already be expired)")


def _renew_watch_if_needed(integration: GmailIntegration) -> None:
    """Renew watch if it expires within 1 day."""
    if not integration.watch_expiry:
        return
    if integration.watch_expiry - datetime.now(timezone.utc) < timedelta(days=1):
        try:
            start_watch(integration)
        except Exception:
            logger.exception("Failed to renew Gmail watch")


def _parse_email_headers(headers: list) -> dict:
    result = {}
    for header in headers:
        name = header["name"].lower()
        if name in ("from", "to", "subject", "date", "message-id"):
            result[name] = header["value"]
    return result


def _get_email_body(payload: dict) -> tuple[str, str]:
    """Extract plain text and HTML body from email payload."""
    plain_text = ""
    html_body = ""

    if "parts" in payload:
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")
            if mime_type == "text/plain" and "data" in part.get("body", {}):
                plain_text = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
            elif mime_type == "text/html" and "data" in part.get("body", {}):
                html_body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
            elif mime_type.startswith("multipart/"):
                sub_plain, sub_html = _get_email_body(part)
                if sub_plain:
                    plain_text = sub_plain
                if sub_html:
                    html_body = sub_html
    elif "body" in payload and "data" in payload["body"]:
        data = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
        if payload.get("mimeType") == "text/html":
            html_body = data
        else:
            plain_text = data

    return plain_text, html_body


def _extract_email_address(header_value: str) -> str:
    """Extract bare email address from a header like 'Name <email@example.com>'."""
    if "<" in header_value and ">" in header_value:
        return header_value.split("<")[1].split(">")[0].strip().lower()
    return header_value.strip().lower()


def _find_contact_for_message(
    db: Session,
    user_id: str,
    gmail_address: str,
    from_addr: str,
    to_addr: str,
) -> Optional[Contact]:
    """Match an email to a contact by comparing from/to against contact emails."""
    from_email = _extract_email_address(from_addr)
    to_email = _extract_email_address(to_addr)

    # Pick the address that isn't the user's Gmail
    match_email = from_email
    if from_email == gmail_address.lower():
        match_email = to_email

    return (
        db.query(Contact)
        .filter(
            Contact.assigned_user_id == user_id,
            Contact.email.ilike(match_email),
        )
        .first()
    )


def _process_message(
    db: Session,
    service,
    msg_id: str,
    integration: GmailIntegration,
) -> bool:
    """Fetch and store a single Gmail message. Returns True if a new comm was created."""
    existing = db.query(Communication).filter(Communication.gmail_message_id == msg_id).first()
    if existing:
        return False

    try:
        msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    except Exception:
        logger.exception("Failed to fetch Gmail message %s", msg_id)
        return False

    # Only process messages that have the INBOX label
    labels = msg.get("labelIds", [])
    if "INBOX" not in labels and "SENT" not in labels:
        return False

    headers = _parse_email_headers(msg.get("payload", {}).get("headers", []))
    from_addr = headers.get("from", "")
    to_addr = headers.get("to", "")

    contact = _find_contact_for_message(
        db, integration.user_id, integration.gmail_address, from_addr, to_addr
    )
    if not contact:
        return False

    plain_text, html_body = _get_email_body(msg.get("payload", {}))
    subject = headers.get("subject", "(no subject)")

    direction = "inbound"
    if integration.gmail_address.lower() in from_addr.lower():
        direction = "outbound"

    internal_date_ms = int(msg.get("internalDate", "0"))
    email_date = datetime.fromtimestamp(internal_date_ms / 1000, tz=timezone.utc)

    comm = Communication(
        id=generate_id(),
        contact_id=contact.id,
        date=email_date,
        type="email",
        notes=plain_text[:10000] if plain_text else subject,
        subject=subject,
        email_from=from_addr[:255],
        email_to=to_addr[:500],
        body_html=sanitize_html(html_body) or None,
        gmail_message_id=msg_id,
        gmail_thread_id=msg.get("threadId"),
        direction=direction,
    )
    db.add(comm)

    if not contact.last_contacted_at or email_date > contact.last_contacted_at:
        contact.last_contacted_at = email_date

    return True


def process_history_update(
    db: Session,
    integration: GmailIntegration,
    new_history_id: str,
) -> int:
    """Process new messages since the stored history_id using Gmail history API.
    Only considers messages added to INBOX. Returns count of new comms created."""
    if not integration.history_id:
        return 0

    service = _build_gmail_service(integration)
    synced_count = 0

    try:
        history = (
            service.users()
            .history()
            .list(
                userId="me",
                startHistoryId=integration.history_id,
                historyTypes=["messageAdded"],
                labelId="INBOX",
            )
            .execute()
        )
    except Exception:
        logger.exception("Failed to list Gmail history")
        # History ID may be too old; update to the new one
        integration.history_id = new_history_id
        db.commit()
        return 0

    records = history.get("history", [])
    seen_ids: set[str] = set()
    for record in records:
        for added in record.get("messagesAdded", []):
            msg_id = added["message"]["id"]
            if msg_id in seen_ids:
                continue
            seen_ids.add(msg_id)
            if _process_message(db, service, msg_id, integration):
                synced_count += 1

    integration.history_id = new_history_id
    integration.last_sync_at = datetime.now(timezone.utc)
    _renew_watch_if_needed(integration)
    db.commit()

    return synced_count


def initial_sync(
    db: Session,
    integration: GmailIntegration,
    max_results: int = 100,
) -> int:
    """One-time sync: search INBOX for emails matching any of the user's contacts."""
    service = _build_gmail_service(integration)

    contacts = db.query(Contact).filter(Contact.assigned_user_id == integration.user_id).all()
    if not contacts:
        return 0

    synced_count = 0
    for contact in contacts:
        query = f"in:inbox (from:{contact.email} OR to:{contact.email})"
        try:
            results = (
                service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )
        except Exception:
            logger.exception("Failed to list messages for contact %s", contact.id)
            continue

        for msg_ref in results.get("messages", []):
            if _process_message(db, service, msg_ref["id"], integration):
                synced_count += 1

    if synced_count > 0:
        integration.last_sync_at = datetime.now(timezone.utc)
        db.commit()

    return synced_count


def send_email(
    db: Session,
    integration: GmailIntegration,
    contact: Contact,
    to: str,
    subject: str,
    body: str,
    reply_to_message_id: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> Communication:
    """Send an email via Gmail and log it as a Communication."""
    service = _build_gmail_service(integration)

    message = MIMEText(body, "html")
    message["to"] = to
    message["from"] = integration.gmail_address
    message["subject"] = subject

    if reply_to_message_id:
        # For replies, look up the original message's Message-ID header
        try:
            orig = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=reply_to_message_id,
                    format="metadata",
                    metadataHeaders=["Message-ID"],
                )
                .execute()
            )
            for header in orig.get("payload", {}).get("headers", []):
                if header["name"].lower() == "message-id":
                    message["In-Reply-To"] = header["value"]
                    message["References"] = header["value"]
                    break
        except Exception:
            logger.warning("Could not fetch original message headers for reply")

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    send_body: dict = {"raw": raw}
    if thread_id:
        send_body["threadId"] = thread_id

    sent = service.users().messages().send(userId="me", body=send_body).execute()

    now = datetime.now(timezone.utc)
    comm = Communication(
        id=generate_id(),
        contact_id=contact.id,
        date=now,
        type="email",
        notes=body[:10000],
        subject=subject,
        email_from=integration.gmail_address,
        email_to=to,
        body_html=body,
        gmail_message_id=sent["id"],
        gmail_thread_id=sent.get("threadId"),
        direction="outbound",
    )
    db.add(comm)
    contact.last_contacted_at = now
    db.commit()
    db.refresh(comm)
    return comm


def fetch_google_contacts(
    integration: GmailIntegration,
    max_results: int = 1000,
) -> list[dict]:
    """Fetch contacts from Google People API. Returns list of parsed contact dicts."""
    creds = _get_credentials(integration)
    service = build("people", "v1", credentials=creds)

    contacts: list[dict] = []
    page_token = None

    while True:
        kwargs: dict = {
            "resourceName": "people/me",
            "pageSize": min(max_results - len(contacts), 1000),
            "personFields": "names,emailAddresses,phoneNumbers,organizations",
        }
        if page_token:
            kwargs["pageToken"] = page_token

        results = service.people().connections().list(**kwargs).execute()

        for person in results.get("connections", []):
            names = person.get("names", [])
            emails = person.get("emailAddresses", [])

            if not names or not emails:
                continue

            name = names[0]
            first_name = name.get("givenName", "").strip()
            last_name = name.get("familyName", "").strip()

            if not first_name and not last_name:
                display = name.get("displayName", "").strip()
                if not display:
                    continue
                parts = display.split(" ", 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ""

            email = emails[0].get("value", "").strip()
            if not email:
                continue

            phones = person.get("phoneNumbers", [])
            phone = phones[0].get("value", "").strip() if phones else ""

            orgs = person.get("organizations", [])
            organization = ""
            title = ""
            if orgs:
                organization = orgs[0].get("name", "").strip()
                title = orgs[0].get("title", "").strip()

            contacts.append(
                {
                    "google_resource_name": person.get("resourceName", ""),
                    "first_name": first_name[:100],
                    "last_name": last_name[:100],
                    "email": email[:255],
                    "phone": phone[:50],
                    "organization": organization[:200],
                    "title": title[:200],
                }
            )

            if len(contacts) >= max_results:
                break

        page_token = results.get("nextPageToken")
        if not page_token or len(contacts) >= max_results:
            break

    return contacts

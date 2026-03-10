"""Tests for Gmail integration endpoints and service (Pub/Sub webhook architecture)."""

import base64
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.models import Communication, Contact, GmailIntegration
from app.services.gmail_service import fetch_google_contacts
from app.utils import generate_id


@pytest.fixture
def gmail_integration(db, admin_user):
    """Create a Gmail integration for the admin user."""
    integration = GmailIntegration(
        id=generate_id(),
        user_id=admin_user.id,
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_expiry=datetime(2099, 1, 1, tzinfo=timezone.utc),
        gmail_address="admin@gmail.com",
        history_id="12345",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration


@pytest.fixture
def user_gmail_integration(db, regular_user):
    """Create a Gmail integration for the regular user."""
    integration = GmailIntegration(
        id=generate_id(),
        user_id=regular_user.id,
        access_token="test_user_access_token",
        refresh_token="test_user_refresh_token",
        token_expiry=datetime(2099, 1, 1, tzinfo=timezone.utc),
        gmail_address="user@gmail.com",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration


# --- Status endpoint ---


def test_gmail_status_not_connected(client, admin_headers):
    resp = client.get("/gmail/status", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is False
    assert data["gmail_address"] is None


def test_gmail_status_connected(client, admin_headers, gmail_integration):
    resp = client.get("/gmail/status", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True
    assert data["gmail_address"] == "admin@gmail.com"


def test_gmail_status_unauthenticated(client):
    resp = client.get("/gmail/status")
    assert resp.status_code in (401, 403)


# --- Auth URL endpoint ---


@patch("app.services.gmail_service.GOOGLE_CLIENT_ID", "")
def test_gmail_auth_url_not_configured(client, admin_headers):
    resp = client.get("/gmail/auth-url", headers=admin_headers)
    assert resp.status_code == 503


@patch("app.services.gmail_service.GOOGLE_CLIENT_ID", "test-client-id")
@patch("app.services.gmail_service.GOOGLE_CLIENT_SECRET", "test-secret")
@patch("app.services.gmail_service.Flow")
def test_gmail_auth_url_success(mock_flow_cls, client, admin_headers, admin_user):
    mock_flow = MagicMock()
    mock_flow.authorization_url.return_value = (
        "https://accounts.google.com/o/oauth2/auth?test=1",
        "state",
    )
    mock_flow_cls.from_client_config.return_value = mock_flow

    resp = client.get("/gmail/auth-url", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "auth_url" in data
    assert data["auth_url"].startswith("https://accounts.google.com")


# --- Callback endpoint ---


@patch("app.routers.gmail.initial_sync")
@patch("app.routers.gmail.start_watch")
@patch("app.routers.gmail.get_gmail_address")
@patch("app.routers.gmail.exchange_code")
def test_gmail_callback_success(
    mock_exchange,
    mock_get_email,
    mock_start_watch,
    mock_initial_sync,
    client,
    admin_user,
    db,
):
    mock_exchange.return_value = {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "token_expiry": datetime(2099, 6, 1, tzinfo=timezone.utc),
    }
    mock_get_email.return_value = "admin@gmail.com"

    resp = client.get(
        f"/gmail/callback?code=auth_code_123&state={admin_user.id}",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "gmail=connected" in resp.headers["location"]
    assert "/api-settings" in resp.headers["location"]

    # Check integration was created
    integration = (
        db.query(GmailIntegration).filter(GmailIntegration.user_id == admin_user.id).first()
    )
    assert integration is not None
    assert integration.access_token == "new_access_token"
    assert integration.gmail_address == "admin@gmail.com"

    # Verify start_watch and initial_sync were called
    mock_start_watch.assert_called_once()
    mock_initial_sync.assert_called_once()


@patch("app.routers.gmail.initial_sync")
@patch("app.routers.gmail.start_watch")
@patch("app.routers.gmail.get_gmail_address")
@patch("app.routers.gmail.exchange_code")
def test_gmail_callback_updates_existing(
    mock_exchange,
    mock_get_email,
    mock_start_watch,
    mock_initial_sync,
    client,
    admin_user,
    gmail_integration,
    db,
):
    mock_exchange.return_value = {
        "access_token": "updated_token",
        "refresh_token": "updated_refresh",
        "token_expiry": None,
    }
    mock_get_email.return_value = "newemail@gmail.com"

    resp = client.get(
        f"/gmail/callback?code=code&state={admin_user.id}",
        follow_redirects=False,
    )
    assert resp.status_code == 302

    db.refresh(gmail_integration)
    assert gmail_integration.access_token == "updated_token"
    assert gmail_integration.gmail_address == "newemail@gmail.com"


@patch("app.routers.gmail.initial_sync")
@patch("app.routers.gmail.start_watch", side_effect=Exception("watch err"))
@patch("app.routers.gmail.get_gmail_address")
@patch("app.routers.gmail.exchange_code")
def test_gmail_callback_watch_failure_non_fatal(
    mock_exchange,
    mock_get_email,
    mock_start_watch,
    mock_initial_sync,
    client,
    admin_user,
    db,
):
    """start_watch failure should not prevent callback from succeeding."""
    mock_exchange.return_value = {
        "access_token": "t",
        "refresh_token": "r",
        "token_expiry": None,
    }
    mock_get_email.return_value = "a@gmail.com"

    resp = client.get(
        f"/gmail/callback?code=c&state={admin_user.id}",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    mock_initial_sync.assert_called_once()


@patch("app.routers.gmail.start_watch")
@patch("app.routers.gmail.get_gmail_address")
@patch("app.routers.gmail.exchange_code")
def test_gmail_callback_initial_sync_failure_non_fatal(
    mock_exchange,
    mock_get_email,
    mock_start_watch,
    client,
    admin_user,
    db,
):
    """initial_sync failure should not prevent callback from succeeding."""
    mock_exchange.return_value = {
        "access_token": "t",
        "refresh_token": "r",
        "token_expiry": None,
    }
    mock_get_email.return_value = "a@gmail.com"

    with patch("app.routers.gmail.initial_sync", side_effect=Exception("sync err")):
        resp = client.get(
            f"/gmail/callback?code=c&state={admin_user.id}",
            follow_redirects=False,
        )
    assert resp.status_code == 302


def test_gmail_callback_invalid_state(client):
    resp = client.get(
        "/gmail/callback?code=code&state=nonexistent_user_id",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "gmail=error" in resp.headers["location"]
    assert "reason=invalid_state" in resp.headers["location"]


@patch("app.routers.gmail.exchange_code", side_effect=Exception("OAuth error"))
def test_gmail_callback_exchange_failure(mock_exchange, client, admin_user):
    resp = client.get(
        f"/gmail/callback?code=bad_code&state={admin_user.id}",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "gmail=error" in resp.headers["location"]
    assert "reason=auth_failed" in resp.headers["location"]


@patch("app.routers.gmail.exchange_code")
@patch("app.routers.gmail.get_gmail_address", side_effect=Exception("API error"))
def test_gmail_callback_email_fetch_failure(mock_get_email, mock_exchange, client, admin_user):
    mock_exchange.return_value = {
        "access_token": "token",
        "refresh_token": "refresh",
        "token_expiry": None,
    }
    resp = client.get(
        f"/gmail/callback?code=code&state={admin_user.id}",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "gmail=error" in resp.headers["location"]
    assert "reason=email_lookup_failed" in resp.headers["location"]


# --- Disconnect endpoint ---


@patch("app.routers.gmail.stop_watch")
def test_gmail_disconnect_success(
    mock_stop_watch,
    client,
    admin_headers,
    gmail_integration,
    db,
    admin_user,
):
    resp = client.delete("/gmail/disconnect", headers=admin_headers)
    assert resp.status_code == 204

    integration = (
        db.query(GmailIntegration).filter(GmailIntegration.user_id == admin_user.id).first()
    )
    assert integration is None
    mock_stop_watch.assert_called_once()


def test_gmail_disconnect_not_connected(client, admin_headers):
    resp = client.delete("/gmail/disconnect", headers=admin_headers)
    assert resp.status_code == 404


# --- Webhook endpoint ---


def _make_webhook_body(email_address: str, history_id: str) -> dict:
    """Build a Pub/Sub push notification body."""
    data = json.dumps({"emailAddress": email_address, "historyId": history_id}).encode()
    return {"message": {"data": base64.urlsafe_b64encode(data).decode()}}


@patch("app.routers.gmail.process_history_update", return_value=2)
def test_gmail_webhook_success(mock_process, client, gmail_integration):
    body = _make_webhook_body("admin@gmail.com", "99999")
    resp = client.post("/gmail/webhook", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["synced"] == 2
    mock_process.assert_called_once()


def test_gmail_webhook_no_data(client):
    resp = client.post("/gmail/webhook", json={"message": {}})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


def test_gmail_webhook_invalid_json(client):
    resp = client.post(
        "/gmail/webhook",
        content=b"not json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400


def test_gmail_webhook_invalid_base64_data(client):
    resp = client.post(
        "/gmail/webhook",
        json={"message": {"data": "!!!invalid!!!"}},
    )
    assert resp.status_code == 400


def test_gmail_webhook_missing_fields(client):
    data = json.dumps({"emailAddress": "", "historyId": ""}).encode()
    body = {"message": {"data": base64.urlsafe_b64encode(data).decode()}}
    resp = client.post("/gmail/webhook", json=body)
    assert resp.status_code == 200
    assert resp.json()["reason"] == "missing fields"


def test_gmail_webhook_unknown_account(client):
    body = _make_webhook_body("nobody@gmail.com", "111")
    resp = client.post("/gmail/webhook", json=body)
    assert resp.status_code == 200
    assert resp.json()["reason"] == "unknown account"


@patch(
    "app.routers.gmail.process_history_update",
    side_effect=Exception("process err"),
)
def test_gmail_webhook_process_error(mock_process, client, gmail_integration):
    body = _make_webhook_body("admin@gmail.com", "99999")
    resp = client.post("/gmail/webhook", json=body)
    assert resp.status_code == 200
    assert resp.json()["status"] == "error"


# --- Send endpoint ---


def test_gmail_send_not_connected(client, admin_headers, sample_contact):
    resp = client.post(
        "/gmail/send",
        headers=admin_headers,
        json={
            "to": "john@example.com",
            "subject": "Test",
            "body": "Hello",
            "contact_id": sample_contact.id,
        },
    )
    assert resp.status_code == 400


def test_gmail_send_contact_not_found(client, admin_headers, gmail_integration):
    resp = client.post(
        "/gmail/send",
        headers=admin_headers,
        json={
            "to": "nobody@example.com",
            "subject": "Test",
            "body": "Hello",
            "contact_id": "nonexistent",
        },
    )
    assert resp.status_code == 404


def test_gmail_send_contact_not_owned(
    client, admin_headers, gmail_integration, sample_contact_for_regular
):
    resp = client.post(
        "/gmail/send",
        headers=admin_headers,
        json={
            "to": "jane@example.com",
            "subject": "Test",
            "body": "Hello",
            "contact_id": sample_contact_for_regular.id,
        },
    )
    assert resp.status_code == 404


@patch("app.services.gmail_service._build_gmail_service")
def test_gmail_send_success(
    mock_build,
    client,
    admin_headers,
    gmail_integration,
    sample_contact,
    db,
):
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.users().messages().send().execute.return_value = {
        "id": "sent_msg_1",
        "threadId": "sent_thread_1",
    }

    resp = client.post(
        "/gmail/send",
        headers=admin_headers,
        json={
            "to": "john@example.com",
            "subject": "Hello John",
            "body": "<p>Hi there!</p>",
            "contact_id": sample_contact.id,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["subject"] == "Hello John"
    assert data["direction"] == "outbound"
    assert data["gmail_message_id"] == "sent_msg_1"
    assert data["type"] == "email"


@patch("app.services.gmail_service._build_gmail_service")
def test_gmail_send_reply(
    mock_build,
    client,
    admin_headers,
    gmail_integration,
    sample_contact,
    db,
):
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    mock_service.users().messages().get().execute.return_value = {
        "payload": {"headers": [{"name": "Message-ID", "value": "<original@example.com>"}]}
    }
    mock_service.users().messages().send().execute.return_value = {
        "id": "reply_msg_1",
        "threadId": "thread_1",
    }

    resp = client.post(
        "/gmail/send",
        headers=admin_headers,
        json={
            "to": "john@example.com",
            "subject": "Re: Hello",
            "body": "Reply body",
            "contact_id": sample_contact.id,
            "reply_to_message_id": "original_msg",
            "thread_id": "thread_1",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["gmail_thread_id"] == "thread_1"


@patch(
    "app.services.gmail_service._build_gmail_service",
    side_effect=Exception("Send failed"),
)
def test_gmail_send_api_failure(
    mock_build, client, admin_headers, gmail_integration, sample_contact
):
    resp = client.post(
        "/gmail/send",
        headers=admin_headers,
        json={
            "to": "john@example.com",
            "subject": "Test",
            "body": "Hello",
            "contact_id": sample_contact.id,
        },
    )
    assert resp.status_code == 502


def test_gmail_send_validation_no_subject(client, admin_headers, gmail_integration, sample_contact):
    resp = client.post(
        "/gmail/send",
        headers=admin_headers,
        json={
            "to": "john@example.com",
            "subject": "",
            "body": "Hello",
            "contact_id": sample_contact.id,
        },
    )
    assert resp.status_code == 422


def test_gmail_send_validation_invalid_email(
    client, admin_headers, gmail_integration, sample_contact
):
    resp = client.post(
        "/gmail/send",
        headers=admin_headers,
        json={
            "to": "not-an-email",
            "subject": "Test",
            "body": "Hello",
            "contact_id": sample_contact.id,
        },
    )
    assert resp.status_code == 422


@patch("app.services.gmail_service._build_gmail_service")
def test_gmail_send_reply_header_fetch_error(
    mock_build,
    client,
    admin_headers,
    gmail_integration,
    sample_contact,
):
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    mock_service.users().messages().get().execute.side_effect = Exception("Cannot fetch")
    mock_service.users().messages().send().execute.return_value = {
        "id": "reply_despite_err",
        "threadId": "thread_x",
    }

    resp = client.post(
        "/gmail/send",
        headers=admin_headers,
        json={
            "to": "john@example.com",
            "subject": "Re: Test",
            "body": "Reply body",
            "contact_id": sample_contact.id,
            "reply_to_message_id": "orig_msg",
            "thread_id": "thread_x",
        },
    )
    assert resp.status_code == 201


# --- Model tests ---


def test_gmail_integration_model(db, admin_user):
    integration = GmailIntegration(
        id=generate_id(),
        user_id=admin_user.id,
        access_token="token",
        refresh_token="refresh",
        gmail_address="test@gmail.com",
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)

    assert integration.gmail_address == "test@gmail.com"
    assert integration.user.email == admin_user.email


def test_gmail_integration_user_unique(db, admin_user, gmail_integration):
    from sqlalchemy.exc import IntegrityError

    dup = GmailIntegration(
        id=generate_id(),
        user_id=admin_user.id,
        access_token="token2",
        refresh_token="refresh2",
        gmail_address="other@gmail.com",
    )
    db.add(dup)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_communication_email_fields(db, sample_contact):
    comm = Communication(
        id=generate_id(),
        contact_id=sample_contact.id,
        date=datetime.now(timezone.utc),
        type="email",
        notes="Email body text",
        subject="Test Subject",
        email_from="sender@example.com",
        email_to="recipient@example.com",
        body_html="<p>HTML body</p>",
        gmail_message_id="unique_msg_123",
        gmail_thread_id="thread_456",
        direction="inbound",
        created_at=datetime.now(timezone.utc),
    )
    db.add(comm)
    db.commit()
    db.refresh(comm)

    assert comm.subject == "Test Subject"
    assert comm.direction == "inbound"
    assert comm.gmail_message_id == "unique_msg_123"


def test_communication_email_fields_nullable(db, sample_contact):
    comm = Communication(
        id=generate_id(),
        contact_id=sample_contact.id,
        date=datetime.now(timezone.utc),
        type="phone",
        notes="Phone call",
        created_at=datetime.now(timezone.utc),
    )
    db.add(comm)
    db.commit()
    db.refresh(comm)

    assert comm.subject is None
    assert comm.gmail_message_id is None
    assert comm.direction is None


def test_gmail_message_id_unique(db, sample_contact):
    from sqlalchemy.exc import IntegrityError

    comm1 = Communication(
        id=generate_id(),
        contact_id=sample_contact.id,
        date=datetime.now(timezone.utc),
        type="email",
        notes="First",
        gmail_message_id="same_id",
        created_at=datetime.now(timezone.utc),
    )
    db.add(comm1)
    db.commit()

    comm2 = Communication(
        id=generate_id(),
        contact_id=sample_contact.id,
        date=datetime.now(timezone.utc),
        type="email",
        notes="Second",
        gmail_message_id="same_id",
        created_at=datetime.now(timezone.utc),
    )
    db.add(comm2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_user_gmail_integration_relationship(db, admin_user, gmail_integration):
    db.refresh(admin_user)
    assert admin_user.gmail_integration is not None
    assert admin_user.gmail_integration.gmail_address == "admin@gmail.com"


def test_user_gmail_integration_cascade_delete(db, admin_user, gmail_integration):
    integration_id = gmail_integration.id
    db.delete(admin_user)
    db.commit()

    result = db.query(GmailIntegration).filter(GmailIntegration.id == integration_id).first()
    assert result is None


def test_gmail_communication_schema_has_email_fields(client, admin_headers, sample_contact, db):
    comm = Communication(
        id=generate_id(),
        contact_id=sample_contact.id,
        date=datetime.now(timezone.utc),
        type="email",
        notes="Synced email",
        subject="Schema Test",
        email_from="sender@test.com",
        email_to="admin@gmail.com",
        gmail_message_id="schema_msg",
        gmail_thread_id="schema_thread",
        direction="inbound",
        created_at=datetime.now(timezone.utc),
    )
    db.add(comm)
    db.commit()

    resp = client.get(
        f"/communications?contact_id={sample_contact.id}",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["subject"] == "Schema Test"
    assert data[0]["direction"] == "inbound"
    assert data[0]["gmail_message_id"] == "schema_msg"
    assert data[0]["email_from"] == "sender@test.com"


# --- Service: _extract_email_address ---


def test_extract_email_address_with_name():
    from app.services.gmail_service import _extract_email_address

    assert _extract_email_address("John <john@test.com>") == "john@test.com"


def test_extract_email_address_bare():
    from app.services.gmail_service import _extract_email_address

    assert _extract_email_address("john@test.com") == "john@test.com"


def test_extract_email_address_uppercase():
    from app.services.gmail_service import _extract_email_address

    assert _extract_email_address("JOHN@TEST.COM") == "john@test.com"


# --- Service: _find_contact_for_message ---


def test_find_contact_inbound(db, admin_user, sample_contact):
    from app.services.gmail_service import _find_contact_for_message

    contact = _find_contact_for_message(
        db,
        admin_user.id,
        "admin@gmail.com",
        "john@example.com",
        "admin@gmail.com",
    )
    assert contact is not None
    assert contact.id == sample_contact.id


def test_find_contact_outbound(db, admin_user, sample_contact):
    from app.services.gmail_service import _find_contact_for_message

    contact = _find_contact_for_message(
        db,
        admin_user.id,
        "admin@gmail.com",
        "admin@gmail.com",
        "john@example.com",
    )
    assert contact is not None
    assert contact.id == sample_contact.id


def test_find_contact_no_match(db, admin_user, sample_contact):
    from app.services.gmail_service import _find_contact_for_message

    contact = _find_contact_for_message(
        db,
        admin_user.id,
        "admin@gmail.com",
        "unknown@other.com",
        "admin@gmail.com",
    )
    assert contact is None


# --- Service: _process_message ---


def _make_gmail_message(
    msg_id="msg_1",
    thread_id="thread_1",
    from_addr="john@example.com",
    to_addr="admin@gmail.com",
    subject="Test email",
    body_text="Hello from test",
    labels=None,
):
    """Helper to build a mock Gmail message dict."""
    if labels is None:
        labels = ["INBOX"]
    plain_body = base64.urlsafe_b64encode(body_text.encode()).decode()
    return {
        "id": msg_id,
        "threadId": thread_id,
        "internalDate": "1700000000000",
        "labelIds": labels,
        "payload": {
            "headers": [
                {"name": "From", "value": from_addr},
                {"name": "To", "value": to_addr},
                {"name": "Subject", "value": subject},
            ],
            "mimeType": "text/plain",
            "body": {"data": plain_body},
        },
    }


@patch("app.services.gmail_service._build_gmail_service")
def test_process_message_creates_comm(
    mock_build,
    db,
    gmail_integration,
    sample_contact,
):
    from app.services.gmail_service import _process_message

    mock_service = MagicMock()
    mock_service.users().messages().get().execute.return_value = _make_gmail_message()

    result = _process_message(db, mock_service, "msg_1", gmail_integration)
    assert result is True

    db.flush()
    comm = db.query(Communication).filter(Communication.gmail_message_id == "msg_1").first()
    assert comm is not None
    assert comm.subject == "Test email"
    assert comm.direction == "inbound"
    assert comm.type == "email"


@patch("app.services.gmail_service._build_gmail_service")
def test_process_message_outbound(
    mock_build,
    db,
    gmail_integration,
    sample_contact,
):
    from app.services.gmail_service import _process_message

    mock_service = MagicMock()
    mock_service.users().messages().get().execute.return_value = _make_gmail_message(
        from_addr="admin@gmail.com",
        to_addr="john@example.com",
        labels=["SENT"],
    )

    result = _process_message(db, mock_service, "out_1", gmail_integration)
    assert result is True

    db.flush()
    comm = db.query(Communication).filter(Communication.gmail_message_id == "out_1").first()
    assert comm.direction == "outbound"


def test_process_message_skips_duplicate(db, gmail_integration, sample_contact):
    from app.services.gmail_service import _process_message

    existing = Communication(
        id=generate_id(),
        contact_id=sample_contact.id,
        date=datetime.now(timezone.utc),
        type="email",
        notes="Existing",
        gmail_message_id="dup_msg",
        created_at=datetime.now(timezone.utc),
    )
    db.add(existing)
    db.commit()

    mock_service = MagicMock()
    result = _process_message(db, mock_service, "dup_msg", gmail_integration)
    assert result is False
    # get() should not have been called
    mock_service.users().messages().get.assert_not_called()


def test_process_message_fetch_error(db, gmail_integration, sample_contact):
    from app.services.gmail_service import _process_message

    mock_service = MagicMock()
    mock_service.users().messages().get().execute.side_effect = Exception("Fetch failed")

    result = _process_message(db, mock_service, "err_msg", gmail_integration)
    assert result is False


def test_process_message_skips_non_inbox_sent(
    db,
    gmail_integration,
    sample_contact,
):
    from app.services.gmail_service import _process_message

    mock_service = MagicMock()
    mock_service.users().messages().get().execute.return_value = _make_gmail_message(
        labels=["SPAM"]
    )

    result = _process_message(db, mock_service, "spam_msg", gmail_integration)
    assert result is False


def test_process_message_no_matching_contact(db, gmail_integration):
    from app.services.gmail_service import _process_message

    mock_service = MagicMock()
    mock_service.users().messages().get().execute.return_value = _make_gmail_message(
        from_addr="stranger@other.com",
        to_addr="admin@gmail.com",
    )

    result = _process_message(db, mock_service, "no_contact_msg", gmail_integration)
    assert result is False


def test_process_message_updates_last_contacted(
    db,
    gmail_integration,
    sample_contact,
):
    from app.services.gmail_service import _process_message

    mock_service = MagicMock()
    mock_service.users().messages().get().execute.return_value = _make_gmail_message()

    _process_message(db, mock_service, "lca_msg", gmail_integration)

    db.flush()
    db.expire_all()
    contact = db.query(Contact).filter(Contact.id == sample_contact.id).first()
    assert contact.last_contacted_at is not None


# --- Service: process_history_update ---


@patch("app.services.gmail_service._renew_watch_if_needed")
@patch("app.services.gmail_service._build_gmail_service")
def test_process_history_update_success(
    mock_build,
    mock_renew,
    db,
    gmail_integration,
    sample_contact,
):
    from app.services.gmail_service import process_history_update

    mock_service = MagicMock()
    mock_build.return_value = mock_service

    mock_service.users().history().list().execute.return_value = {
        "history": [
            {
                "messagesAdded": [
                    {"message": {"id": "hist_msg_1"}},
                ]
            }
        ]
    }
    mock_service.users().messages().get().execute.return_value = _make_gmail_message(
        msg_id="hist_msg_1"
    )

    count = process_history_update(db, gmail_integration, "99999")
    assert count == 1

    db.refresh(gmail_integration)
    assert gmail_integration.history_id == "99999"
    assert gmail_integration.last_sync_at is not None
    mock_renew.assert_called_once()


def test_process_history_update_no_history_id(db, admin_user):
    from app.services.gmail_service import process_history_update

    integration = GmailIntegration(
        id=generate_id(),
        user_id=admin_user.id,
        access_token="t",
        refresh_token="r",
        gmail_address="a@gmail.com",
        history_id=None,
    )
    db.add(integration)
    db.commit()

    count = process_history_update(db, integration, "999")
    assert count == 0


@patch("app.services.gmail_service._build_gmail_service")
def test_process_history_update_api_error(
    mock_build,
    db,
    gmail_integration,
):
    from app.services.gmail_service import process_history_update

    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.users().history().list().execute.side_effect = Exception("History error")

    count = process_history_update(db, gmail_integration, "99999")
    assert count == 0

    db.refresh(gmail_integration)
    assert gmail_integration.history_id == "99999"


@patch("app.services.gmail_service._renew_watch_if_needed")
@patch("app.services.gmail_service._build_gmail_service")
def test_process_history_update_deduplicates(
    mock_build,
    mock_renew,
    db,
    gmail_integration,
    sample_contact,
):
    from app.services.gmail_service import process_history_update

    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Same message appears twice in history
    mock_service.users().history().list().execute.return_value = {
        "history": [
            {"messagesAdded": [{"message": {"id": "dup_hist"}}]},
            {"messagesAdded": [{"message": {"id": "dup_hist"}}]},
        ]
    }
    mock_service.users().messages().get().execute.return_value = _make_gmail_message(
        msg_id="dup_hist"
    )

    count = process_history_update(db, gmail_integration, "99999")
    assert count == 1


@patch("app.services.gmail_service._renew_watch_if_needed")
@patch("app.services.gmail_service._build_gmail_service")
def test_process_history_update_empty(
    mock_build,
    mock_renew,
    db,
    gmail_integration,
):
    from app.services.gmail_service import process_history_update

    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.users().history().list().execute.return_value = {}

    count = process_history_update(db, gmail_integration, "99999")
    assert count == 0


# --- Service: initial_sync ---


@patch("app.services.gmail_service._build_gmail_service")
def test_initial_sync_success(
    mock_build,
    db,
    gmail_integration,
    sample_contact,
):
    from app.services.gmail_service import initial_sync

    mock_service = MagicMock()
    mock_build.return_value = mock_service

    mock_service.users().messages().list().execute.return_value = {
        "messages": [{"id": "init_msg_1"}]
    }
    mock_service.users().messages().get().execute.return_value = _make_gmail_message(
        msg_id="init_msg_1"
    )

    count = initial_sync(db, gmail_integration)
    assert count == 1

    db.refresh(gmail_integration)
    assert gmail_integration.last_sync_at is not None


@patch("app.services.gmail_service._build_gmail_service")
def test_initial_sync_no_contacts(mock_build, db, gmail_integration):
    from app.services.gmail_service import initial_sync

    count = initial_sync(db, gmail_integration)
    assert count == 0


@patch("app.services.gmail_service._build_gmail_service")
def test_initial_sync_no_messages(
    mock_build,
    db,
    gmail_integration,
    sample_contact,
):
    from app.services.gmail_service import initial_sync

    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.users().messages().list().execute.return_value = {}

    count = initial_sync(db, gmail_integration)
    assert count == 0


@patch("app.services.gmail_service._build_gmail_service")
def test_initial_sync_list_error(
    mock_build,
    db,
    gmail_integration,
    sample_contact,
):
    from app.services.gmail_service import initial_sync

    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.users().messages().list().execute.side_effect = Exception("List failed")

    count = initial_sync(db, gmail_integration)
    assert count == 0


# --- Service: start_watch / stop_watch / _renew_watch_if_needed ---


@patch("app.services.gmail_service._build_gmail_service")
@patch("app.services.gmail_service.GOOGLE_PUBSUB_TOPIC", "projects/x/topics/y")
def test_start_watch_success(mock_build, db, gmail_integration):
    from app.services.gmail_service import start_watch

    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.users().watch().execute.return_value = {
        "historyId": "55555",
        "expiration": str(int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp() * 1000)),
    }

    start_watch(gmail_integration)
    assert gmail_integration.history_id == "55555"
    assert gmail_integration.watch_expiry is not None


@patch("app.services.gmail_service.GOOGLE_PUBSUB_TOPIC", "")
def test_start_watch_no_topic(gmail_integration):
    from app.services.gmail_service import start_watch

    start_watch(gmail_integration)
    # Should be a no-op; history_id unchanged
    assert gmail_integration.history_id == "12345"


@patch("app.services.gmail_service._build_gmail_service")
def test_stop_watch_success(mock_build, gmail_integration):
    from app.services.gmail_service import stop_watch

    mock_service = MagicMock()
    mock_build.return_value = mock_service

    stop_watch(gmail_integration)
    mock_service.users().stop.assert_called_once()


@patch("app.services.gmail_service._build_gmail_service")
def test_stop_watch_error_non_fatal(mock_build, gmail_integration):
    from app.services.gmail_service import stop_watch

    mock_build.side_effect = Exception("stop err")
    stop_watch(gmail_integration)  # Should not raise


@patch("app.services.gmail_service.start_watch")
def test_renew_watch_if_needed_expires_soon(mock_start, gmail_integration):
    from app.services.gmail_service import _renew_watch_if_needed

    gmail_integration.watch_expiry = datetime.now(timezone.utc) + timedelta(hours=12)
    _renew_watch_if_needed(gmail_integration)
    mock_start.assert_called_once_with(gmail_integration)


@patch("app.services.gmail_service.start_watch")
def test_renew_watch_if_needed_not_expiring(mock_start, gmail_integration):
    from app.services.gmail_service import _renew_watch_if_needed

    gmail_integration.watch_expiry = datetime.now(timezone.utc) + timedelta(days=5)
    _renew_watch_if_needed(gmail_integration)
    mock_start.assert_not_called()


def test_renew_watch_if_needed_no_expiry(gmail_integration):
    from app.services.gmail_service import _renew_watch_if_needed

    gmail_integration.watch_expiry = None
    _renew_watch_if_needed(gmail_integration)  # Should be a no-op


@patch(
    "app.services.gmail_service.start_watch",
    side_effect=Exception("renew err"),
)
def test_renew_watch_if_needed_error_non_fatal(mock_start, gmail_integration):
    from app.services.gmail_service import _renew_watch_if_needed

    gmail_integration.watch_expiry = datetime.now(timezone.utc) + timedelta(hours=6)
    _renew_watch_if_needed(gmail_integration)  # Should not raise


# --- Service: helper unit tests ---


def test_parse_email_headers():
    from app.services.gmail_service import _parse_email_headers

    headers = [
        {"name": "From", "value": "sender@test.com"},
        {"name": "To", "value": "recipient@test.com"},
        {"name": "Subject", "value": "Test Subject"},
        {"name": "Date", "value": "Mon, 1 Jan 2024 00:00:00 +0000"},
        {"name": "Message-ID", "value": "<abc@test.com>"},
        {"name": "X-Custom", "value": "ignored"},
    ]
    result = _parse_email_headers(headers)
    assert result["from"] == "sender@test.com"
    assert result["to"] == "recipient@test.com"
    assert result["subject"] == "Test Subject"
    assert "x-custom" not in result


def test_get_email_body_plain_only():
    from app.services.gmail_service import _get_email_body

    plain = base64.urlsafe_b64encode(b"Plain text").decode()
    payload = {"mimeType": "text/plain", "body": {"data": plain}}
    text, html = _get_email_body(payload)
    assert text == "Plain text"
    assert html == ""


def test_get_email_body_html_only():
    from app.services.gmail_service import _get_email_body

    html_data = base64.urlsafe_b64encode(b"<p>HTML</p>").decode()
    payload = {"mimeType": "text/html", "body": {"data": html_data}}
    text, html = _get_email_body(payload)
    assert text == ""
    assert html == "<p>HTML</p>"


def test_get_email_body_no_data():
    from app.services.gmail_service import _get_email_body

    payload = {"mimeType": "text/plain", "body": {}}
    text, html = _get_email_body(payload)
    assert text == ""
    assert html == ""


def test_get_email_body_multipart():
    from app.services.gmail_service import _get_email_body

    plain = base64.urlsafe_b64encode(b"Plain").decode()
    html_data = base64.urlsafe_b64encode(b"<p>HTML</p>").decode()
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/plain", "body": {"data": plain}},
            {"mimeType": "text/html", "body": {"data": html_data}},
        ],
    }
    text, html = _get_email_body(payload)
    assert text == "Plain"
    assert html == "<p>HTML</p>"


def test_get_email_body_nested_with_plain_text():
    from app.services.gmail_service import _get_email_body

    plain = base64.urlsafe_b64encode(b"Nested plain").decode()
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": plain}},
                ],
            },
        ],
    }
    text, html = _get_email_body(payload)
    assert text == "Nested plain"
    assert html == ""


def test_get_email_body_nested_with_html():
    from app.services.gmail_service import _get_email_body

    html_data = base64.urlsafe_b64encode(b"<b>Nested HTML</b>").decode()
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/html", "body": {"data": html_data}},
                ],
            },
        ],
    }
    text, html = _get_email_body(payload)
    assert text == ""
    assert html == "<b>Nested HTML</b>"


@patch("app.services.gmail_service.GOOGLE_CLIENT_ID", "test-id")
@patch("app.services.gmail_service.GOOGLE_CLIENT_SECRET", "test-secret")
@patch("app.services.gmail_service.GOOGLE_REDIRECT_URI", "http://localhost/callback")
def test_get_client_config():
    from app.services.gmail_service import _get_client_config

    config = _get_client_config()
    assert "web" in config
    assert config["web"]["client_id"] == "test-id"
    assert config["web"]["client_secret"] == "test-secret"


@patch("app.services.gmail_service.GOOGLE_CLIENT_ID", "test-id")
@patch("app.services.gmail_service.GOOGLE_CLIENT_SECRET", "test-secret")
@patch("app.services.gmail_service.Flow")
def test_get_auth_url(mock_flow_cls):
    from app.services.gmail_service import get_auth_url

    mock_flow = MagicMock()
    mock_flow.authorization_url.return_value = ("https://auth.url", "state")
    mock_flow_cls.from_client_config.return_value = mock_flow

    url = get_auth_url("user_state")
    assert url == "https://auth.url"


@patch("app.services.gmail_service.GOOGLE_CLIENT_ID", "test-id")
@patch("app.services.gmail_service.GOOGLE_CLIENT_SECRET", "test-secret")
@patch("app.services.gmail_service.Flow")
def test_exchange_code(mock_flow_cls):
    from app.services.gmail_service import exchange_code

    mock_flow = MagicMock()
    mock_creds = MagicMock()
    mock_creds.token = "access_token"
    mock_creds.refresh_token = "refresh_token"
    mock_creds.expiry = None
    mock_flow.credentials = mock_creds
    mock_flow_cls.from_client_config.return_value = mock_flow

    result = exchange_code("code123")
    assert result["access_token"] == "access_token"
    assert result["refresh_token"] == "refresh_token"


@patch("app.services.gmail_service.build")
def test_get_gmail_address(mock_build):
    from app.services.gmail_service import get_gmail_address

    mock_service = MagicMock()
    mock_service.userinfo().get().execute.return_value = {"email": "test@gmail.com"}
    mock_build.return_value = mock_service

    creds = MagicMock()
    email = get_gmail_address(creds)
    assert email == "test@gmail.com"


@patch("app.services.gmail_service.GoogleRequest")
@patch("app.services.gmail_service.GOOGLE_CLIENT_ID", "test-id")
@patch("app.services.gmail_service.GOOGLE_CLIENT_SECRET", "test-secret")
def test_get_credentials_refresh(mock_google_request, db, admin_user):
    from app.services.gmail_service import _get_credentials

    integration = GmailIntegration(
        id=generate_id(),
        user_id=admin_user.id,
        access_token="old_token",
        refresh_token="refresh_token",
        gmail_address="test@gmail.com",
    )
    db.add(integration)
    db.commit()

    with patch("app.services.gmail_service.Credentials") as mock_creds_cls:
        mock_creds = MagicMock()
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh_token"
        mock_creds.token = "new_token"
        mock_creds.expiry = datetime(2099, 1, 1)
        mock_creds_cls.return_value = mock_creds

        result = _get_credentials(integration)
        mock_creds.refresh.assert_called_once()
        assert integration.access_token == "new_token"
        assert result == mock_creds


@patch("app.services.gmail_service.build")
@patch("app.services.gmail_service.GOOGLE_CLIENT_ID", "test-id")
@patch("app.services.gmail_service.GOOGLE_CLIENT_SECRET", "test-secret")
def test_build_gmail_service(mock_build, db, admin_user):
    from app.services.gmail_service import _build_gmail_service

    mock_build.return_value = MagicMock()
    integration = GmailIntegration(
        id=generate_id(),
        user_id=admin_user.id,
        access_token="token",
        refresh_token="refresh",
        gmail_address="test@gmail.com",
    )
    db.add(integration)
    db.commit()

    with patch("app.services.gmail_service.Credentials") as mock_creds_cls:
        mock_creds = MagicMock()
        mock_creds.expired = False
        mock_creds_cls.return_value = mock_creds

        result = _build_gmail_service(integration)
        mock_build.assert_called_once_with("gmail", "v1", credentials=mock_creds)
        assert result is not None


@patch("app.services.gmail_service.GoogleRequest")
@patch("app.services.gmail_service.GOOGLE_CLIENT_ID", "test-id")
@patch("app.services.gmail_service.GOOGLE_CLIENT_SECRET", "test-secret")
def test_get_credentials_no_refresh_needed(
    mock_google_request,
    db,
    admin_user,
):
    from app.services.gmail_service import _get_credentials

    integration = GmailIntegration(
        id=generate_id(),
        user_id=admin_user.id,
        access_token="valid_token",
        refresh_token="refresh_token",
        gmail_address="test@gmail.com",
    )
    db.add(integration)
    db.commit()

    with patch("app.services.gmail_service.Credentials") as mock_creds_cls:
        mock_creds = MagicMock()
        mock_creds.expired = False
        mock_creds_cls.return_value = mock_creds

        _get_credentials(integration)
        mock_creds.refresh.assert_not_called()


# --- Webhook authentication tests ---


@patch("app.routers.gmail.GMAIL_WEBHOOK_TOKEN", "secret123")
@patch("app.routers.gmail.process_history_update", return_value=1)
def test_gmail_webhook_auth_valid_token(mock_process, client, gmail_integration):
    """Webhook succeeds with correct Bearer token when GMAIL_WEBHOOK_TOKEN is set."""
    body = _make_webhook_body("admin@gmail.com", "99999")
    resp = client.post("/gmail/webhook", json=body, headers={"Authorization": "Bearer secret123"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@patch("app.routers.gmail.GMAIL_WEBHOOK_TOKEN", "secret123")
def test_gmail_webhook_auth_missing_token(client):
    """Webhook rejects request without Authorization header."""
    body = _make_webhook_body("admin@gmail.com", "99999")
    resp = client.post("/gmail/webhook", json=body)
    assert resp.status_code == 403
    assert "Missing webhook token" in resp.json()["detail"]


@patch("app.routers.gmail.GMAIL_WEBHOOK_TOKEN", "secret123")
def test_gmail_webhook_auth_wrong_token(client):
    """Webhook rejects request with wrong Bearer token."""
    body = _make_webhook_body("admin@gmail.com", "99999")
    resp = client.post("/gmail/webhook", json=body, headers={"Authorization": "Bearer wrongtoken"})
    assert resp.status_code == 403
    assert "Invalid webhook token" in resp.json()["detail"]


# --- Google Contacts import: service function ---


def _make_people_api_response(connections, next_page_token=None):
    """Helper to build a mock People API connections.list response."""
    resp = {"connections": connections}
    if next_page_token:
        resp["nextPageToken"] = next_page_token
    return resp


def _make_person(
    resource_name="people/1",
    given_name="Alice",
    family_name="Smith",
    email="alice@example.com",
    phone="555-0001",
    org_name="Acme Inc",
    org_title="Engineer",
):
    person = {"resourceName": resource_name}
    if given_name or family_name:
        person["names"] = [{"givenName": given_name, "familyName": family_name}]
    if email:
        person["emailAddresses"] = [{"value": email}]
    if phone:
        person["phoneNumbers"] = [{"value": phone}]
    if org_name or org_title:
        person["organizations"] = [{"name": org_name or "", "title": org_title or ""}]
    return person


@patch("app.services.gmail_service._get_credentials")
@patch("app.services.gmail_service.build")
def test_fetch_google_contacts_basic(mock_build, mock_get_creds, gmail_integration):
    """Fetches contacts from Google People API."""
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.people().connections().list().execute.return_value = _make_people_api_response(
        [
            _make_person("people/1", "Alice", "Smith", "alice@ex.com", "555-1", "Acme", "Dev"),
            _make_person("people/2", "Bob", "Jones", "bob@ex.com", "555-2", "Corp", ""),
        ]
    )

    result = fetch_google_contacts(gmail_integration, max_results=100)
    assert len(result) == 2
    assert result[0]["first_name"] == "Alice"
    assert result[0]["last_name"] == "Smith"
    assert result[0]["email"] == "alice@ex.com"
    assert result[0]["phone"] == "555-1"
    assert result[0]["organization"] == "Acme"
    assert result[0]["title"] == "Dev"
    assert result[0]["google_resource_name"] == "people/1"
    assert result[1]["first_name"] == "Bob"


@patch("app.services.gmail_service._get_credentials")
@patch("app.services.gmail_service.build")
def test_fetch_google_contacts_skips_no_name(mock_build, mock_get_creds, gmail_integration):
    """Skips contacts without a name."""
    person_no_name = {"resourceName": "people/x", "emailAddresses": [{"value": "a@b.com"}]}
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.people().connections().list().execute.return_value = _make_people_api_response(
        [person_no_name, _make_person()]
    )

    result = fetch_google_contacts(gmail_integration)
    assert len(result) == 1
    assert result[0]["first_name"] == "Alice"


@patch("app.services.gmail_service._get_credentials")
@patch("app.services.gmail_service.build")
def test_fetch_google_contacts_skips_no_email(mock_build, mock_get_creds, gmail_integration):
    """Skips contacts without an email."""
    person_no_email = {
        "resourceName": "people/x",
        "names": [{"givenName": "No", "familyName": "Email"}],
    }
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.people().connections().list().execute.return_value = _make_people_api_response(
        [person_no_email, _make_person()]
    )

    result = fetch_google_contacts(gmail_integration)
    assert len(result) == 1


@patch("app.services.gmail_service._get_credentials")
@patch("app.services.gmail_service.build")
def test_fetch_google_contacts_display_name_fallback(mock_build, mock_get_creds, gmail_integration):
    """Falls back to displayName when givenName/familyName are empty."""
    person = {
        "resourceName": "people/dn",
        "names": [{"givenName": "", "familyName": "", "displayName": "Full Name"}],
        "emailAddresses": [{"value": "dn@ex.com"}],
    }
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.people().connections().list().execute.return_value = _make_people_api_response(
        [person]
    )

    result = fetch_google_contacts(gmail_integration)
    assert len(result) == 1
    assert result[0]["first_name"] == "Full"
    assert result[0]["last_name"] == "Name"


@patch("app.services.gmail_service._get_credentials")
@patch("app.services.gmail_service.build")
def test_fetch_google_contacts_single_display_name(mock_build, mock_get_creds, gmail_integration):
    """Single-word displayName puts it in first_name with empty last_name."""
    person = {
        "resourceName": "people/sdn",
        "names": [{"givenName": "", "familyName": "", "displayName": "Mononym"}],
        "emailAddresses": [{"value": "mono@ex.com"}],
    }
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.people().connections().list().execute.return_value = _make_people_api_response(
        [person]
    )

    result = fetch_google_contacts(gmail_integration)
    assert result[0]["first_name"] == "Mononym"
    assert result[0]["last_name"] == ""


@patch("app.services.gmail_service._get_credentials")
@patch("app.services.gmail_service.build")
def test_fetch_google_contacts_no_org_no_phone(mock_build, mock_get_creds, gmail_integration):
    """Handles contacts without org or phone."""
    person = _make_person("people/bare", "Solo", "Person", "solo@ex.com", "", "", "")
    person.pop("phoneNumbers", None)
    person.pop("organizations", None)
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.people().connections().list().execute.return_value = _make_people_api_response(
        [person]
    )

    result = fetch_google_contacts(gmail_integration)
    assert len(result) == 1
    assert result[0]["phone"] == ""
    assert result[0]["organization"] == ""
    assert result[0]["title"] == ""


@patch("app.services.gmail_service._get_credentials")
@patch("app.services.gmail_service.build")
def test_fetch_google_contacts_max_results(mock_build, mock_get_creds, gmail_integration):
    """Respects max_results limit."""
    people = [_make_person(f"people/{i}", "P", f"{i}", f"p{i}@ex.com") for i in range(10)]
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.people().connections().list().execute.return_value = _make_people_api_response(
        people
    )

    result = fetch_google_contacts(gmail_integration, max_results=3)
    assert len(result) == 3


@patch("app.services.gmail_service._get_credentials")
@patch("app.services.gmail_service.build")
def test_fetch_google_contacts_pagination(mock_build, mock_get_creds, gmail_integration):
    """Handles pagination with nextPageToken."""
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.people().connections().list().execute.side_effect = [
        _make_people_api_response(
            [_make_person("people/1", "A", "A", "a@ex.com")], next_page_token="page2"
        ),
        _make_people_api_response([_make_person("people/2", "B", "B", "b@ex.com")]),
    ]

    result = fetch_google_contacts(gmail_integration, max_results=100)
    assert len(result) == 2


@patch("app.services.gmail_service._get_credentials")
@patch("app.services.gmail_service.build")
def test_fetch_google_contacts_empty(mock_build, mock_get_creds, gmail_integration):
    """Returns empty list when no connections exist."""
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.people().connections().list().execute.return_value = {}

    result = fetch_google_contacts(gmail_integration)
    assert result == []


@patch("app.services.gmail_service._get_credentials")
@patch("app.services.gmail_service.build")
def test_fetch_google_contacts_empty_display_name(mock_build, mock_get_creds, gmail_integration):
    """Skips contacts with empty givenName, familyName, AND displayName."""
    person = {
        "resourceName": "people/empty",
        "names": [{"givenName": "", "familyName": "", "displayName": ""}],
        "emailAddresses": [{"value": "e@ex.com"}],
    }
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.people().connections().list().execute.return_value = _make_people_api_response(
        [person]
    )

    result = fetch_google_contacts(gmail_integration)
    assert len(result) == 0


@patch("app.services.gmail_service._get_credentials")
@patch("app.services.gmail_service.build")
def test_fetch_google_contacts_empty_email_value(mock_build, mock_get_creds, gmail_integration):
    """Skips contacts with an emailAddresses entry that has an empty value."""
    person = {
        "resourceName": "people/noval",
        "names": [{"givenName": "A", "familyName": "B"}],
        "emailAddresses": [{"value": ""}],
    }
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.people().connections().list().execute.return_value = _make_people_api_response(
        [person]
    )

    result = fetch_google_contacts(gmail_integration)
    assert len(result) == 0


# --- Google Contacts import: preview endpoint ---


@patch("app.routers.gmail.fetch_google_contacts")
def test_contacts_preview_success(mock_fetch, client, admin_headers, gmail_integration):
    """Returns Google Contacts preview with already_exists flags."""
    mock_fetch.return_value = [
        {
            "google_resource_name": "people/1",
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice@example.com",
            "phone": "555-0001",
            "organization": "Acme",
            "title": "Dev",
        },
    ]

    resp = client.get("/gmail/contacts/preview", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_fetched"] == 1
    assert len(data["contacts"]) == 1
    assert data["contacts"][0]["first_name"] == "Alice"
    assert data["contacts"][0]["already_exists"] is False


@patch("app.routers.gmail.fetch_google_contacts")
def test_contacts_preview_marks_existing(
    mock_fetch, client, admin_headers, gmail_integration, sample_contact
):
    """Contacts whose email already exists are flagged already_exists=True."""
    mock_fetch.return_value = [
        {
            "google_resource_name": "people/1",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",  # same as sample_contact
            "phone": "555-0001",
            "organization": "Acme",
            "title": "",
        },
        {
            "google_resource_name": "people/2",
            "first_name": "New",
            "last_name": "Person",
            "email": "new@example.com",
            "phone": "",
            "organization": "",
            "title": "",
        },
    ]

    resp = client.get("/gmail/contacts/preview", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_fetched"] == 2
    existing = [c for c in data["contacts"] if c["already_exists"]]
    new_ones = [c for c in data["contacts"] if not c["already_exists"]]
    assert len(existing) == 1
    assert existing[0]["email"] == "john@example.com"
    assert len(new_ones) == 1


def test_contacts_preview_not_connected(client, admin_headers):
    """Returns 400 if Gmail not connected."""
    resp = client.get("/gmail/contacts/preview", headers=admin_headers)
    assert resp.status_code == 400
    assert "not connected" in resp.json()["detail"].lower()


def test_contacts_preview_unauthenticated(client):
    """Requires authentication."""
    resp = client.get("/gmail/contacts/preview")
    assert resp.status_code in (401, 403)


@patch("app.routers.gmail.fetch_google_contacts", side_effect=Exception("API error"))
def test_contacts_preview_api_failure(mock_fetch, client, admin_headers, gmail_integration):
    """Returns 502 on Google API failure."""
    resp = client.get("/gmail/contacts/preview", headers=admin_headers)
    assert resp.status_code == 502


# --- Google Contacts import: import endpoint ---


def test_contacts_import_success(client, admin_headers, gmail_integration):
    """Successfully imports new contacts."""
    payload = {
        "contacts": [
            {
                "first_name": "Alice",
                "last_name": "Smith",
                "email": "alice@newcontact.com",
                "phone": "555-9999",
                "organization": "Acme Inc",
                "title": "Engineer",
                "contact_type": "individual",
                "status": "cold",
            },
            {
                "first_name": "Bob",
                "last_name": "Jones",
                "email": "bob@newcontact.com",
                "phone": "",
                "organization": "",
                "title": "",
                "contact_type": "commercial",
                "status": "warm",
            },
        ]
    }
    resp = client.post("/gmail/contacts/import", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["imported"] == 2
    assert data["skipped"] == 0
    assert data["errors"] == []


def test_contacts_import_skips_existing(client, admin_headers, gmail_integration, sample_contact):
    """Skips contacts that already exist (by email)."""
    payload = {
        "contacts": [
            {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",  # already exists
                "phone": "555-1234",
                "organization": "Test Corp",
                "title": "",
                "contact_type": "individual",
                "status": "cold",
            },
            {
                "first_name": "New",
                "last_name": "Person",
                "email": "new@example.com",
                "phone": "",
                "organization": "",
                "title": "",
                "contact_type": "individual",
                "status": "cold",
            },
        ]
    }
    resp = client.post("/gmail/contacts/import", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["imported"] == 1
    assert data["skipped"] == 1


def test_contacts_import_skips_duplicates_in_batch(client, admin_headers, gmail_integration):
    """Skips duplicate emails within the same import batch."""
    payload = {
        "contacts": [
            {
                "first_name": "Alice",
                "last_name": "One",
                "email": "alice@dup.com",
                "phone": "",
                "organization": "",
                "title": "",
                "contact_type": "individual",
                "status": "cold",
            },
            {
                "first_name": "Alice",
                "last_name": "Two",
                "email": "alice@dup.com",
                "phone": "",
                "organization": "",
                "title": "",
                "contact_type": "individual",
                "status": "cold",
            },
        ]
    }
    resp = client.post("/gmail/contacts/import", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["imported"] == 1
    assert data["skipped"] == 1


def test_contacts_import_not_connected(client, admin_headers):
    """Returns 400 if Gmail not connected."""
    payload = {
        "contacts": [
            {
                "first_name": "X",
                "last_name": "Y",
                "email": "x@y.com",
                "phone": "",
                "organization": "",
                "title": "",
                "contact_type": "individual",
                "status": "cold",
            },
        ]
    }
    resp = client.post("/gmail/contacts/import", json=payload, headers=admin_headers)
    assert resp.status_code == 400


def test_contacts_import_unauthenticated(client):
    """Requires authentication."""
    resp = client.post("/gmail/contacts/import", json={"contacts": []})
    assert resp.status_code in (401, 403, 422)


def test_contacts_import_empty_list(client, admin_headers, gmail_integration):
    """Rejects empty contacts list."""
    resp = client.post("/gmail/contacts/import", json={"contacts": []}, headers=admin_headers)
    assert resp.status_code == 422


def test_contacts_import_validation_missing_name(client, admin_headers, gmail_integration):
    """Rejects contacts without a first_name."""
    payload = {
        "contacts": [
            {
                "first_name": "",
                "last_name": "X",
                "email": "a@b.com",
                "phone": "",
                "organization": "",
                "title": "",
                "contact_type": "individual",
                "status": "cold",
            },
        ]
    }
    resp = client.post("/gmail/contacts/import", json=payload, headers=admin_headers)
    assert resp.status_code == 422


def test_contacts_import_case_insensitive_email_check(
    client, admin_headers, gmail_integration, sample_contact
):
    """Email existence check is case-insensitive."""
    payload = {
        "contacts": [
            {
                "first_name": "John",
                "last_name": "Doe",
                "email": "JOHN@EXAMPLE.COM",  # different case, same email
                "phone": "",
                "organization": "",
                "title": "",
                "contact_type": "individual",
                "status": "cold",
            },
        ]
    }
    resp = client.post("/gmail/contacts/import", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["skipped"] == 1
    assert data["imported"] == 0


@patch("app.routers.gmail.generate_id", side_effect=RuntimeError("id gen failed"))
def test_contacts_import_handles_creation_error(
    mock_gen_id, client, admin_headers, gmail_integration
):
    """Records errors when individual contact creation fails."""
    payload = {
        "contacts": [
            {
                "first_name": "Err",
                "last_name": "Contact",
                "email": "err@example.com",
                "phone": "",
                "organization": "",
                "title": "",
                "contact_type": "individual",
                "status": "cold",
            },
        ]
    }
    resp = client.post("/gmail/contacts/import", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["imported"] == 0
    assert len(data["errors"]) == 1
    assert "err@example.com" in data["errors"][0]


def test_contacts_import_user_isolation(
    client, user_headers, user_gmail_integration, sample_contact
):
    """Regular user can import contacts; existing contacts belong to admin so no conflict."""
    payload = {
        "contacts": [
            {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",  # exists for admin, not for regular user
                "phone": "",
                "organization": "",
                "title": "",
                "contact_type": "individual",
                "status": "cold",
            },
        ]
    }
    resp = client.post("/gmail/contacts/import", json=payload, headers=user_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["imported"] == 1
    assert data["skipped"] == 0

"""Tests for Google IDP authentication endpoints."""

from datetime import datetime, timezone
from unittest.mock import patch

from app.auth import get_password_hash
from app.models.models import User
from app.utils import generate_id

FAKE_GOOGLE_ID_INFO = {
    "sub": "google-uid-12345",
    "email": "googleuser@gmail.com",
    "email_verified": True,
    "name": "Google User",
    "iss": "accounts.google.com",
}


@patch("app.auth.GOOGLE_CLIENT_ID", "test-client-id")
@patch("app.auth.google_id_token.verify_oauth2_token")
def test_google_login_creates_new_user(mock_verify, client):
    mock_verify.return_value = FAKE_GOOGLE_ID_INFO

    response = client.post("/auth/google", json={"credential": "fake-token"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@patch("app.auth.GOOGLE_CLIENT_ID", "test-client-id")
@patch("app.auth.google_id_token.verify_oauth2_token")
def test_google_login_existing_google_user(mock_verify, client, db):
    """User with matching google_id signs in directly."""
    mock_verify.return_value = FAKE_GOOGLE_ID_INFO

    user = User(
        id=generate_id(),
        email="googleuser@gmail.com",
        name="Existing Google User",
        hashed_password=get_password_hash("random"),
        role="user",
        auth_provider="google",
        google_id="google-uid-12345",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()

    response = client.post("/auth/google", json={"credential": "fake-token"})
    assert response.status_code == 200
    assert "access_token" in response.json()


@patch("app.auth.GOOGLE_CLIENT_ID", "test-client-id")
@patch("app.auth.google_id_token.verify_oauth2_token")
def test_google_login_links_existing_email_user(mock_verify, client, db):
    """User with matching email but no google_id gets linked."""
    mock_verify.return_value = FAKE_GOOGLE_ID_INFO

    user = User(
        id=generate_id(),
        email="googleuser@gmail.com",
        name="Local User",
        hashed_password=get_password_hash("localpass123"),
        role="user",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()

    response = client.post("/auth/google", json={"credential": "fake-token"})
    assert response.status_code == 200

    # Verify the Google ID was linked
    db.refresh(user)
    assert user.google_id == "google-uid-12345"
    assert user.auth_provider == "google"


@patch("app.auth.GOOGLE_CLIENT_ID", "test-client-id")
@patch("app.auth.google_id_token.verify_oauth2_token")
def test_google_login_preserves_existing_auth_provider(mock_verify, client, db):
    """If user already has auth_provider set, don't overwrite it."""
    mock_verify.return_value = FAKE_GOOGLE_ID_INFO

    user = User(
        id=generate_id(),
        email="googleuser@gmail.com",
        name="Local User",
        hashed_password=get_password_hash("localpass123"),
        role="user",
        auth_provider="local",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()

    response = client.post("/auth/google", json={"credential": "fake-token"})
    assert response.status_code == 200

    db.refresh(user)
    assert user.google_id == "google-uid-12345"
    assert user.auth_provider == "local"  # Not overwritten


@patch("app.auth.GOOGLE_CLIENT_ID", "test-client-id")
@patch("app.auth.google_id_token.verify_oauth2_token")
def test_google_login_inactive_user(mock_verify, client, db):
    mock_verify.return_value = FAKE_GOOGLE_ID_INFO

    user = User(
        id=generate_id(),
        email="googleuser@gmail.com",
        name="Inactive Google User",
        hashed_password=get_password_hash("random"),
        role="user",
        auth_provider="google",
        google_id="google-uid-12345",
        is_active=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()

    response = client.post("/auth/google", json={"credential": "fake-token"})
    assert response.status_code == 403
    assert "inactive" in response.json()["detail"].lower()


@patch("app.auth.GOOGLE_CLIENT_ID", "test-client-id")
@patch("app.auth.google_id_token.verify_oauth2_token")
def test_google_login_invalid_token(mock_verify, client):
    mock_verify.side_effect = ValueError("Token expired")

    response = client.post("/auth/google", json={"credential": "expired-token"})
    assert response.status_code == 401
    assert "Invalid Google credential" in response.json()["detail"]


@patch("app.auth.GOOGLE_CLIENT_ID", "test-client-id")
@patch("app.auth.google_id_token.verify_oauth2_token")
def test_google_login_email_not_verified(mock_verify, client):
    mock_verify.return_value = {
        **FAKE_GOOGLE_ID_INFO,
        "email_verified": False,
    }

    response = client.post("/auth/google", json={"credential": "fake-token"})
    assert response.status_code == 401
    assert "Email not verified" in response.json()["detail"]


@patch("app.auth.GOOGLE_CLIENT_ID", "")
def test_google_login_not_configured(client):
    response = client.post("/auth/google", json={"credential": "fake-token"})
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_google_login_missing_credential(client):
    response = client.post("/auth/google", json={})
    assert response.status_code == 422


@patch("app.auth.GOOGLE_CLIENT_ID", "test-client-id")
@patch("app.auth.google_id_token.verify_oauth2_token")
def test_google_login_name_fallback(mock_verify, client, db):
    """When Google doesn't provide name, fallback to email prefix."""
    mock_verify.return_value = {
        "sub": "google-uid-noname",
        "email": "noname@gmail.com",
        "email_verified": True,
        "iss": "accounts.google.com",
    }

    response = client.post("/auth/google", json={"credential": "fake-token"})
    assert response.status_code == 200

    user = db.query(User).filter(User.email == "noname@gmail.com").first()
    assert user is not None
    assert user.name == "noname"

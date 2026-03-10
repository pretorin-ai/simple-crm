"""Tests for auth router endpoints."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from app.auth import create_password_reset_token, get_password_hash
from app.models.models import User
from app.utils import generate_id


def test_login_success(client, admin_user):
    response = client.post(
        "/auth/login",
        json={
            "email": "admin@test.com",
            "password": "adminpass123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, admin_user):
    response = client.post(
        "/auth/login",
        json={
            "email": "admin@test.com",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_login_nonexistent_user(client):
    response = client.post(
        "/auth/login",
        json={
            "email": "nobody@test.com",
            "password": "password123",
        },
    )
    assert response.status_code == 401


def test_login_inactive_user(client, inactive_user):
    response = client.post(
        "/auth/login",
        json={
            "email": "inactive@test.com",
            "password": "inactivepass123",
        },
    )
    assert response.status_code == 403
    assert "inactive" in response.json()["detail"].lower()


def test_register_admin_only(client, admin_headers):
    response = client.post(
        "/auth/register",
        json={
            "email": "newuser@test.com",
            "name": "New User",
            "password": "newpass12345",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert data["name"] == "New User"


def test_register_non_admin_forbidden(client, user_headers):
    response = client.post(
        "/auth/register",
        json={
            "email": "another@test.com",
            "name": "Another User",
            "password": "anotherpass123",
        },
        headers=user_headers,
    )
    assert response.status_code == 403


def test_register_duplicate_email(client, admin_headers, admin_user):
    response = client.post(
        "/auth/register",
        json={
            "email": "admin@test.com",
            "name": "Duplicate",
            "password": "password12345",
        },
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_register_short_password(client, admin_headers):
    response = client.post(
        "/auth/register",
        json={
            "email": "short@test.com",
            "name": "Short Pass",
            "password": "short",
        },
        headers=admin_headers,
    )
    assert response.status_code == 422  # Pydantic validates min_length on schema


def test_register_no_auth(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "noauth@test.com",
            "name": "No Auth",
            "password": "password12345",
        },
    )
    assert response.status_code == 401


def test_get_me(client, admin_headers, admin_user):
    response = client.get("/auth/me", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@test.com"
    assert data["name"] == "Admin User"


def test_get_me_no_auth(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_get_me_inactive_user(client, db):
    """An inactive user using a valid token should get 403 on /me."""
    user = User(
        id=generate_id(),
        email="inactive_me@test.com",
        name="Inactive Me",
        hashed_password=get_password_hash("password123"),
        role="user",
        is_active=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()

    from app.auth import create_access_token

    token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(minutes=30))
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_get_me_with_api_key(client, user_with_api_key):
    user, raw_key = user_with_api_key
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {raw_key}"})
    assert response.status_code == 200
    assert response.json()["email"] == "apiuser@test.com"


def test_get_me_invalid_api_key(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer crm_invalidkey123"})
    assert response.status_code == 401


def test_get_me_invalid_jwt(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer invalidjwttoken"})
    assert response.status_code == 401


@patch("app.routers.auth.send_password_reset_email", new_callable=AsyncMock)
def test_password_reset_request_existing_user(mock_email, client, admin_user):
    response = client.post(
        "/auth/password-reset-request",
        json={
            "email": "admin@test.com",
        },
    )
    assert response.status_code == 200
    assert "If the email exists" in response.json()["message"]
    mock_email.assert_called_once()


@patch("app.routers.auth.send_password_reset_email", new_callable=AsyncMock)
def test_password_reset_request_nonexistent_user(mock_email, client):
    response = client.post(
        "/auth/password-reset-request",
        json={
            "email": "nobody@test.com",
        },
    )
    assert response.status_code == 200
    assert "If the email exists" in response.json()["message"]
    mock_email.assert_not_called()


@patch("app.routers.auth.send_password_reset_email", new_callable=AsyncMock)
def test_password_reset_request_inactive_user(mock_email, client, inactive_user):
    response = client.post(
        "/auth/password-reset-request",
        json={
            "email": "inactive@test.com",
        },
    )
    assert response.status_code == 200
    mock_email.assert_not_called()


def test_password_reset_success(client, db, admin_user):
    token = create_password_reset_token(admin_user, db)
    response = client.post(
        "/auth/password-reset",
        json={
            "token": token,
            "new_password": "newpassword123",
        },
    )
    assert response.status_code == 200
    assert "successfully" in response.json()["message"]


def test_password_reset_invalid_token(client):
    response = client.post(
        "/auth/password-reset",
        json={
            "token": "invalidtoken",
            "new_password": "newpassword123",
        },
    )
    assert response.status_code == 400
    assert "Invalid or expired" in response.json()["detail"]


def test_password_reset_short_password(client, db, admin_user):
    token = create_password_reset_token(admin_user, db)
    response = client.post(
        "/auth/password-reset",
        json={
            "token": token,
            "new_password": "short",
        },
    )
    assert response.status_code == 422  # Pydantic validates min_length on schema


def test_password_change_success(client, admin_headers, admin_user):
    response = client.post(
        "/auth/password-change",
        json={
            "current_password": "adminpass123",
            "new_password": "newadminpass123",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert "successfully" in response.json()["message"]


def test_password_change_wrong_current(client, admin_headers):
    response = client.post(
        "/auth/password-change",
        json={
            "current_password": "wrongcurrent",
            "new_password": "newpassword123",
        },
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert "Incorrect current password" in response.json()["detail"]


def test_password_change_short_new_password(client, admin_headers):
    response = client.post(
        "/auth/password-change",
        json={
            "current_password": "adminpass123",
            "new_password": "short",
        },
        headers=admin_headers,
    )
    assert response.status_code == 422  # Pydantic validates min_length on schema


def test_password_change_no_auth(client):
    response = client.post(
        "/auth/password-change",
        json={
            "current_password": "whatever",
            "new_password": "newpassword123",
        },
    )
    assert response.status_code == 401


def test_get_current_user_no_sub_in_token(client):
    """Token with no 'sub' field should fail."""
    from app.auth import create_access_token

    token = create_access_token(data={}, expires_delta=timedelta(minutes=30))
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_get_current_user_nonexistent_email(client):
    """Token with email that doesn't exist in DB should fail."""
    from app.auth import create_access_token

    token = create_access_token(data={"sub": "ghost@test.com"}, expires_delta=timedelta(minutes=30))
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


# --- Token refresh endpoint tests ---


def test_refresh_token_success(client, admin_user):
    """Login returns a refresh token, and refresh endpoint returns new tokens."""
    login_resp = client.post(
        "/auth/login", json={"email": "admin@test.com", "password": "adminpass123"}
    )
    assert login_resp.status_code == 200
    refresh = login_resp.json()["refresh_token"]
    assert refresh is not None

    refresh_resp = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert refresh_resp.status_code == 200
    data = refresh_resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_refresh_token_invalid(client):
    """Invalid refresh token returns 401."""
    response = client.post("/auth/refresh", json={"refresh_token": "bad.token.value"})
    assert response.status_code == 401


def test_refresh_token_with_access_token(client, admin_user):
    """An access token should not work as a refresh token."""
    from app.auth import create_access_token

    access = create_access_token(
        data={"sub": "admin@test.com"}, expires_delta=timedelta(minutes=30)
    )
    response = client.post("/auth/refresh", json={"refresh_token": access})
    assert response.status_code == 401


def test_refresh_token_inactive_user(client, db, admin_user):
    """Refresh token for inactive user returns 401."""
    from app.auth import create_refresh_token

    refresh = create_refresh_token(data={"sub": admin_user.email})
    admin_user.is_active = False
    db.commit()

    response = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert response.status_code == 401


def test_refresh_token_nonexistent_user(client):
    """Refresh token for deleted user returns 401."""
    from app.auth import create_refresh_token

    refresh = create_refresh_token(data={"sub": "ghost@test.com"})
    response = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert response.status_code == 401

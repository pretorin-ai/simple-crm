"""Tests for user management and API key endpoints."""

from datetime import datetime, timezone

from app.auth import get_password_hash
from app.models.models import User
from app.utils import generate_id


def test_get_users(client, admin_headers, admin_user, regular_user):
    response = client.get("/users", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


def test_get_users_as_regular_user(client, user_headers, regular_user):
    response = client.get("/users", headers=user_headers)
    assert response.status_code == 200


def test_get_users_no_auth(client):
    response = client.get("/users")
    assert response.status_code == 401


def test_get_users_inactive_user(client, db):
    """Inactive user should be rejected by get_current_active_user."""
    from app.auth import create_access_token

    user = User(
        id=generate_id(),
        email="inactiveusers@test.com",
        name="Inactive Users",
        hashed_password=get_password_hash("password123"),
        role="user",
        is_active=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    from datetime import timedelta

    token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(minutes=30))
    response = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_get_user_by_id(client, admin_headers, regular_user):
    response = client.get(f"/users/{regular_user.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "user@test.com"


def test_get_user_not_found(client, admin_headers):
    response = client.get("/users/nonexistent-id", headers=admin_headers)
    assert response.status_code == 404


def test_create_user_admin_only(client, admin_headers):
    response = client.post(
        "/users",
        json={
            "email": "created@test.com",
            "name": "Created User",
            "password": "createdpass123",
            "role": "user",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "created@test.com"
    assert data["role"] == "user"


def test_create_user_as_admin_role(client, admin_headers):
    response = client.post(
        "/users",
        json={
            "email": "newadmin@test.com",
            "name": "New Admin",
            "password": "adminpass12345",
            "role": "admin",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_create_user_non_admin_forbidden(client, user_headers):
    response = client.post(
        "/users",
        json={
            "email": "forbidden@test.com",
            "name": "Forbidden",
            "password": "password12345",
            "role": "user",
        },
        headers=user_headers,
    )
    assert response.status_code == 403


def test_create_user_duplicate_email(client, admin_headers, regular_user):
    response = client.post(
        "/users",
        json={
            "email": "user@test.com",
            "name": "Duplicate",
            "password": "password12345",
            "role": "user",
        },
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_create_user_invalid_role(client, admin_headers):
    response = client.post(
        "/users",
        json={
            "email": "badrole@test.com",
            "name": "Bad Role",
            "password": "password12345",
            "role": "superadmin",
        },
        headers=admin_headers,
    )
    assert response.status_code == 422  # Pydantic Literal validation


def test_create_user_short_password(client, admin_headers):
    response = client.post(
        "/users",
        json={
            "email": "short@test.com",
            "name": "Short Pass",
            "password": "short",
            "role": "user",
        },
        headers=admin_headers,
    )
    assert response.status_code == 422  # Pydantic validates min_length on schema


def test_update_user(client, admin_headers, regular_user):
    response = client.put(
        f"/users/{regular_user.id}",
        json={
            "name": "Updated Name",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


def test_update_user_email(client, admin_headers, regular_user):
    response = client.put(
        f"/users/{regular_user.id}",
        json={
            "email": "newemail@test.com",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["email"] == "newemail@test.com"


def test_update_user_email_conflict(client, admin_headers, regular_user, admin_user):
    response = client.put(
        f"/users/{regular_user.id}",
        json={
            "email": "admin@test.com",
        },
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert "already in use" in response.json()["detail"]


def test_update_user_role(client, admin_headers, regular_user):
    response = client.put(
        f"/users/{regular_user.id}",
        json={
            "role": "admin",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_update_user_invalid_role(client, admin_headers, regular_user):
    response = client.put(
        f"/users/{regular_user.id}",
        json={
            "role": "superuser",
        },
        headers=admin_headers,
    )
    assert response.status_code == 422  # Pydantic Literal validation


def test_update_user_is_active(client, admin_headers, regular_user):
    response = client.put(
        f"/users/{regular_user.id}",
        json={
            "is_active": False,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_update_user_not_found(client, admin_headers):
    response = client.put(
        "/users/nonexistent-id",
        json={
            "name": "Nobody",
        },
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_update_user_non_admin(client, user_headers, admin_user):
    response = client.put(
        f"/users/{admin_user.id}",
        json={
            "name": "Hacked",
        },
        headers=user_headers,
    )
    assert response.status_code == 403


def test_delete_user(client, admin_headers, db):
    user = User(
        id=generate_id(),
        email="todelete@test.com",
        name="To Delete",
        hashed_password=get_password_hash("password123"),
        role="user",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()

    response = client.delete(f"/users/{user.id}", headers=admin_headers)
    assert response.status_code == 200
    assert "deleted" in response.json()["message"]


def test_delete_user_self(client, admin_headers, admin_user):
    response = client.delete(f"/users/{admin_user.id}", headers=admin_headers)
    assert response.status_code == 400
    assert "Cannot delete your own" in response.json()["detail"]


def test_delete_user_not_found(client, admin_headers):
    response = client.delete("/users/nonexistent-id", headers=admin_headers)
    assert response.status_code == 404


def test_delete_user_with_contacts(client, admin_headers, sample_contact_for_regular, regular_user):
    """Cannot delete user with assigned contacts."""
    response = client.delete(f"/users/{regular_user.id}", headers=admin_headers)
    assert response.status_code == 400
    assert "assigned contacts" in response.json()["detail"]


def test_delete_user_non_admin(client, user_headers, admin_user):
    response = client.delete(f"/users/{admin_user.id}", headers=user_headers)
    assert response.status_code == 403


# --- API Key tests ---


def test_generate_api_key(client, admin_headers):
    response = client.post("/users/me/api-key/generate", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "api_key" in data
    assert data["api_key"].startswith("crm_")
    assert "Store it securely" in data["message"]


def test_get_api_key_status_no_key(client, admin_headers):
    response = client.get("/users/me/api-key/status", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["has_api_key"] is False
    assert data["api_key_prefix"] is None


def test_get_api_key_status_with_key(client, admin_headers):
    # Generate a key first
    client.post("/users/me/api-key/generate", headers=admin_headers)

    response = client.get("/users/me/api-key/status", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["has_api_key"] is True
    assert data["api_key_prefix"] is not None
    assert data["api_key_prefix"].endswith("...")


def test_revoke_api_key(client, admin_headers):
    # Generate first
    client.post("/users/me/api-key/generate", headers=admin_headers)

    response = client.delete("/users/me/api-key", headers=admin_headers)
    assert response.status_code == 200
    assert "revoked" in response.json()["message"]


def test_revoke_api_key_when_none(client, admin_headers):
    response = client.delete("/users/me/api-key", headers=admin_headers)
    assert response.status_code == 404
    assert "No API key found" in response.json()["detail"]


def test_regenerate_api_key(client, admin_headers):
    # Generate first key
    resp1 = client.post("/users/me/api-key/generate", headers=admin_headers)
    key1 = resp1.json()["api_key"]

    # Generate second key (replaces first)
    resp2 = client.post("/users/me/api-key/generate", headers=admin_headers)
    key2 = resp2.json()["api_key"]

    assert key1 != key2


def test_api_key_auth_after_revoke(client, admin_headers):
    """After revoking, old API key should not work."""
    gen_resp = client.post("/users/me/api-key/generate", headers=admin_headers)
    api_key = gen_resp.json()["api_key"]

    # Revoke
    client.delete("/users/me/api-key", headers=admin_headers)

    # Try to use revoked key
    response = client.get("/contracts", headers={"Authorization": f"Bearer {api_key}"})
    assert response.status_code == 401

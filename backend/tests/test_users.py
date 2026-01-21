"""
Tests for user management endpoints.
"""
import pytest


class TestGetUsers:
    """Tests for GET /users endpoint."""

    def test_get_users_as_admin(self, client, admin_headers, admin_user):
        """Test admin can get list of users."""
        response = client.get("/users", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(u["email"] == admin_user.email for u in data)

    def test_get_users_as_regular_user(self, client, user_headers, regular_user):
        """Test regular user can get list of users."""
        response = client.get("/users", headers=user_headers)
        assert response.status_code == 200

    def test_get_users_without_auth_fails(self, client):
        """Test getting users without authentication fails."""
        response = client.get("/users")
        assert response.status_code == 401


class TestGetUser:
    """Tests for GET /users/{user_id} endpoint."""

    def test_get_user_by_id(self, client, admin_headers, admin_user):
        """Test getting a specific user by ID."""
        response = client.get(f"/users/{admin_user.id}", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == admin_user.id
        assert data["email"] == admin_user.email

    def test_get_nonexistent_user_returns_404(self, client, admin_headers):
        """Test getting non-existent user returns 404."""
        response = client.get("/users/nonexistent-id", headers=admin_headers)
        assert response.status_code == 404


class TestCreateUser:
    """Tests for POST /users endpoint (admin pre-provisioning)."""

    def test_admin_can_create_user(self, client, admin_headers):
        """Test admin can pre-provision a new user."""
        response = client.post(
            "/users",
            headers=admin_headers,
            json={
                "email": "newuser@test.com",
                "name": "New User",
                "role": "user"
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["name"] == "New User"
        assert data["role"] == "user"
        assert data["is_active"] is True

    def test_admin_can_create_admin_user(self, client, admin_headers):
        """Test admin can pre-provision a new admin user."""
        response = client.post(
            "/users",
            headers=admin_headers,
            json={
                "email": "newadmin@test.com",
                "name": "New Admin",
                "role": "admin"
            }
        )
        assert response.status_code == 200
        assert response.json()["role"] == "admin"

    def test_regular_user_cannot_create_user(self, client, user_headers):
        """Test regular user cannot create users."""
        response = client.post(
            "/users",
            headers=user_headers,
            json={
                "email": "unauthorized@test.com",
                "name": "Unauthorized",
                "role": "user"
            }
        )
        assert response.status_code == 403

    def test_cannot_create_duplicate_email(self, client, admin_headers, admin_user):
        """Test cannot create user with existing email."""
        response = client.post(
            "/users",
            headers=admin_headers,
            json={
                "email": admin_user.email,
                "name": "Duplicate",
                "role": "user"
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_create_user_with_invalid_role_fails(self, client, admin_headers):
        """Test creating user with invalid role fails."""
        response = client.post(
            "/users",
            headers=admin_headers,
            json={
                "email": "invalid@test.com",
                "name": "Invalid Role",
                "role": "superuser"  # Invalid role
            }
        )
        assert response.status_code == 400


class TestUpdateUser:
    """Tests for PUT /users/{user_id} endpoint."""

    def test_admin_can_update_user(self, client, admin_headers, regular_user):
        """Test admin can update a user."""
        response = client.put(
            f"/users/{regular_user.id}",
            headers=admin_headers,
            json={"name": "Updated Name"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    def test_admin_can_change_user_role(self, client, admin_headers, regular_user):
        """Test admin can change a user's role."""
        response = client.put(
            f"/users/{regular_user.id}",
            headers=admin_headers,
            json={"role": "admin"}
        )
        assert response.status_code == 200
        assert response.json()["role"] == "admin"

    def test_admin_can_deactivate_user(self, client, admin_headers, regular_user):
        """Test admin can deactivate a user."""
        response = client.put(
            f"/users/{regular_user.id}",
            headers=admin_headers,
            json={"is_active": False}
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_regular_user_cannot_update_others(self, client, user_headers, admin_user):
        """Test regular user cannot update other users."""
        response = client.put(
            f"/users/{admin_user.id}",
            headers=user_headers,
            json={"name": "Hacked"}
        )
        assert response.status_code == 403

    def test_update_nonexistent_user_returns_404(self, client, admin_headers):
        """Test updating non-existent user returns 404."""
        response = client.put(
            "/users/nonexistent-id",
            headers=admin_headers,
            json={"name": "Ghost"}
        )
        assert response.status_code == 404


class TestDeleteUser:
    """Tests for DELETE /users/{user_id} endpoint."""

    def test_admin_can_delete_user(self, client, admin_headers, regular_user):
        """Test admin can delete a user."""
        response = client.delete(
            f"/users/{regular_user.id}",
            headers=admin_headers
        )
        assert response.status_code == 200

        # Verify user is deleted
        get_response = client.get(f"/users/{regular_user.id}", headers=admin_headers)
        assert get_response.status_code == 404

    def test_admin_cannot_delete_self(self, client, admin_headers, admin_user):
        """Test admin cannot delete their own account."""
        response = client.delete(
            f"/users/{admin_user.id}",
            headers=admin_headers
        )
        assert response.status_code == 400
        assert "cannot delete your own" in response.json()["detail"].lower()

    def test_regular_user_cannot_delete_users(self, client, user_headers, admin_user):
        """Test regular user cannot delete users."""
        response = client.delete(
            f"/users/{admin_user.id}",
            headers=user_headers
        )
        assert response.status_code == 403


class TestApiKeyManagement:
    """Tests for API key management endpoints."""

    def test_generate_api_key(self, client, user_headers):
        """Test user can generate an API key."""
        response = client.post("/users/me/api-key/generate", headers=user_headers)
        assert response.status_code == 200

        data = response.json()
        assert "api_key" in data
        assert data["api_key"].startswith("crm_")
        assert "message" in data

    def test_get_api_key_status_without_key(self, client, user_headers):
        """Test getting API key status when no key exists."""
        response = client.get("/users/me/api-key/status", headers=user_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["has_api_key"] is False
        assert data["api_key_prefix"] is None

    def test_get_api_key_status_with_key(self, client, api_key_headers, user_with_api_key):
        """Test getting API key status when key exists."""
        # Use JWT token for this user instead of API key
        from app.auth import create_access_token
        from datetime import timedelta
        token = create_access_token(
            data={"sub": user_with_api_key.email},
            expires_delta=timedelta(minutes=30)
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/users/me/api-key/status", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["has_api_key"] is True
        assert data["api_key_prefix"] is not None
        assert "..." in data["api_key_prefix"]

    def test_revoke_api_key(self, client, user_with_api_key):
        """Test revoking an API key."""
        from app.auth import create_access_token
        from datetime import timedelta
        token = create_access_token(
            data={"sub": user_with_api_key.email},
            expires_delta=timedelta(minutes=30)
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = client.delete("/users/me/api-key", headers=headers)
        assert response.status_code == 200

        # Verify key is revoked
        status_response = client.get("/users/me/api-key/status", headers=headers)
        assert status_response.json()["has_api_key"] is False

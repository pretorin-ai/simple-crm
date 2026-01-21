"""
Tests for authentication endpoints.
"""
import pytest


class TestAuthMe:
    """Tests for /auth/me endpoint."""

    def test_get_current_user_with_valid_token(self, client, admin_headers, admin_user):
        """Test getting current user with valid JWT token."""
        response = client.get("/auth/me", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["email"] == admin_user.email
        assert data["name"] == admin_user.name
        assert data["role"] == "admin"
        assert data["is_active"] is True

    def test_get_current_user_with_api_key(self, client, api_key_headers, user_with_api_key):
        """Test getting current user with API key."""
        response = client.get("/auth/me", headers=api_key_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["email"] == user_with_api_key.email

    def test_get_current_user_without_token_fails(self, client):
        """Test that accessing /auth/me without token fails."""
        response = client.get("/auth/me")
        assert response.status_code == 401  # No credentials provided

    def test_get_current_user_with_invalid_token_fails(self, client):
        """Test that invalid token is rejected."""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 401

    def test_get_current_user_with_expired_token_fails(self, client, db, admin_user):
        """Test that expired token is rejected."""
        from datetime import timedelta
        from app.auth import create_access_token

        # Create an already-expired token
        expired_token = create_access_token(
            data={"sub": admin_user.email},
            expires_delta=timedelta(minutes=-5)  # Expired 5 minutes ago
        )
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 401

    def test_inactive_user_cannot_access(self, client, inactive_user_token):
        """Test that inactive user cannot access their profile."""
        headers = {"Authorization": f"Bearer {inactive_user_token}"}
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 403
        assert "inactive" in response.json()["detail"].lower()


class TestApiKeyAuth:
    """Tests for API key authentication."""

    def test_valid_api_key_authenticates(self, client, api_key_headers, user_with_api_key):
        """Test that valid API key authenticates successfully."""
        response = client.get("/auth/me", headers=api_key_headers)
        assert response.status_code == 200
        assert response.json()["email"] == user_with_api_key.email

    def test_invalid_api_key_fails(self, client):
        """Test that invalid API key is rejected."""
        headers = {"Authorization": "Bearer crm_invalidapikey123456"}
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 401

    def test_api_key_format_validation(self, client):
        """Test that non-crm_ prefixed keys are treated as JWT."""
        headers = {"Authorization": "Bearer some_random_key"}
        response = client.get("/auth/me", headers=headers)
        # Should fail JWT validation, not API key validation
        assert response.status_code == 401

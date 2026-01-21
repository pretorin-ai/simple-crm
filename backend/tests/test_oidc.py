"""
Tests for OIDC authentication endpoints.
"""
import pytest
import os

# Mock OIDC config for tests
os.environ["GOOGLE_CLIENT_ID"] = "test-client-id.apps.googleusercontent.com"
os.environ["GOOGLE_CLIENT_SECRET"] = "test-client-secret"
os.environ["GOOGLE_REDIRECT_URI"] = "http://localhost:8080/auth/callback"


class TestOIDCConfig:
    """Tests for /auth/oidc/config endpoint."""

    def test_get_oidc_config_returns_config(self, client):
        """Test that OIDC config endpoint returns configuration."""
        response = client.get("/auth/oidc/config")
        assert response.status_code == 200

        data = response.json()
        assert "client_id" in data
        assert "authorization_endpoint" in data
        assert "redirect_uri" in data
        assert "enabled" in data

    def test_oidc_config_contains_correct_values(self, client):
        """Test that OIDC config contains expected values."""
        response = client.get("/auth/oidc/config")
        data = response.json()

        assert data["client_id"] == "test-client-id.apps.googleusercontent.com"
        assert data["redirect_uri"] == "http://localhost:8080/auth/callback"
        assert data["enabled"] is True

    def test_oidc_config_authorization_endpoint_format(self, client):
        """Test that authorization endpoint has correct format."""
        response = client.get("/auth/oidc/config")
        data = response.json()

        assert "accounts.google.com" in data["authorization_endpoint"]
        assert "oauth2" in data["authorization_endpoint"]


class TestOIDCCallback:
    """Tests for /auth/oidc/callback endpoint."""

    def test_callback_requires_code(self, client):
        """Test that callback requires authorization code."""
        response = client.post(
            "/auth/oidc/callback",
            json={"code_verifier": "test-verifier"}
        )
        assert response.status_code == 422  # Validation error

    def test_callback_requires_code_verifier(self, client):
        """Test that callback requires code verifier."""
        response = client.post(
            "/auth/oidc/callback",
            json={"code": "test-code"}
        )
        assert response.status_code == 422  # Validation error

    def test_callback_with_invalid_code_fails(self, client):
        """Test that callback with invalid code fails."""
        response = client.post(
            "/auth/oidc/callback",
            json={
                "code": "invalid-code",
                "code_verifier": "test-verifier"
            }
        )
        # Should fail when trying to exchange code with Google
        assert response.status_code == 401

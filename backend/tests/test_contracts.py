"""
Tests for contracts endpoints.
"""
import pytest
from datetime import datetime, timedelta, UTC


class TestGetContracts:
    """Tests for GET /contracts endpoint."""

    def test_get_contracts(self, client, user_headers, sample_contract):
        """Test getting list of contracts."""
        response = client.get("/contracts", headers=user_headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(c["id"] == sample_contract.id for c in data)

    def test_get_contracts_without_auth_fails(self, client):
        """Test getting contracts without authentication fails."""
        response = client.get("/contracts")
        assert response.status_code == 401


class TestGetContract:
    """Tests for GET /contracts/{contract_id} endpoint."""

    def test_get_contract_by_id(self, client, user_headers, sample_contract):
        """Test getting a specific contract by ID."""
        response = client.get(f"/contracts/{sample_contract.id}", headers=user_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == sample_contract.id
        assert data["title"] == sample_contract.title

    def test_get_nonexistent_contract_returns_404(self, client, user_headers):
        """Test getting non-existent contract returns 404."""
        response = client.get("/contracts/nonexistent-id", headers=user_headers)
        assert response.status_code == 404


class TestCreateContract:
    """Tests for POST /contracts endpoint."""

    def test_create_contract(self, client, user_headers):
        """Test creating a new contract."""
        deadline = (datetime.now(UTC) + timedelta(days=30)).isoformat()
        response = client.post(
            "/contracts",
            headers=user_headers,
            json={
                "title": "New Contract",
                "description": "A new test contract",
                "source": "SAM.gov",
                "deadline": deadline,
                "status": "prospective",
                "notes": "Test notes",
                "assigned_contact_ids": []
            }
        )
        assert response.status_code == 201

        data = response.json()
        assert data["title"] == "New Contract"
        assert data["source"] == "SAM.gov"
        assert data["status"] == "prospective"
        assert "id" in data

    def test_create_contract_with_contacts(self, client, user_headers, sample_contact):
        """Test creating contract with assigned contacts."""
        deadline = (datetime.now(UTC) + timedelta(days=30)).isoformat()
        response = client.post(
            "/contracts",
            headers=user_headers,
            json={
                "title": "Contract with Contacts",
                "description": "Has assigned contacts",
                "source": "GSA eBuy",
                "deadline": deadline,
                "status": "in progress",
                "notes": "",
                "assigned_contact_ids": [sample_contact.id]
            }
        )
        assert response.status_code == 201

        data = response.json()
        assert sample_contact.id in data["assigned_contact_ids"]

    def test_create_contract_without_auth_fails(self, client):
        """Test creating contract without authentication fails."""
        deadline = (datetime.now(UTC) + timedelta(days=30)).isoformat()
        response = client.post(
            "/contracts",
            json={
                "title": "Unauthorized Contract",
                "description": "Should fail",
                "source": "Test",
                "deadline": deadline,
                "status": "prospective",
                "notes": "",
                "assigned_contact_ids": []
            }
        )
        assert response.status_code == 401


class TestUpdateContract:
    """Tests for PUT /contracts/{contract_id} endpoint."""

    def test_update_contract(self, client, user_headers, sample_contract):
        """Test updating a contract."""
        new_deadline = (datetime.now(UTC) + timedelta(days=60)).isoformat()
        response = client.put(
            f"/contracts/{sample_contract.id}",
            headers=user_headers,
            json={
                "title": "Updated Contract",
                "description": "Updated description",
                "source": sample_contract.source,
                "deadline": new_deadline,
                "status": "in progress",
                "notes": "Updated notes",
                "assigned_contact_ids": []
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert data["title"] == "Updated Contract"
        assert data["status"] == "in progress"

    def test_update_contract_status(self, client, user_headers, sample_contract):
        """Test updating contract status."""
        deadline = (datetime.now(UTC) + timedelta(days=30)).isoformat()
        response = client.put(
            f"/contracts/{sample_contract.id}",
            headers=user_headers,
            json={
                "title": sample_contract.title,
                "description": sample_contract.description,
                "source": sample_contract.source,
                "deadline": deadline,
                "status": "submitted",
                "notes": sample_contract.notes,
                "assigned_contact_ids": []
            }
        )
        assert response.status_code == 200
        assert response.json()["status"] == "submitted"

    def test_update_nonexistent_contract_returns_404(self, client, user_headers):
        """Test updating non-existent contract returns 404."""
        deadline = (datetime.now(UTC) + timedelta(days=30)).isoformat()
        response = client.put(
            "/contracts/nonexistent-id",
            headers=user_headers,
            json={
                "title": "Ghost Contract",
                "description": "",
                "source": "Test",
                "deadline": deadline,
                "status": "prospective",
                "notes": "",
                "assigned_contact_ids": []
            }
        )
        assert response.status_code == 404


class TestDeleteContract:
    """Tests for DELETE /contracts/{contract_id} endpoint."""

    def test_delete_contract(self, client, user_headers, sample_contract):
        """Test deleting a contract."""
        response = client.delete(
            f"/contracts/{sample_contract.id}",
            headers=user_headers
        )
        assert response.status_code == 204

        # Verify contract is deleted
        get_response = client.get(f"/contracts/{sample_contract.id}", headers=user_headers)
        assert get_response.status_code == 404

    def test_delete_nonexistent_contract_returns_404(self, client, user_headers):
        """Test deleting non-existent contract returns 404."""
        response = client.delete("/contracts/nonexistent-id", headers=user_headers)
        assert response.status_code == 404


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint returns healthy."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert "version" in data

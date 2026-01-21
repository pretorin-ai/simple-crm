"""
Tests for contacts endpoints.
"""
import pytest
from datetime import datetime, timedelta, UTC


class TestGetContacts:
    """Tests for GET /contacts endpoint."""

    def test_get_contacts_returns_user_contacts(self, client, user_headers, sample_contact):
        """Test getting contacts returns only user's contacts."""
        response = client.get("/contacts", headers=user_headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(c["id"] == sample_contact.id for c in data)

    def test_get_contacts_empty_for_new_user(self, client, admin_headers):
        """Test new user sees no contacts."""
        response = client.get("/contacts", headers=admin_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_get_contacts_without_auth_fails(self, client):
        """Test getting contacts without authentication fails."""
        response = client.get("/contacts")
        assert response.status_code == 401


class TestGetContact:
    """Tests for GET /contacts/{contact_id} endpoint."""

    def test_get_contact_by_id(self, client, user_headers, sample_contact):
        """Test getting a specific contact by ID."""
        response = client.get(f"/contacts/{sample_contact.id}", headers=user_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == sample_contact.id
        assert data["first_name"] == sample_contact.first_name
        assert data["email"] == sample_contact.email

    def test_get_contact_not_owned_returns_404(self, client, admin_headers, sample_contact):
        """Test cannot get contact owned by another user."""
        # Admin doesn't own the sample_contact (owned by regular_user)
        response = client.get(f"/contacts/{sample_contact.id}", headers=admin_headers)
        assert response.status_code == 404

    def test_get_nonexistent_contact_returns_404(self, client, user_headers):
        """Test getting non-existent contact returns 404."""
        response = client.get("/contacts/nonexistent-id", headers=user_headers)
        assert response.status_code == 404


class TestCreateContact:
    """Tests for POST /contacts endpoint."""

    def test_create_contact(self, client, user_headers):
        """Test creating a new contact."""
        response = client.post(
            "/contacts",
            headers=user_headers,
            json={
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane.smith@example.com",
                "phone": "555-5678",
                "organization": "Acme Inc",
                "contact_type": "commercial",
                "status": "cold",
                "notes": "New prospect"
            }
        )
        assert response.status_code == 201

        data = response.json()
        assert data["first_name"] == "Jane"
        assert data["last_name"] == "Smith"
        assert data["email"] == "jane.smith@example.com"
        assert data["status"] == "cold"
        assert "id" in data

    def test_create_contact_with_follow_up_date(self, client, user_headers):
        """Test creating contact with follow-up date."""
        follow_up = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        response = client.post(
            "/contacts",
            headers=user_headers,
            json={
                "first_name": "Follow",
                "last_name": "Up",
                "email": "followup@example.com",
                "phone": "555-9999",
                "organization": "Follow Corp",
                "contact_type": "government",
                "status": "warm",
                "follow_up_date": follow_up,
                "notes": ""
            }
        )
        assert response.status_code == 201
        assert response.json()["follow_up_date"] is not None

    def test_create_contact_without_auth_fails(self, client):
        """Test creating contact without authentication fails."""
        response = client.post(
            "/contacts",
            json={
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
                "phone": "555-0000",
                "organization": "Test",
                "contact_type": "individual",
                "status": "cold",
                "notes": ""
            }
        )
        assert response.status_code == 401


class TestUpdateContact:
    """Tests for PUT /contacts/{contact_id} endpoint."""

    def test_update_contact(self, client, user_headers, sample_contact, regular_user):
        """Test updating a contact."""
        response = client.put(
            f"/contacts/{sample_contact.id}",
            headers=user_headers,
            json={
                "first_name": "Updated",
                "last_name": "Name",
                "email": sample_contact.email,
                "phone": sample_contact.phone,
                "organization": sample_contact.organization,
                "contact_type": sample_contact.contact_type,
                "status": "hot",
                "notes": "Updated notes",
                "assigned_user_id": regular_user.id
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["status"] == "hot"
        assert data["notes"] == "Updated notes"

    def test_update_contact_not_owned_fails(self, client, admin_headers, sample_contact, admin_user):
        """Test cannot update contact owned by another user."""
        response = client.put(
            f"/contacts/{sample_contact.id}",
            headers=admin_headers,
            json={
                "first_name": "Hacked",
                "last_name": "Contact",
                "email": "hacked@example.com",
                "phone": "555-0000",
                "organization": "Hacked",
                "contact_type": "individual",
                "status": "cold",
                "notes": "",
                "assigned_user_id": admin_user.id
            }
        )
        assert response.status_code == 404


class TestDeleteContact:
    """Tests for DELETE /contacts/{contact_id} endpoint."""

    def test_delete_contact(self, client, user_headers, sample_contact):
        """Test deleting a contact."""
        response = client.delete(
            f"/contacts/{sample_contact.id}",
            headers=user_headers
        )
        assert response.status_code == 204

        # Verify contact is deleted
        get_response = client.get(f"/contacts/{sample_contact.id}", headers=user_headers)
        assert get_response.status_code == 404

    def test_delete_contact_not_owned_fails(self, client, admin_headers, sample_contact):
        """Test cannot delete contact owned by another user."""
        response = client.delete(
            f"/contacts/{sample_contact.id}",
            headers=admin_headers
        )
        assert response.status_code == 404


class TestFollowUps:
    """Tests for follow-up related endpoints."""

    def test_get_due_follow_ups(self, client, user_headers, db, regular_user):
        """Test getting contacts with due follow-ups."""
        from app.models.models import Contact
        from app.seed_data import generate_id

        # Create contact with follow-up due in 3 days
        contact = Contact(
            id=generate_id(),
            first_name="Due",
            last_name="Soon",
            email="due@example.com",
            phone="555-1111",
            organization="Due Corp",
            contact_type="commercial",
            status="warm",
            follow_up_date=datetime.now(UTC) + timedelta(days=3),
            notes="",
            assigned_user_id=regular_user.id,
        )
        db.add(contact)
        db.commit()

        response = client.get("/contacts/follow-ups/due?days_ahead=7", headers=user_headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert any(c["email"] == "due@example.com" for c in data)

    def test_get_overdue_follow_ups(self, client, user_headers, db, regular_user):
        """Test getting contacts with overdue follow-ups."""
        from app.models.models import Contact
        from app.seed_data import generate_id

        # Create contact with overdue follow-up
        contact = Contact(
            id=generate_id(),
            first_name="Overdue",
            last_name="Contact",
            email="overdue@example.com",
            phone="555-2222",
            organization="Late Corp",
            contact_type="commercial",
            status="warm",
            follow_up_date=datetime.now(UTC) - timedelta(days=2),
            notes="",
            assigned_user_id=regular_user.id,
        )
        db.add(contact)
        db.commit()

        response = client.get("/contacts/follow-ups/overdue", headers=user_headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert any(c["email"] == "overdue@example.com" for c in data)

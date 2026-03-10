"""Tests for contacts CRUD endpoints."""


def test_get_contacts_empty(client, admin_headers, admin_user):
    response = client.get("/contacts", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_contacts(client, admin_headers, sample_contact):
    response = client.get("/contacts", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["first_name"] == "John"
    assert data[0]["last_name"] == "Doe"


def test_get_contacts_only_own(client, user_headers, sample_contact, sample_contact_for_regular):
    """Regular user should only see their own contacts."""
    response = client.get("/contacts", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["first_name"] == "Jane"


def test_get_contact_by_id(client, admin_headers, sample_contact):
    response = client.get(f"/contacts/{sample_contact.id}", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "John"
    assert data["email"] == "john@example.com"


def test_get_contact_not_found(client, admin_headers):
    response = client.get("/contacts/nonexistent-id", headers=admin_headers)
    assert response.status_code == 404


def test_get_contact_wrong_user(client, user_headers, sample_contact):
    """User should not see contacts assigned to another user."""
    response = client.get(f"/contacts/{sample_contact.id}", headers=user_headers)
    assert response.status_code == 404


def test_create_contact(client, admin_headers, admin_user):
    response = client.post(
        "/contacts",
        json={
            "first_name": "New",
            "last_name": "Contact",
            "email": "new@example.com",
            "phone": "555-9999",
            "organization": "New Corp",
            "contact_type": "individual",
            "status": "cold",
            "needs_follow_up": False,
            "notes": "New contact note",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "New"
    assert data["assigned_user_id"] == admin_user.id


def test_create_contact_with_assigned_user(client, admin_headers, regular_user):
    response = client.post(
        "/contacts",
        json={
            "first_name": "Assigned",
            "last_name": "Contact",
            "email": "assigned@example.com",
            "phone": "555-0000",
            "organization": "Assign Corp",
            "contact_type": "commercial",
            "status": "warm",
            "needs_follow_up": True,
            "assigned_user_id": regular_user.id,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert response.json()["assigned_user_id"] == regular_user.id


def test_create_contact_with_follow_up_date(client, admin_headers, admin_user):
    response = client.post(
        "/contacts",
        json={
            "first_name": "Follow",
            "last_name": "Up",
            "email": "followup@example.com",
            "phone": "555-1111",
            "organization": "Follow Corp",
            "contact_type": "government",
            "status": "hot",
            "needs_follow_up": True,
            "follow_up_date": "2026-06-01T00:00:00",
            "notes": "Follow up needed",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert response.json()["follow_up_date"] is not None


def test_create_contact_no_auth(client):
    response = client.post(
        "/contacts",
        json={
            "first_name": "No",
            "last_name": "Auth",
            "email": "noauth@example.com",
            "phone": "555-0000",
            "organization": "No Auth Corp",
            "contact_type": "individual",
            "status": "cold",
        },
    )
    assert response.status_code == 401


def test_update_contact(client, admin_headers, sample_contact):
    response = client.put(
        f"/contacts/{sample_contact.id}",
        json={
            "first_name": "Updated",
            "last_name": "Name",
            "email": "updated@example.com",
            "phone": "555-0001",
            "organization": "Updated Corp",
            "contact_type": "commercial",
            "status": "hot",
            "needs_follow_up": True,
            "notes": "Updated notes",
            "assigned_user_id": sample_contact.assigned_user_id,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Updated"
    assert data["email"] == "updated@example.com"


def test_update_contact_with_last_contacted(client, admin_headers, sample_contact):
    response = client.put(
        f"/contacts/{sample_contact.id}",
        json={
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone": "555-1234",
            "organization": "Test Corp",
            "contact_type": "individual",
            "status": "warm",
            "needs_follow_up": False,
            "notes": "Test contact",
            "assigned_user_id": sample_contact.assigned_user_id,
            "last_contacted_at": "2026-03-01T12:00:00",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["last_contacted_at"] is not None


def test_update_contact_not_found(client, admin_headers):
    response = client.put(
        "/contacts/nonexistent-id",
        json={
            "first_name": "X",
            "last_name": "Y",
            "email": "x@example.com",
            "phone": "555-0000",
            "organization": "X Corp",
            "contact_type": "individual",
            "status": "cold",
            "needs_follow_up": False,
            "assigned_user_id": "someid",
        },
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_update_contact_wrong_user(client, user_headers, sample_contact):
    response = client.put(
        f"/contacts/{sample_contact.id}",
        json={
            "first_name": "Hack",
            "last_name": "Attempt",
            "email": "hack@example.com",
            "phone": "555-0000",
            "organization": "Hack Corp",
            "contact_type": "individual",
            "status": "cold",
            "needs_follow_up": False,
            "assigned_user_id": sample_contact.assigned_user_id,
        },
        headers=user_headers,
    )
    assert response.status_code == 404


def test_delete_contact(client, admin_headers, sample_contact):
    response = client.delete(f"/contacts/{sample_contact.id}", headers=admin_headers)
    assert response.status_code == 204

    # Verify deleted
    response = client.get(f"/contacts/{sample_contact.id}", headers=admin_headers)
    assert response.status_code == 404


def test_delete_contact_not_found(client, admin_headers):
    response = client.delete("/contacts/nonexistent-id", headers=admin_headers)
    assert response.status_code == 404


def test_delete_contact_wrong_user(client, user_headers, sample_contact):
    response = client.delete(f"/contacts/{sample_contact.id}", headers=user_headers)
    assert response.status_code == 404


def test_patch_contact(client, admin_headers, sample_contact):
    """Partially update a contact via PATCH."""
    response = client.patch(
        f"/contacts/{sample_contact.id}",
        json={"first_name": "Patched"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Patched"
    assert data["last_name"] == "Doe"  # unchanged


def test_patch_contact_multiple_fields(client, admin_headers, sample_contact):
    """PATCH multiple fields at once."""
    response = client.patch(
        f"/contacts/{sample_contact.id}",
        json={"status": "hot", "needs_follow_up": True, "notes": "Updated via patch"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "hot"
    assert data["needs_follow_up"] is True
    assert data["notes"] == "Updated via patch"


def test_patch_contact_not_found(client, admin_headers):
    """PATCH a nonexistent contact returns 404."""
    response = client.patch(
        "/contacts/nonexistent-id",
        json={"first_name": "Ghost"},
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_patch_contact_wrong_user(client, user_headers, sample_contact):
    """Regular user cannot PATCH another user's contact."""
    response = client.patch(
        f"/contacts/{sample_contact.id}",
        json={"first_name": "Hacked"},
        headers=user_headers,
    )
    assert response.status_code == 404


def test_contacts_invalid_jwt(client):
    """Invalid JWT on a get_current_user endpoint should return 401."""
    response = client.get("/contacts", headers={"Authorization": "Bearer badjwt"})
    assert response.status_code == 401


def test_contacts_nonexistent_user_jwt(client):
    """JWT with email not in DB should return 401."""
    from datetime import timedelta

    from app.auth import create_access_token

    token = create_access_token(data={"sub": "ghost@test.com"}, expires_delta=timedelta(minutes=30))
    response = client.get("/contacts", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_contacts_jwt_no_sub(client):
    """JWT with no sub claim should return 401."""
    from datetime import timedelta

    from app.auth import create_access_token

    token = create_access_token(data={}, expires_delta=timedelta(minutes=30))
    response = client.get("/contacts", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401

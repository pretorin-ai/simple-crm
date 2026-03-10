"""Tests for communications CRUD endpoints."""


def test_get_communications_empty(client, admin_headers, admin_user):
    response = client.get("/communications", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_communications(client, admin_headers, sample_communication):
    response = client.get("/communications", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["type"] == "email"


def test_get_communications_filtered_by_contact(
    client, admin_headers, sample_contact, sample_communication
):
    response = client.get(
        f"/communications?contact_id={sample_contact.id}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["contact_id"] == sample_contact.id


def test_get_communications_wrong_contact_filter(client, admin_headers, sample_communication):
    response = client.get(
        "/communications?contact_id=nonexistent-id",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json() == []


def test_get_communication_by_id(client, admin_headers, sample_communication):
    response = client.get(
        f"/communications/{sample_communication.id}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "email"
    assert data["notes"] == "Test communication"


def test_get_communication_not_found(client, admin_headers):
    response = client.get("/communications/nonexistent-id", headers=admin_headers)
    assert response.status_code == 404


def test_get_communication_wrong_user(client, user_headers, sample_communication):
    """Regular user should not see communications for admin's contacts."""
    response = client.get(
        f"/communications/{sample_communication.id}",
        headers=user_headers,
    )
    assert response.status_code == 404


def test_create_communication(client, admin_headers, sample_contact):
    response = client.post(
        "/communications",
        json={
            "contact_id": sample_contact.id,
            "date": "2026-03-01T10:00:00",
            "type": "phone",
            "notes": "Discussed project timeline",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "phone"
    assert data["contact_id"] == sample_contact.id


def test_create_communication_updates_last_contacted(client, admin_headers, sample_contact):
    client.post(
        "/communications",
        json={
            "contact_id": sample_contact.id,
            "date": "2026-03-01T10:00:00",
            "type": "meeting",
            "notes": "Meeting notes",
        },
        headers=admin_headers,
    )

    # Check that last_contacted_at was updated
    response = client.get(f"/contacts/{sample_contact.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["last_contacted_at"] is not None


def test_create_communication_contact_not_found(client, admin_headers):
    response = client.post(
        "/communications",
        json={
            "contact_id": "nonexistent-id",
            "date": "2026-03-01T10:00:00",
            "type": "email",
            "notes": "Test",
        },
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_create_communication_wrong_user_contact(client, user_headers, sample_contact):
    """Regular user cannot create communication for admin's contact."""
    response = client.post(
        "/communications",
        json={
            "contact_id": sample_contact.id,
            "date": "2026-03-01T10:00:00",
            "type": "email",
            "notes": "Unauthorized",
        },
        headers=user_headers,
    )
    assert response.status_code == 404


def test_delete_communication(client, admin_headers, sample_communication):
    response = client.delete(
        f"/communications/{sample_communication.id}",
        headers=admin_headers,
    )
    assert response.status_code == 204

    # Verify deleted
    response = client.get(
        f"/communications/{sample_communication.id}",
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_delete_communication_not_found(client, admin_headers):
    response = client.delete("/communications/nonexistent-id", headers=admin_headers)
    assert response.status_code == 404


def test_delete_communication_wrong_user(client, user_headers, sample_communication):
    response = client.delete(
        f"/communications/{sample_communication.id}",
        headers=user_headers,
    )
    assert response.status_code == 404


def test_create_communication_no_auth(client, sample_contact):
    response = client.post(
        "/communications",
        json={
            "contact_id": sample_contact.id,
            "date": "2026-03-01T10:00:00",
            "type": "email",
            "notes": "Test",
        },
    )
    assert response.status_code == 401

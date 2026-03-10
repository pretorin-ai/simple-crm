"""Tests for contract vehicles CRUD endpoints."""

from app.models.models import ContractVehicle
from app.utils import generate_id


def _make_vehicle(db, **overrides):
    defaults = {"id": generate_id(), "name": "Test Vehicle", "notes": ""}
    defaults.update(overrides)
    v = ContractVehicle(**defaults)
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def test_get_vehicles_empty(client, admin_headers, admin_user):
    response = client.get("/vehicles", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_vehicles(client, admin_headers, db, admin_user):
    _make_vehicle(db)
    response = client.get("/vehicles", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_vehicle_by_id(client, admin_headers, db, admin_user):
    v = _make_vehicle(db, name="OASIS")
    response = client.get(f"/vehicles/{v.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "OASIS"


def test_get_vehicle_not_found(client, admin_headers, admin_user):
    response = client.get("/vehicles/nonexistent", headers=admin_headers)
    assert response.status_code == 404


def test_create_vehicle(client, admin_headers, admin_user):
    response = client.post(
        "/vehicles",
        json={
            "name": "GSA MAS",
            "agency": "GSA",
            "contract_number": "GS-35F-0001A",
            "ceiling_value": 500000000,
            "prime_or_sub": "prime",
            "notes": "IT Schedule",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "GSA MAS"
    assert data["prime_or_sub"] == "prime"


def test_update_vehicle(client, admin_headers, db, admin_user):
    v = _make_vehicle(db)
    response = client.put(
        f"/vehicles/{v.id}",
        json={
            "name": "Updated Vehicle",
            "agency": "Navy",
            "notes": "Updated",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Vehicle"


def test_update_vehicle_not_found(client, admin_headers, admin_user):
    response = client.put(
        "/vehicles/nonexistent",
        json={"name": "X", "notes": ""},
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_patch_vehicle(client, admin_headers, db, admin_user):
    v = _make_vehicle(db, name="Original")
    response = client.patch(
        f"/vehicles/{v.id}",
        json={"name": "Patched"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Patched"


def test_patch_vehicle_not_found(client, admin_headers, admin_user):
    response = client.patch(
        "/vehicles/nonexistent",
        json={"name": "Ghost"},
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_delete_vehicle(client, admin_headers, db, admin_user):
    v = _make_vehicle(db)
    response = client.delete(f"/vehicles/{v.id}", headers=admin_headers)
    assert response.status_code == 204

    response = client.get(f"/vehicles/{v.id}", headers=admin_headers)
    assert response.status_code == 404


def test_delete_vehicle_not_found(client, admin_headers, admin_user):
    response = client.delete("/vehicles/nonexistent", headers=admin_headers)
    assert response.status_code == 404


# --- Authorization ---


def test_update_vehicle_forbidden_for_non_creator(
    client, user_headers, db, admin_user, regular_user
):
    v = _make_vehicle(db, created_by_user_id=admin_user.id)
    response = client.put(
        f"/vehicles/{v.id}",
        json={"name": "Hacked", "notes": ""},
        headers=user_headers,
    )
    assert response.status_code == 403


def test_patch_vehicle_forbidden_for_non_creator(
    client, user_headers, db, admin_user, regular_user
):
    v = _make_vehicle(db, created_by_user_id=admin_user.id)
    response = client.patch(
        f"/vehicles/{v.id}",
        json={"name": "Hacked"},
        headers=user_headers,
    )
    assert response.status_code == 403


def test_delete_vehicle_forbidden_for_non_creator(
    client, user_headers, db, admin_user, regular_user
):
    v = _make_vehicle(db, created_by_user_id=admin_user.id)
    response = client.delete(f"/vehicles/{v.id}", headers=user_headers)
    assert response.status_code == 403

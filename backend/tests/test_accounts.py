"""Tests for accounts CRUD endpoints."""

from app.models.models import Account
from app.utils import generate_id


def _make_account(db, **overrides):
    defaults = {
        "id": generate_id(),
        "name": "Test Agency",
        "account_type": "government_agency",
        "notes": "",
    }
    defaults.update(overrides)
    account = Account(**defaults)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


# --- GET ---


def test_get_accounts_empty(client, admin_headers, admin_user):
    response = client.get("/accounts", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_accounts(client, admin_headers, db, admin_user):
    _make_account(db)
    response = client.get("/accounts", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_accounts_filter_by_type(client, admin_headers, db, admin_user):
    _make_account(db, account_type="government_agency")
    _make_account(db, name="Prime Co", account_type="prime_contractor")
    response = client.get("/accounts?account_type=prime_contractor", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["account_type"] == "prime_contractor"


def test_get_account_by_id(client, admin_headers, db, admin_user):
    acct = _make_account(db)
    response = client.get(f"/accounts/{acct.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Test Agency"


def test_get_account_not_found(client, admin_headers, admin_user):
    response = client.get("/accounts/nonexistent", headers=admin_headers)
    assert response.status_code == 404


# --- POST ---


def test_create_account(client, admin_headers, admin_user):
    response = client.post(
        "/accounts",
        json={
            "name": "New Agency",
            "account_type": "government_agency",
            "parent_agency": "DoD",
            "office": "CIO",
            "location": "DC",
            "website": "https://example.gov",
            "notes": "Test notes",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Agency"
    assert data["account_type"] == "government_agency"
    assert data["parent_agency"] == "DoD"


# --- PUT ---


def test_update_account(client, admin_headers, db, admin_user):
    acct = _make_account(db)
    response = client.put(
        f"/accounts/{acct.id}",
        json={
            "name": "Updated Agency",
            "account_type": "prime_contractor",
            "notes": "Updated",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Agency"
    assert data["account_type"] == "prime_contractor"


def test_update_account_not_found(client, admin_headers, admin_user):
    response = client.put(
        "/accounts/nonexistent",
        json={"name": "X", "account_type": "vendor", "notes": ""},
        headers=admin_headers,
    )
    assert response.status_code == 404


# --- PATCH ---


def test_patch_account(client, admin_headers, db, admin_user):
    acct = _make_account(db, name="Original")
    response = client.patch(
        f"/accounts/{acct.id}",
        json={"name": "Patched"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Patched"


def test_patch_account_not_found(client, admin_headers, admin_user):
    response = client.patch(
        "/accounts/nonexistent",
        json={"name": "Ghost"},
        headers=admin_headers,
    )
    assert response.status_code == 404


# --- DELETE ---


def test_delete_account(client, admin_headers, db, admin_user):
    acct = _make_account(db)
    response = client.delete(f"/accounts/{acct.id}", headers=admin_headers)
    assert response.status_code == 204

    response = client.get(f"/accounts/{acct.id}", headers=admin_headers)
    assert response.status_code == 404


def test_delete_account_not_found(client, admin_headers, admin_user):
    response = client.delete("/accounts/nonexistent", headers=admin_headers)
    assert response.status_code == 404


# --- Authorization (creator/admin only for mutations) ---


def test_update_account_forbidden_for_non_creator(
    client, admin_headers, user_headers, db, admin_user, regular_user
):
    acct = _make_account(db, created_by_user_id=admin_user.id)
    response = client.put(
        f"/accounts/{acct.id}",
        json={"name": "Hacked", "account_type": "vendor", "notes": ""},
        headers=user_headers,
    )
    assert response.status_code == 403


def test_patch_account_forbidden_for_non_creator(
    client, user_headers, db, admin_user, regular_user
):
    acct = _make_account(db, created_by_user_id=admin_user.id)
    response = client.patch(
        f"/accounts/{acct.id}",
        json={"name": "Hacked"},
        headers=user_headers,
    )
    assert response.status_code == 403


def test_delete_account_forbidden_for_non_creator(
    client, user_headers, db, admin_user, regular_user
):
    acct = _make_account(db, created_by_user_id=admin_user.id)
    response = client.delete(f"/accounts/{acct.id}", headers=user_headers)
    assert response.status_code == 403


def test_admin_can_modify_any_account(client, admin_headers, db, admin_user, regular_user):
    acct = _make_account(db, created_by_user_id=regular_user.id)
    response = client.patch(
        f"/accounts/{acct.id}",
        json={"name": "Admin Override"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Admin Override"

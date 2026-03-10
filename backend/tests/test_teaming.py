"""Tests for teaming CRUD endpoints."""

from app.models.models import Account, Opportunity, Teaming
from app.utils import generate_id


def _make_account(db, **overrides):
    defaults = {
        "id": generate_id(),
        "name": "Partner Co",
        "account_type": "prime_contractor",
        "notes": "",
    }
    defaults.update(overrides)
    a = Account(**defaults)
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _make_opportunity(db, user_id, **overrides):
    defaults = {
        "id": generate_id(),
        "title": "Test Opp",
        "stage": "teaming",
        "notes": "",
        "capture_manager_id": user_id,
        "created_by_user_id": user_id,
    }
    defaults.update(overrides)
    opp = Opportunity(**defaults)
    db.add(opp)
    db.commit()
    db.refresh(opp)
    return opp


def _make_teaming(db, opp_id, acct_id, **overrides):
    defaults = {
        "id": generate_id(),
        "opportunity_id": opp_id,
        "partner_account_id": acct_id,
        "role": "subcontractor",
        "status": "potential",
        "notes": "",
    }
    defaults.update(overrides)
    t = Teaming(**defaults)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def test_get_teaming_empty(client, admin_headers, admin_user):
    response = client.get("/teaming", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_teaming(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    acct = _make_account(db)
    _make_teaming(db, opp.id, acct.id)
    response = client.get("/teaming", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["partner_account"]["name"] == "Partner Co"


def test_get_teaming_filter_by_opportunity(client, admin_headers, db, admin_user):
    opp1 = _make_opportunity(db, admin_user.id)
    opp2 = _make_opportunity(db, admin_user.id, title="Other Opp")
    acct = _make_account(db)
    _make_teaming(db, opp1.id, acct.id)
    _make_teaming(db, opp2.id, acct.id, role="prime")
    response = client.get(f"/teaming?opportunity_id={opp1.id}", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_teaming_by_id(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    acct = _make_account(db)
    t = _make_teaming(db, opp.id, acct.id)
    response = client.get(f"/teaming/{t.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["role"] == "subcontractor"


def test_get_teaming_not_found(client, admin_headers, admin_user):
    response = client.get("/teaming/nonexistent", headers=admin_headers)
    assert response.status_code == 404


def test_create_teaming(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    acct = _make_account(db)
    response = client.post(
        "/teaming",
        json={
            "opportunity_id": opp.id,
            "partner_account_id": acct.id,
            "role": "prime",
            "status": "nda_signed",
            "notes": "Key partner",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "prime"
    assert data["status"] == "nda_signed"


def test_update_teaming(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    acct = _make_account(db)
    t = _make_teaming(db, opp.id, acct.id)
    response = client.put(
        f"/teaming/{t.id}",
        json={
            "opportunity_id": opp.id,
            "partner_account_id": acct.id,
            "role": "jv_partner",
            "status": "teaming_agreed",
            "notes": "Updated",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "jv_partner"
    assert data["status"] == "teaming_agreed"


def test_update_teaming_not_found(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    acct = _make_account(db)
    response = client.put(
        "/teaming/nonexistent",
        json={
            "opportunity_id": opp.id,
            "partner_account_id": acct.id,
            "role": "prime",
            "status": "potential",
            "notes": "",
        },
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_patch_teaming(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    acct = _make_account(db)
    t = _make_teaming(db, opp.id, acct.id)
    response = client.patch(
        f"/teaming/{t.id}",
        json={"status": "active"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_patch_teaming_not_found(client, admin_headers, admin_user):
    response = client.patch(
        "/teaming/nonexistent",
        json={"status": "inactive"},
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_delete_teaming(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    acct = _make_account(db)
    t = _make_teaming(db, opp.id, acct.id)
    response = client.delete(f"/teaming/{t.id}", headers=admin_headers)
    assert response.status_code == 204

    response = client.get(f"/teaming/{t.id}", headers=admin_headers)
    assert response.status_code == 404


def test_delete_teaming_not_found(client, admin_headers, admin_user):
    response = client.delete("/teaming/nonexistent", headers=admin_headers)
    assert response.status_code == 404


# --- Authorization ---


def test_update_teaming_forbidden_for_non_opp_creator(
    client, user_headers, db, admin_user, regular_user
):
    opp = _make_opportunity(db, admin_user.id)
    acct = _make_account(db)
    t = _make_teaming(db, opp.id, acct.id)
    response = client.put(
        f"/teaming/{t.id}",
        json={
            "opportunity_id": opp.id,
            "partner_account_id": acct.id,
            "role": "prime",
            "status": "active",
            "notes": "",
        },
        headers=user_headers,
    )
    assert response.status_code == 403


def test_patch_teaming_forbidden_for_non_opp_creator(
    client, user_headers, db, admin_user, regular_user
):
    opp = _make_opportunity(db, admin_user.id)
    acct = _make_account(db)
    t = _make_teaming(db, opp.id, acct.id)
    response = client.patch(
        f"/teaming/{t.id}",
        json={"status": "active"},
        headers=user_headers,
    )
    assert response.status_code == 403


def test_delete_teaming_forbidden_for_non_opp_creator(
    client, user_headers, db, admin_user, regular_user
):
    opp = _make_opportunity(db, admin_user.id)
    acct = _make_account(db)
    t = _make_teaming(db, opp.id, acct.id)
    response = client.delete(f"/teaming/{t.id}", headers=user_headers)
    assert response.status_code == 403


def test_opp_creator_can_modify_teaming(client, user_headers, db, admin_user, regular_user):
    opp = _make_opportunity(db, regular_user.id)
    acct = _make_account(db)
    t = _make_teaming(db, opp.id, acct.id)
    response = client.patch(
        f"/teaming/{t.id}",
        json={"status": "active"},
        headers=user_headers,
    )
    assert response.status_code == 200

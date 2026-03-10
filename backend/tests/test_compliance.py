"""Tests for compliance CRUD and expiring certifications endpoints."""

from datetime import datetime, timedelta, timezone

from freezegun import freeze_time

from app.auth import create_access_token
from app.models.models import Compliance
from app.utils import generate_id


def _make_compliance(db, **overrides):
    defaults = {
        "id": generate_id(),
        "certification_type": "small_business",
        "issued_by": "SBA",
        "status": "active",
        "notes": "",
    }
    defaults.update(overrides)
    c = Compliance(**defaults)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _frozen_headers(user):
    """Create auth headers valid at the frozen time."""
    token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def test_get_compliance_empty(client, admin_headers, admin_user):
    response = client.get("/compliance", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_compliance(client, admin_headers, db, admin_user):
    _make_compliance(db)
    response = client.get("/compliance", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_compliance_filter_by_status(client, admin_headers, db, admin_user):
    _make_compliance(db, status="active")
    _make_compliance(db, certification_type="8a", status="expired")
    response = client.get("/compliance?status=expired", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "expired"


def test_get_compliance_by_id(client, admin_headers, db, admin_user):
    c = _make_compliance(db, certification_type="hubzone")
    response = client.get(f"/compliance/{c.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["certification_type"] == "hubzone"


def test_get_compliance_not_found(client, admin_headers, admin_user):
    response = client.get("/compliance/nonexistent", headers=admin_headers)
    assert response.status_code == 404


def test_get_expiring_certifications(client, db, admin_user):
    with freeze_time("2026-06-15T12:00:00Z"):
        headers = _frozen_headers(admin_user)
        frozen_now = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        # Expiring in 30 days (within default 90 day window)
        _make_compliance(
            db,
            expiration_date=frozen_now + timedelta(days=30),
            status="expiring_soon",
        )
        # Expiring in 200 days (outside default window)
        _make_compliance(
            db,
            certification_type="8a",
            expiration_date=frozen_now + timedelta(days=200),
            status="active",
        )
        # Already expired (should not appear)
        _make_compliance(
            db,
            certification_type="wosb",
            expiration_date=frozen_now - timedelta(days=10),
            status="expired",
        )
        response = client.get("/compliance/expiring", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "expiring_soon"


def test_get_expiring_certifications_custom_days(client, db, admin_user):
    with freeze_time("2026-06-15T12:00:00Z"):
        headers = _frozen_headers(admin_user)
        frozen_now = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        _make_compliance(db, expiration_date=frozen_now + timedelta(days=30))
        response = client.get("/compliance/expiring?days_ahead=10", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 0  # 30 days out, but window is only 10


def test_create_compliance(client, admin_headers, admin_user):
    response = client.post(
        "/compliance",
        json={
            "certification_type": "8a",
            "issued_by": "U.S. Small Business Administration",
            "issue_date": "2025-01-01T00:00:00",
            "expiration_date": "2028-01-01T00:00:00",
            "status": "active",
            "notes": "8(a) certification",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["certification_type"] == "8a"
    assert data["issued_by"] == "U.S. Small Business Administration"


def test_update_compliance(client, admin_headers, db, admin_user):
    c = _make_compliance(db)
    response = client.put(
        f"/compliance/{c.id}",
        json={
            "certification_type": "wosb",
            "issued_by": "SBA",
            "status": "expiring_soon",
            "notes": "Renewal needed",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["certification_type"] == "wosb"
    assert data["status"] == "expiring_soon"


def test_update_compliance_not_found(client, admin_headers, admin_user):
    response = client.put(
        "/compliance/nonexistent",
        json={
            "certification_type": "small_business",
            "status": "active",
            "notes": "",
        },
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_patch_compliance(client, admin_headers, db, admin_user):
    c = _make_compliance(db)
    response = client.patch(
        f"/compliance/{c.id}",
        json={"status": "expired"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "expired"


def test_patch_compliance_not_found(client, admin_headers, admin_user):
    response = client.patch(
        "/compliance/nonexistent",
        json={"status": "pending"},
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_delete_compliance(client, admin_headers, db, admin_user):
    c = _make_compliance(db)
    response = client.delete(f"/compliance/{c.id}", headers=admin_headers)
    assert response.status_code == 204

    response = client.get(f"/compliance/{c.id}", headers=admin_headers)
    assert response.status_code == 404


def test_delete_compliance_not_found(client, admin_headers, admin_user):
    response = client.delete("/compliance/nonexistent", headers=admin_headers)
    assert response.status_code == 404


# --- Authorization ---


def test_update_compliance_forbidden_for_non_creator(
    client, user_headers, db, admin_user, regular_user
):
    c = _make_compliance(db, created_by_user_id=admin_user.id)
    response = client.put(
        f"/compliance/{c.id}",
        json={
            "certification_type": "small_business",
            "status": "active",
            "notes": "",
        },
        headers=user_headers,
    )
    assert response.status_code == 403


def test_patch_compliance_forbidden_for_non_creator(
    client, user_headers, db, admin_user, regular_user
):
    c = _make_compliance(db, created_by_user_id=admin_user.id)
    response = client.patch(
        f"/compliance/{c.id}",
        json={"status": "expired"},
        headers=user_headers,
    )
    assert response.status_code == 403


def test_delete_compliance_forbidden_for_non_creator(
    client, user_headers, db, admin_user, regular_user
):
    c = _make_compliance(db, created_by_user_id=admin_user.id)
    response = client.delete(f"/compliance/{c.id}", headers=user_headers)
    assert response.status_code == 403

"""Tests for audit log endpoints and audit trail creation."""

from datetime import datetime, timedelta, timezone

from app.models.models import Account, AuditLog, Contact, Contract, Opportunity
from app.routers.audit import create_audit_entry
from app.utils import generate_id


def _make_opportunity(db, user_id, **overrides):
    defaults = {
        "id": generate_id(),
        "title": "Audit Test Opp",
        "stage": "identified",
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


def _make_account(db, **overrides):
    defaults = {
        "id": generate_id(),
        "name": "Audit Test Account",
        "account_type": "partner",
        "notes": "",
    }
    defaults.update(overrides)
    a = Account(**defaults)
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _make_contact(db, user_id, **overrides):
    defaults = {
        "id": generate_id(),
        "first_name": "Audit",
        "last_name": "Contact",
        "email": f"audit-{generate_id()[:8]}@example.com",
        "phone": "555-0000",
        "organization": "Test Corp",
        "contact_type": "individual",
        "status": "warm",
        "assigned_user_id": user_id,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    c = Contact(**defaults)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _make_contract(db, user_id=None, **overrides):
    defaults = {
        "id": generate_id(),
        "title": "Audit Test Contract",
        "description": "Test",
        "source": "SAM.gov",
        "deadline": datetime.now(timezone.utc) + timedelta(days=30),
        "status": "prospective",
        "notes": "",
        "created_by_user_id": user_id,
    }
    defaults.update(overrides)
    c = Contract(**defaults)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# --- Audit log endpoint ---


def test_get_audit_log_empty(client, admin_headers, admin_user):
    response = client.get("/audit-log", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_audit_log_with_entries(client, admin_headers, db, admin_user):
    create_audit_entry(
        db,
        user_id=admin_user.id,
        action="delete",
        entity_type="opportunity",
        entity_id="opp-123",
        details="Deleted test opp",
    )
    response = client.get("/audit-log", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["action"] == "delete"
    assert data[0]["entity_type"] == "opportunity"
    assert data[0]["details"] == "Deleted test opp"


def test_get_audit_log_filter_by_entity_type(client, admin_headers, db, admin_user):
    create_audit_entry(
        db,
        user_id=admin_user.id,
        action="delete",
        entity_type="opportunity",
        entity_id="opp-1",
    )
    create_audit_entry(
        db,
        user_id=admin_user.id,
        action="delete",
        entity_type="account",
        entity_id="acct-1",
    )
    response = client.get("/audit-log?entity_type=opportunity", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_audit_log_filter_by_entity_id(client, admin_headers, db, admin_user):
    create_audit_entry(
        db,
        user_id=admin_user.id,
        action="delete",
        entity_type="opportunity",
        entity_id="opp-specific",
    )
    create_audit_entry(
        db,
        user_id=admin_user.id,
        action="delete",
        entity_type="opportunity",
        entity_id="opp-other",
    )
    response = client.get("/audit-log?entity_id=opp-specific", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_audit_log_filter_by_action(client, admin_headers, db, admin_user):
    create_audit_entry(
        db,
        user_id=admin_user.id,
        action="delete",
        entity_type="opportunity",
        entity_id="opp-1",
    )
    create_audit_entry(
        db,
        user_id=admin_user.id,
        action="update",
        entity_type="opportunity",
        entity_id="opp-2",
    )
    response = client.get("/audit-log?action=delete", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_audit_log_pagination(client, admin_headers, db, admin_user):
    for i in range(5):
        create_audit_entry(
            db,
            user_id=admin_user.id,
            action="delete",
            entity_type="opportunity",
            entity_id=f"opp-{i}",
        )
    response = client.get("/audit-log?skip=2&limit=2", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_audit_log_forbidden_for_non_admin(client, user_headers, regular_user):
    response = client.get("/audit-log", headers=user_headers)
    assert response.status_code == 403


# --- Audit trail on delete ---


def test_delete_opportunity_creates_audit_entry(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    response = client.delete(f"/opportunities/{opp.id}", headers=admin_headers)
    assert response.status_code == 204

    entries = db.query(AuditLog).filter(AuditLog.entity_id == opp.id).all()
    assert len(entries) == 1
    assert entries[0].action == "delete"
    assert entries[0].entity_type == "opportunity"
    assert "Audit Test Opp" in entries[0].details


def test_delete_account_creates_audit_entry(client, admin_headers, db, admin_user):
    acct = _make_account(db, created_by_user_id=admin_user.id)
    response = client.delete(f"/accounts/{acct.id}", headers=admin_headers)
    assert response.status_code == 204

    entries = db.query(AuditLog).filter(AuditLog.entity_id == acct.id).all()
    assert len(entries) == 1
    assert entries[0].action == "delete"
    assert entries[0].entity_type == "account"


def test_delete_contact_creates_audit_entry(client, admin_headers, db, admin_user):
    contact = _make_contact(db, admin_user.id)
    response = client.delete(f"/contacts/{contact.id}", headers=admin_headers)
    assert response.status_code == 204

    entries = db.query(AuditLog).filter(AuditLog.entity_id == contact.id).all()
    assert len(entries) == 1
    assert entries[0].action == "delete"
    assert entries[0].entity_type == "contact"


def test_delete_contract_creates_audit_entry(client, admin_headers, db, admin_user):
    contract = _make_contract(db, admin_user.id)
    response = client.delete(f"/contracts/{contract.id}", headers=admin_headers)
    assert response.status_code == 204

    entries = db.query(AuditLog).filter(AuditLog.entity_id == contract.id).all()
    assert len(entries) == 1
    assert entries[0].action == "delete"
    assert entries[0].entity_type == "contract"

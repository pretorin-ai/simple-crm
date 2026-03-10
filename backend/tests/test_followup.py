"""Tests for follow-up endpoints."""

from datetime import datetime, timedelta, timezone

from freezegun import freeze_time

from app.auth import create_access_token
from app.models.models import Contact
from app.utils import generate_id


def _frozen_headers(user):
    """Create auth headers valid at the frozen time."""
    token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def test_get_due_follow_ups_empty(client, admin_headers, admin_user):
    response = client.get("/contacts/follow-ups/due", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_due_follow_ups(client, sample_contact_for_regular, admin_user, db):
    """Create a contact with a follow-up date in the near future."""
    with freeze_time("2026-06-15T12:00:00Z"):
        headers = _frozen_headers(admin_user)
        frozen_now = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        contact = Contact(
            id=generate_id(),
            first_name="Due",
            last_name="Soon",
            email="due@example.com",
            phone="555-0000",
            organization="Due Corp",
            contact_type="individual",
            status="warm",
            needs_follow_up=True,
            follow_up_date=frozen_now + timedelta(days=2),
            assigned_user_id=admin_user.id,
            created_at=frozen_now,
        )
        db.add(contact)
        db.commit()

        response = client.get("/contacts/follow-ups/due?days_ahead=7", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(c["first_name"] == "Due" for c in data)


def test_get_due_follow_ups_custom_days(client, admin_user, db):
    with freeze_time("2026-06-15T12:00:00Z"):
        headers = _frozen_headers(admin_user)
        frozen_now = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        contact = Contact(
            id=generate_id(),
            first_name="Far",
            last_name="Away",
            email="far@example.com",
            phone="555-0000",
            organization="Far Corp",
            contact_type="individual",
            status="cold",
            needs_follow_up=True,
            follow_up_date=frozen_now + timedelta(days=20),
            assigned_user_id=admin_user.id,
            created_at=frozen_now,
        )
        db.add(contact)
        db.commit()

        # 7 days ahead should not include it
        response = client.get("/contacts/follow-ups/due?days_ahead=7", headers=headers)
        assert all(c["first_name"] != "Far" for c in response.json())

        # 30 days ahead should include it
        response = client.get("/contacts/follow-ups/due?days_ahead=30", headers=headers)
        assert any(c["first_name"] == "Far" for c in response.json())


def test_get_due_follow_ups_only_own(client, admin_user, regular_user, db):
    """User should only see follow-ups for their own contacts."""
    with freeze_time("2026-06-15T12:00:00Z"):
        user_headers = _frozen_headers(regular_user)
        frozen_now = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        admin_contact = Contact(
            id=generate_id(),
            first_name="Admin",
            last_name="Contact",
            email="admin_fu@example.com",
            phone="555-0000",
            organization="Admin Corp",
            contact_type="individual",
            status="warm",
            needs_follow_up=True,
            follow_up_date=frozen_now + timedelta(days=1),
            assigned_user_id=admin_user.id,
            created_at=frozen_now,
        )
        user_contact = Contact(
            id=generate_id(),
            first_name="User",
            last_name="Contact",
            email="user_fu@example.com",
            phone="555-0000",
            organization="User Corp",
            contact_type="individual",
            status="warm",
            needs_follow_up=True,
            follow_up_date=frozen_now + timedelta(days=1),
            assigned_user_id=regular_user.id,
            created_at=frozen_now,
        )
        db.add(admin_contact)
        db.add(user_contact)
        db.commit()

        response = client.get("/contacts/follow-ups/due", headers=user_headers)
        data = response.json()
        assert all(c["first_name"] != "Admin" for c in data)
        assert any(c["first_name"] == "User" for c in data)


def test_get_overdue_follow_ups_empty(client, admin_headers, admin_user):
    response = client.get("/contacts/follow-ups/overdue", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_overdue_follow_ups(client, admin_user, db):
    with freeze_time("2026-06-15T12:00:00Z"):
        headers = _frozen_headers(admin_user)
        frozen_now = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        contact = Contact(
            id=generate_id(),
            first_name="Overdue",
            last_name="Contact",
            email="overdue@example.com",
            phone="555-0000",
            organization="Overdue Corp",
            contact_type="government",
            status="hot",
            needs_follow_up=True,
            follow_up_date=frozen_now - timedelta(days=5),
            assigned_user_id=admin_user.id,
            created_at=frozen_now,
        )
        db.add(contact)
        db.commit()

        response = client.get("/contacts/follow-ups/overdue", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(c["first_name"] == "Overdue" for c in data)


def test_get_overdue_follow_ups_only_own(client, admin_user, regular_user, db):
    with freeze_time("2026-06-15T12:00:00Z"):
        user_headers = _frozen_headers(regular_user)
        frozen_now = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        admin_contact = Contact(
            id=generate_id(),
            first_name="AdminOverdue",
            last_name="X",
            email="admin_overdue@example.com",
            phone="555-0000",
            organization="X",
            contact_type="individual",
            status="cold",
            needs_follow_up=True,
            follow_up_date=frozen_now - timedelta(days=3),
            assigned_user_id=admin_user.id,
            created_at=frozen_now,
        )
        user_contact = Contact(
            id=generate_id(),
            first_name="UserOverdue",
            last_name="Y",
            email="user_overdue@example.com",
            phone="555-0000",
            organization="Y",
            contact_type="individual",
            status="cold",
            needs_follow_up=True,
            follow_up_date=frozen_now - timedelta(days=3),
            assigned_user_id=regular_user.id,
            created_at=frozen_now,
        )
        db.add(admin_contact)
        db.add(user_contact)
        db.commit()

        response = client.get("/contacts/follow-ups/overdue", headers=user_headers)
        data = response.json()
        assert all(c["first_name"] != "AdminOverdue" for c in data)
        assert any(c["first_name"] == "UserOverdue" for c in data)


def test_follow_ups_no_auth(client):
    response = client.get("/contacts/follow-ups/due")
    assert response.status_code == 401


def test_overdue_no_auth(client):
    response = client.get("/contacts/follow-ups/overdue")
    assert response.status_code == 401

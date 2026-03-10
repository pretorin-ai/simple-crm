"""Tests for opportunity timeline endpoints."""

from datetime import datetime, timezone

from app.models.models import Opportunity, OpportunityEvent
from app.utils import generate_id


def _make_opportunity(db, user_id, **overrides):
    defaults = {
        "id": generate_id(),
        "title": "Test Opportunity",
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


def _make_event(db, opp_id, user_id, **overrides):
    defaults = {
        "id": generate_id(),
        "opportunity_id": opp_id,
        "date": datetime.now(timezone.utc),
        "event_type": "note",
        "description": "Test event",
        "created_by_user_id": user_id,
    }
    defaults.update(overrides)
    ev = OpportunityEvent(**defaults)
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


# --- GET timeline ---


def test_get_timeline_opp_not_found(client, admin_headers):
    response = client.get("/opportunities/fake-id/timeline", headers=admin_headers)
    assert response.status_code == 404


def test_get_timeline_empty(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    response = client.get(f"/opportunities/{opp.id}/timeline", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_timeline_with_events(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    _make_event(db, opp.id, admin_user.id, description="First")
    _make_event(db, opp.id, admin_user.id, description="Second")
    response = client.get(f"/opportunities/{opp.id}/timeline", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


# --- POST timeline ---


def test_create_event(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    payload = {
        "opportunity_id": opp.id,
        "date": datetime.now(timezone.utc).isoformat(),
        "event_type": "meeting",
        "description": "Kickoff meeting",
    }
    response = client.post(f"/opportunities/{opp.id}/timeline", json=payload, headers=admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["description"] == "Kickoff meeting"
    assert data["event_type"] == "meeting"


def test_create_event_opp_not_found(client, admin_headers):
    payload = {
        "opportunity_id": "fake-id",
        "date": datetime.now(timezone.utc).isoformat(),
        "event_type": "note",
        "description": "Test",
    }
    response = client.post("/opportunities/fake-id/timeline", json=payload, headers=admin_headers)
    assert response.status_code == 404


# --- PATCH timeline ---


def test_update_event(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    ev = _make_event(db, opp.id, admin_user.id)
    payload = {"description": "Updated description"}
    response = client.patch(
        f"/opportunities/{opp.id}/timeline/{ev.id}",
        json=payload,
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Updated description"


def test_update_event_not_found(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    response = client.patch(
        f"/opportunities/{opp.id}/timeline/fake-id",
        json={"description": "Nope"},
        headers=admin_headers,
    )
    assert response.status_code == 404


# --- DELETE timeline ---


def test_delete_event(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    ev = _make_event(db, opp.id, admin_user.id)
    response = client.delete(f"/opportunities/{opp.id}/timeline/{ev.id}", headers=admin_headers)
    assert response.status_code == 204


def test_delete_event_not_found(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    response = client.delete(f"/opportunities/{opp.id}/timeline/fake-id", headers=admin_headers)
    assert response.status_code == 404


# --- Authorization ---


def test_update_event_forbidden_for_non_creator(client, user_headers, db, admin_user, regular_user):
    opp = _make_opportunity(db, admin_user.id)
    ev = _make_event(db, opp.id, admin_user.id)
    response = client.patch(
        f"/opportunities/{opp.id}/timeline/{ev.id}",
        json={"description": "Hacked"},
        headers=user_headers,
    )
    assert response.status_code == 403


def test_delete_event_forbidden_for_non_creator(client, user_headers, db, admin_user, regular_user):
    opp = _make_opportunity(db, admin_user.id)
    ev = _make_event(db, opp.id, admin_user.id)
    response = client.delete(
        f"/opportunities/{opp.id}/timeline/{ev.id}",
        headers=user_headers,
    )
    assert response.status_code == 403

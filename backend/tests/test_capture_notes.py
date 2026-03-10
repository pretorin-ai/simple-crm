"""Tests for capture notes endpoints."""

from app.models.models import CaptureNote, Opportunity
from app.utils import generate_id


def _make_opportunity(db, user_id, **overrides):
    defaults = {
        "id": generate_id(),
        "title": "Test Opportunity",
        "stage": "capture",
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


def _make_note(db, opp_id, section="customer_intel", content="Some intel"):
    note = CaptureNote(
        id=generate_id(),
        opportunity_id=opp_id,
        section=section,
        content=content,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


# --- GET capture-notes ---


def test_get_notes_opp_not_found(client, admin_headers):
    response = client.get("/opportunities/fake-id/capture-notes", headers=admin_headers)
    assert response.status_code == 404


def test_get_notes_empty(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    response = client.get(f"/opportunities/{opp.id}/capture-notes", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_notes_with_data(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    _make_note(db, opp.id, section="risks", content="Budget risk")
    response = client.get(f"/opportunities/{opp.id}/capture-notes", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["section"] == "risks"


# --- PUT capture-notes (upsert) ---


def test_upsert_create_note(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    payload = {"content": "New intel gathered"}
    response = client.put(
        f"/opportunities/{opp.id}/capture-notes/customer_intel",
        json=payload,
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["section"] == "customer_intel"
    assert data["content"] == "New intel gathered"


def test_upsert_update_existing_note(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    _make_note(db, opp.id, section="strategy", content="Old strategy")
    payload = {"content": "Updated strategy"}
    response = client.put(
        f"/opportunities/{opp.id}/capture-notes/strategy",
        json=payload,
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["content"] == "Updated strategy"


def test_upsert_invalid_section(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    payload = {"content": "test"}
    response = client.put(
        f"/opportunities/{opp.id}/capture-notes/invalid_section",
        json=payload,
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_upsert_opp_not_found(client, admin_headers):
    payload = {"content": "test"}
    response = client.put(
        "/opportunities/fake-id/capture-notes/risks",
        json=payload,
        headers=admin_headers,
    )
    assert response.status_code == 404

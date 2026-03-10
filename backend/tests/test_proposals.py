"""Tests for proposals CRUD endpoints."""

from app.models.models import Opportunity, Proposal
from app.utils import generate_id


def _make_opportunity(db, user_id, **overrides):
    defaults = {
        "id": generate_id(),
        "title": "Test Opp",
        "stage": "proposal",
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


def _make_proposal(db, opp_id, user_id, **overrides):
    defaults = {
        "id": generate_id(),
        "opportunity_id": opp_id,
        "proposal_manager_id": user_id,
        "status": "not_started",
        "notes": "",
    }
    defaults.update(overrides)
    p = Proposal(**defaults)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_get_proposals_empty(client, admin_headers, admin_user):
    response = client.get("/proposals", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_proposals(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    _make_proposal(db, opp.id, admin_user.id)
    response = client.get("/proposals", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_proposals_filter_by_opportunity(client, admin_headers, db, admin_user):
    opp1 = _make_opportunity(db, admin_user.id)
    opp2 = _make_opportunity(db, admin_user.id, title="Other Opp")
    _make_proposal(db, opp1.id, admin_user.id)
    _make_proposal(db, opp2.id, admin_user.id)
    response = client.get(f"/proposals?opportunity_id={opp1.id}", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_proposals_filter_by_status(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    _make_proposal(db, opp.id, admin_user.id, status="in_progress")
    response = client.get("/proposals?status=in_progress", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get("/proposals?status=submitted", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_get_proposal_by_id(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    p = _make_proposal(db, opp.id, admin_user.id)
    response = client.get(f"/proposals/{p.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "not_started"


def test_get_proposal_not_found(client, admin_headers, admin_user):
    response = client.get("/proposals/nonexistent", headers=admin_headers)
    assert response.status_code == 404


def test_create_proposal(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    response = client.post(
        "/proposals",
        json={
            "opportunity_id": opp.id,
            "submission_type": "full",
            "submission_deadline": "2026-06-01T00:00:00",
            "status": "not_started",
            "notes": "New proposal",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["opportunity_id"] == opp.id
    assert data["submission_type"] == "full"


def test_create_proposal_conflict(client, admin_headers, db, admin_user):
    """Cannot create a second proposal for the same opportunity."""
    opp = _make_opportunity(db, admin_user.id)
    _make_proposal(db, opp.id, admin_user.id)
    response = client.post(
        "/proposals",
        json={
            "opportunity_id": opp.id,
            "status": "not_started",
            "notes": "",
        },
        headers=admin_headers,
    )
    assert response.status_code == 409


def test_update_proposal(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    p = _make_proposal(db, opp.id, admin_user.id)
    response = client.put(
        f"/proposals/{p.id}",
        json={
            "opportunity_id": opp.id,
            "submission_type": "partial",
            "status": "in_progress",
            "notes": "Updated",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"
    assert data["submission_type"] == "partial"


def test_update_proposal_not_found(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    response = client.put(
        "/proposals/nonexistent",
        json={
            "opportunity_id": opp.id,
            "status": "not_started",
            "notes": "",
        },
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_patch_proposal(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    p = _make_proposal(db, opp.id, admin_user.id)
    response = client.patch(
        f"/proposals/{p.id}",
        json={"status": "review"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "review"


def test_patch_proposal_not_found(client, admin_headers, admin_user):
    response = client.patch(
        "/proposals/nonexistent",
        json={"status": "final"},
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_delete_proposal(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    p = _make_proposal(db, opp.id, admin_user.id)
    response = client.delete(f"/proposals/{p.id}", headers=admin_headers)
    assert response.status_code == 204

    response = client.get(f"/proposals/{p.id}", headers=admin_headers)
    assert response.status_code == 404


def test_delete_proposal_not_found(client, admin_headers, admin_user):
    response = client.delete("/proposals/nonexistent", headers=admin_headers)
    assert response.status_code == 404


# --- Authorization ---


def test_update_proposal_forbidden_for_non_owner(
    client, user_headers, db, admin_user, regular_user
):
    """Regular user who is neither proposal manager nor opp creator gets 403."""
    opp = _make_opportunity(db, admin_user.id)
    p = _make_proposal(db, opp.id, admin_user.id)
    response = client.put(
        f"/proposals/{p.id}",
        json={
            "opportunity_id": opp.id,
            "status": "in_progress",
            "notes": "Hacked",
        },
        headers=user_headers,
    )
    assert response.status_code == 403


def test_patch_proposal_forbidden_for_non_owner(client, user_headers, db, admin_user, regular_user):
    opp = _make_opportunity(db, admin_user.id)
    p = _make_proposal(db, opp.id, admin_user.id)
    response = client.patch(
        f"/proposals/{p.id}",
        json={"status": "review"},
        headers=user_headers,
    )
    assert response.status_code == 403


def test_delete_proposal_forbidden_for_non_owner(
    client, user_headers, db, admin_user, regular_user
):
    opp = _make_opportunity(db, admin_user.id)
    p = _make_proposal(db, opp.id, admin_user.id)
    response = client.delete(f"/proposals/{p.id}", headers=user_headers)
    assert response.status_code == 403


def test_proposal_manager_can_modify(client, user_headers, db, admin_user, regular_user):
    """Proposal manager (even if not opp creator) can modify."""
    opp = _make_opportunity(db, admin_user.id)
    p = _make_proposal(db, opp.id, regular_user.id)
    response = client.patch(
        f"/proposals/{p.id}",
        json={"status": "review"},
        headers=user_headers,
    )
    assert response.status_code == 200


def test_opp_creator_can_modify_proposal(client, user_headers, db, admin_user, regular_user):
    """Opportunity creator can modify proposal even if not manager."""
    opp = _make_opportunity(db, regular_user.id)
    p = _make_proposal(db, opp.id, admin_user.id)
    response = client.patch(
        f"/proposals/{p.id}",
        json={"status": "review"},
        headers=user_headers,
    )
    assert response.status_code == 200

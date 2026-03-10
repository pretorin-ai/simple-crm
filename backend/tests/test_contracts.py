"""Tests for contracts CRUD and SAM.gov import endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.import_service import _get_field


def test_get_field_from_object():
    """_get_field works with both dicts and objects."""
    # Dict path
    assert _get_field({"key": "val"}, "key") == "val"
    assert _get_field({"key": "val"}, "missing") is None

    # Object path
    class Obj:
        key = "val"

    assert _get_field(Obj(), "key") == "val"
    assert _get_field(Obj(), "missing") is None


def test_get_contracts_empty(client, admin_headers, admin_user):
    response = client.get("/contracts", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_contracts(client, admin_headers, sample_contract):
    response = client.get("/contracts", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Contract"


def test_get_contracts_with_api_key(client, user_with_api_key, sample_contract):
    user, raw_key = user_with_api_key
    response = client.get("/contracts", headers={"Authorization": f"Bearer {raw_key}"})
    assert response.status_code == 200


def test_get_contract_by_id(client, admin_headers, sample_contract):
    response = client.get(f"/contracts/{sample_contract.id}", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Contract"
    assert data["status"] == "prospective"


def test_get_contract_not_found(client, admin_headers):
    response = client.get("/contracts/nonexistent-id", headers=admin_headers)
    assert response.status_code == 404


def test_create_contract(client, admin_headers):
    response = client.post(
        "/contracts",
        json={
            "title": "New Contract",
            "description": "A new contract",
            "source": "Direct",
            "deadline": "2026-06-01T00:00:00",
            "status": "prospective",
            "notes": "Notes here",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "New Contract"
    assert data["assigned_contact_ids"] == []


def test_create_contract_with_contacts(client, admin_headers, sample_contact):
    response = client.post(
        "/contracts",
        json={
            "title": "Contract With Contacts",
            "description": "Has contacts",
            "source": "SAM.gov",
            "deadline": "2026-07-01T00:00:00",
            "status": "in progress",
            "assigned_contact_ids": [sample_contact.id],
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert sample_contact.id in data["assigned_contact_ids"]


def test_create_contract_with_submission_link(client, admin_headers):
    response = client.post(
        "/contracts",
        json={
            "title": "Linked Contract",
            "source": "SAM.gov",
            "deadline": "2026-08-01T00:00:00",
            "status": "prospective",
            "submission_link": "https://sam.gov/opp/12345",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert response.json()["submission_link"] == "https://sam.gov/opp/12345"


def test_update_contract(client, admin_headers, sample_contract):
    response = client.put(
        f"/contracts/{sample_contract.id}",
        json={
            "title": "Updated Contract",
            "description": "Updated description",
            "source": "Updated Source",
            "deadline": "2026-09-01T00:00:00",
            "status": "in progress",
            "notes": "Updated notes",
            "assigned_contact_ids": [],
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Contract"
    assert data["status"] == "in progress"


def test_update_contract_with_contacts(client, admin_headers, sample_contract, sample_contact):
    response = client.put(
        f"/contracts/{sample_contract.id}",
        json={
            "title": "Test Contract",
            "description": "Test description",
            "source": "SAM.gov",
            "deadline": "2026-06-01T00:00:00",
            "status": "prospective",
            "notes": "Test notes",
            "assigned_contact_ids": [sample_contact.id],
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert sample_contact.id in response.json()["assigned_contact_ids"]


def test_update_contract_not_found(client, admin_headers):
    response = client.put(
        "/contracts/nonexistent-id",
        json={
            "title": "X",
            "source": "X",
            "deadline": "2026-06-01T00:00:00",
            "status": "prospective",
        },
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_delete_contract(client, admin_headers, sample_contract):
    response = client.delete(f"/contracts/{sample_contract.id}", headers=admin_headers)
    assert response.status_code == 204

    response = client.get(f"/contracts/{sample_contract.id}", headers=admin_headers)
    assert response.status_code == 404


def test_delete_contract_not_found(client, admin_headers):
    response = client.delete("/contracts/nonexistent-id", headers=admin_headers)
    assert response.status_code == 404


def test_update_contract_forbidden(client, user_headers, sample_contract_owned_by_admin):
    """Regular user cannot update a contract they don't own."""
    response = client.put(
        f"/contracts/{sample_contract_owned_by_admin.id}",
        json={
            "title": "Hacked",
            "source": "Hacked",
            "deadline": "2026-06-01T00:00:00",
            "status": "prospective",
        },
        headers=user_headers,
    )
    assert response.status_code == 403


def test_delete_contract_forbidden(client, user_headers, sample_contract_owned_by_admin):
    """Regular user cannot delete a contract they don't own."""
    response = client.delete(
        f"/contracts/{sample_contract_owned_by_admin.id}",
        headers=user_headers,
    )
    assert response.status_code == 403


def test_patch_contract(client, admin_headers, sample_contract):
    """Partially update a contract via PATCH."""
    response = client.patch(
        f"/contracts/{sample_contract.id}",
        json={"title": "Patched Contract"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Patched Contract"
    assert data["source"] == "SAM.gov"  # unchanged


def test_patch_contract_with_contacts(client, admin_headers, sample_contract, sample_contact):
    """PATCH contract with assigned_contact_ids."""
    response = client.patch(
        f"/contracts/{sample_contract.id}",
        json={"assigned_contact_ids": [sample_contact.id]},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert sample_contact.id in response.json()["assigned_contact_ids"]


def test_patch_contract_not_found(client, admin_headers):
    """PATCH nonexistent contract returns 404."""
    response = client.patch(
        "/contracts/nonexistent-id",
        json={"title": "Ghost"},
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_patch_contract_forbidden(client, user_headers, sample_contract_owned_by_admin):
    """Regular user cannot PATCH a contract they don't own."""
    response = client.patch(
        f"/contracts/{sample_contract_owned_by_admin.id}",
        json={"title": "Hacked"},
        headers=user_headers,
    )
    assert response.status_code == 403


def test_import_samgov_exception_in_loop(client, admin_headers):
    """Exception during individual opportunity import is caught and recorded."""
    with patch("app.services.import_service.generate_id", side_effect=[Exception("boom")]):
        response = client.post(
            "/contracts/import/samgov",
            json={
                "opportunities": [
                    {
                        "noticeId": "SAM-EXCEPTION",
                        "title": "Exception Test",
                        "responseDeadLine": "2026-06-01T00:00:00Z",
                        "source": "SAM.gov",
                    }
                ],
                "auto_create_contacts": False,
            },
            headers=admin_headers,
        )
    assert response.status_code == 200
    data = response.json()
    assert data["contracts_created"] == 0
    assert len(data["errors"]) == 1
    assert "boom" in data["errors"][0]


def test_import_samgov_commit_failure():
    """Final commit failure returns 500."""
    from app.services.import_service import import_opportunities

    mock_db = MagicMock()
    mock_db.begin_nested.return_value = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_db.commit.side_effect = Exception("commit failed")

    mock_user = MagicMock()
    mock_user.id = "user-123"

    with pytest.raises(HTTPException) as exc_info:
        import_opportunities(
            opportunities=[
                {
                    "noticeId": "SAM-COMMITFAIL",
                    "title": "Commit Fail Test",
                    "responseDeadLine": "2026-06-01T00:00:00Z",
                    "source": "SAM.gov",
                }
            ],
            auto_create_contacts=False,
            current_user=mock_user,
            db=mock_db,
        )
    assert exc_info.value.status_code == 500
    assert "Failed to save" in exc_info.value.detail


# --- SAM.gov import tests ---


def test_import_samgov_basic(client, admin_headers):
    response = client.post(
        "/contracts/import/samgov",
        json={
            "opportunities": [
                {
                    "noticeId": "SAM-001",
                    "title": "Test Opportunity",
                    "responseDeadLine": "2026-06-01T00:00:00Z",
                    "source": "SAM.gov",
                }
            ],
            "auto_create_contacts": False,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["contracts_created"] == 1
    assert data["contracts_skipped"] == 0


def test_import_samgov_with_contacts(client, admin_headers):
    response = client.post(
        "/contracts/import/samgov",
        json={
            "opportunities": [
                {
                    "noticeId": "SAM-002",
                    "title": "Opportunity With Contacts",
                    "responseDeadLine": "2026-07-01T00:00:00",
                    "source": "SAM.gov",
                    "pointOfContact": [
                        {
                            "email": "poc@gov.gov",
                            "fullName": "John Smith",
                            "phone": "555-1234",
                        }
                    ],
                }
            ],
            "auto_create_contacts": True,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["contracts_created"] == 1
    assert data["contacts_created"] == 1


def test_import_samgov_duplicate_skipped(client, admin_headers):
    # Import first time
    client.post(
        "/contracts/import/samgov",
        json={
            "opportunities": [
                {
                    "noticeId": "SAM-DUP",
                    "title": "Duplicate Test",
                    "responseDeadLine": "2026-06-01T00:00:00Z",
                    "source": "SAM.gov",
                }
            ],
            "auto_create_contacts": False,
        },
        headers=admin_headers,
    )

    # Import same again
    response = client.post(
        "/contracts/import/samgov",
        json={
            "opportunities": [
                {
                    "noticeId": "SAM-DUP",
                    "title": "Duplicate Test",
                    "responseDeadLine": "2026-06-01T00:00:00Z",
                    "source": "SAM.gov",
                }
            ],
            "auto_create_contacts": False,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["contracts_skipped"] == 1
    assert response.json()["contracts_created"] == 0


def test_import_samgov_no_deadline(client, admin_headers):
    response = client.post(
        "/contracts/import/samgov",
        json={
            "opportunities": [
                {
                    "noticeId": "SAM-NODEADLINE",
                    "title": "No Deadline",
                    "source": "SAM.gov",
                }
            ],
            "auto_create_contacts": False,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    # Opportunities don't require a deadline, so import succeeds
    assert data["contracts_created"] == 1
    assert len(data["errors"]) == 0


def test_import_samgov_bad_deadline_format(client, admin_headers):
    response = client.post(
        "/contracts/import/samgov",
        json={
            "opportunities": [
                {
                    "noticeId": "SAM-BADDATE",
                    "title": "Bad Deadline",
                    "responseDeadLine": "not-a-date",
                    "source": "SAM.gov",
                }
            ],
            "auto_create_contacts": False,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    # Opportunities don't require a deadline, import succeeds with null deadline
    assert data["contracts_created"] == 1
    assert len(data["errors"]) == 0


def test_import_samgov_alternate_date_format(client, admin_headers):
    response = client.post(
        "/contracts/import/samgov",
        json={
            "opportunities": [
                {
                    "noticeId": "SAM-ALTDATE",
                    "title": "Alternate Date Format",
                    "responseDeadLine": "2026-08-15",
                    "source": "SAM.gov",
                }
            ],
            "auto_create_contacts": False,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["contracts_created"] == 1


def test_import_samgov_with_metadata(client, admin_headers):
    response = client.post(
        "/contracts/import/samgov",
        json={
            "opportunities": [
                {
                    "noticeId": "SAM-META",
                    "title": "Metadata Test",
                    "solicitationNumber": "SOL-12345",
                    "naicsCode": "541511",
                    "responseDeadLine": "2026-06-01T00:00:00Z",
                    "uiLink": "https://sam.gov/opp/meta",
                    "source": "SAM.gov",
                    "notes": "Extra notes",
                }
            ],
            "auto_create_contacts": False,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["contracts_created"] == 1


def test_import_samgov_existing_contact_reused(client, admin_headers, sample_contact):
    """If a contact with the same email exists, it should be reused."""
    response = client.post(
        "/contracts/import/samgov",
        json={
            "opportunities": [
                {
                    "noticeId": "SAM-EXISTCONTACT",
                    "title": "Existing Contact Test",
                    "responseDeadLine": "2026-06-01T00:00:00Z",
                    "source": "SAM.gov",
                    "pointOfContact": [
                        {
                            "email": "john@example.com",
                            "fullName": "John Doe",
                        }
                    ],
                }
            ],
            "auto_create_contacts": True,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["contacts_created"] == 0  # Reused existing


def test_import_samgov_poc_missing_email(client, admin_headers):
    """POC without email should be skipped."""
    response = client.post(
        "/contracts/import/samgov",
        json={
            "opportunities": [
                {
                    "noticeId": "SAM-NOEMAIL",
                    "title": "No Email POC",
                    "responseDeadLine": "2026-06-01T00:00:00Z",
                    "source": "SAM.gov",
                    "pointOfContact": [
                        {
                            "fullName": "No Email Person",
                        }
                    ],
                }
            ],
            "auto_create_contacts": True,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["contacts_created"] == 0


def test_import_samgov_poc_missing_name(client, admin_headers):
    """POC without fullName should be skipped."""
    response = client.post(
        "/contracts/import/samgov",
        json={
            "opportunities": [
                {
                    "noticeId": "SAM-NONAME",
                    "title": "No Name POC",
                    "responseDeadLine": "2026-06-01T00:00:00Z",
                    "source": "SAM.gov",
                    "pointOfContact": [
                        {
                            "email": "noname@gov.gov",
                        }
                    ],
                }
            ],
            "auto_create_contacts": True,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["contacts_created"] == 0


def test_import_samgov_with_api_key(client, user_with_api_key):
    user, raw_key = user_with_api_key
    response = client.post(
        "/contracts/import/samgov",
        json={
            "opportunities": [
                {
                    "noticeId": "SAM-APIKEY",
                    "title": "API Key Import",
                    "responseDeadLine": "2026-06-01T00:00:00Z",
                    "source": "SAM.gov",
                }
            ],
            "auto_create_contacts": False,
        },
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    assert response.status_code == 200
    assert response.json()["contracts_created"] == 1


def test_import_samgov_poc_single_name(client, admin_headers):
    """POC with a single name should use it as first_name."""
    response = client.post(
        "/contracts/import/samgov",
        json={
            "opportunities": [
                {
                    "noticeId": "SAM-SINGLENAME",
                    "title": "Single Name POC",
                    "responseDeadLine": "2026-06-01T00:00:00Z",
                    "source": "SAM.gov",
                    "pointOfContact": [
                        {
                            "email": "single@gov.gov",
                            "fullName": "Madonna",
                        }
                    ],
                }
            ],
            "auto_create_contacts": True,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["contacts_created"] == 1


def test_import_samgov_multiple_opportunities(client, admin_headers):
    """Import multiple opportunities in one request."""
    response = client.post(
        "/contracts/import/samgov",
        json={
            "opportunities": [
                {
                    "noticeId": "SAM-MULTI-1",
                    "title": "Multi 1",
                    "responseDeadLine": "2026-06-01T00:00:00Z",
                    "source": "SAM.gov",
                },
                {
                    "noticeId": "SAM-MULTI-2",
                    "title": "Multi 2",
                    "responseDeadLine": "2026-07-01T00:00:00Z",
                    "source": "SAM.gov",
                },
            ],
            "auto_create_contacts": False,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["contracts_created"] == 2


def test_import_samgov_poc_no_phone(client, admin_headers):
    """POC with email and name but no phone."""
    response = client.post(
        "/contracts/import/samgov",
        json={
            "opportunities": [
                {
                    "noticeId": "SAM-NOPHONE",
                    "title": "No Phone POC",
                    "responseDeadLine": "2026-06-01T00:00:00Z",
                    "source": "SAM.gov",
                    "pointOfContact": [
                        {
                            "email": "nophone@gov.gov",
                            "fullName": "Jane Doe",
                        }
                    ],
                }
            ],
            "auto_create_contacts": True,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["contacts_created"] == 1


def test_import_samgov_with_description(client, admin_headers):
    """Import with description field."""
    response = client.post(
        "/contracts/import/samgov",
        json={
            "opportunities": [
                {
                    "noticeId": "SAM-DESC",
                    "title": "Description Test",
                    "description": "A detailed description of the opportunity",
                    "responseDeadLine": "2026-06-01T00:00:00Z",
                    "source": "SAM.gov",
                }
            ],
            "auto_create_contacts": False,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["contracts_created"] == 1

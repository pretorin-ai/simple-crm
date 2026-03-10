"""Tests for SAM.gov collection service and endpoints."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.sam_gov import SAMGovClient, collect_opportunities

# --- Unit tests for SAMGovClient ---


class TestSAMGovClient:
    def test_init(self):
        client = SAMGovClient("test-key")
        assert client.api_key == "test-key"
        assert client.session.headers["X-Api-Key"] == "test-key"

    def test_search_validates_naics_limit(self):
        client = SAMGovClient("key")
        from datetime import datetime

        with pytest.raises(ValueError, match="Maximum 50 NAICS codes"):
            client.search_opportunities(
                posted_from=datetime(2024, 1, 1),
                posted_to=datetime(2024, 1, 2),
                naics_codes=["x"] * 51,
            )

    def test_search_validates_date_range(self):
        client = SAMGovClient("key")
        from datetime import datetime

        with pytest.raises(ValueError, match="Maximum 90 days"):
            client.search_opportunities(
                posted_from=datetime(2024, 1, 1),
                posted_to=datetime(2024, 12, 31),
            )

    @patch("app.services.sam_gov.time.sleep")
    def test_search_opportunities_success(self, mock_sleep):
        client = SAMGovClient("key")
        from datetime import datetime

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "totalRecords": 1,
            "opportunitiesData": [{"noticeId": "ABC123", "title": "Test Opp"}],
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.session, "get", return_value=mock_response):
            result = client.search_opportunities(
                posted_from=datetime(2024, 1, 1),
                posted_to=datetime(2024, 1, 10),
                naics_codes=["541511"],
            )

        assert result["totalRecords"] == 1
        assert len(result["opportunitiesData"]) == 1
        mock_sleep.assert_called_once_with(2)

    @patch("app.services.sam_gov.time.sleep")
    def test_search_logs_error_on_non_200(self, mock_sleep):
        client = SAMGovClient("key")
        from datetime import datetime

        from requests.exceptions import HTTPError

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.raise_for_status.side_effect = HTTPError("403")

        with patch.object(client.session, "get", return_value=mock_response):
            with pytest.raises(HTTPError):
                client.search_opportunities(
                    posted_from=datetime(2024, 1, 1),
                    posted_to=datetime(2024, 1, 2),
                )

    @patch("app.services.sam_gov.time.sleep")
    def test_get_all_opportunities_pagination(self, mock_sleep):
        client = SAMGovClient("key")
        from datetime import datetime

        page1 = {
            "totalRecords": 1000,
            "opportunitiesData": [{"noticeId": "A"}],
        }
        page2 = {
            "totalRecords": 1000,
            "opportunitiesData": [{"noticeId": "B"}],
        }
        page3 = {
            "totalRecords": 1000,
            "opportunitiesData": [],
        }

        with patch.object(client, "search_opportunities", side_effect=[page1, page2, page3]):
            results = client.get_all_opportunities(
                posted_from=datetime(2024, 1, 1),
                posted_to=datetime(2024, 1, 10),
            )

        assert len(results) == 2

    @patch("app.services.sam_gov.time.sleep")
    def test_get_all_opportunities_handles_empty(self, mock_sleep):
        client = SAMGovClient("key")
        from datetime import datetime

        with patch.object(
            client,
            "search_opportunities",
            return_value={"totalRecords": 0, "opportunitiesData": []},
        ):
            results = client.get_all_opportunities(
                posted_from=datetime(2024, 1, 1),
                posted_to=datetime(2024, 1, 2),
            )

        assert results == []

    @patch("app.services.sam_gov.time.sleep")
    def test_get_all_opportunities_handles_exception(self, mock_sleep):
        client = SAMGovClient("key")
        from datetime import datetime

        with patch.object(client, "search_opportunities", side_effect=Exception("network error")):
            results = client.get_all_opportunities(
                posted_from=datetime(2024, 1, 1),
                posted_to=datetime(2024, 1, 2),
            )

        assert results == []


# --- Unit tests for collect_opportunities ---


class TestCollectOpportunities:
    def test_validates_days_back(self):
        with pytest.raises(ValueError, match="Maximum 90 days"):
            collect_opportunities("key", ["541511"], days_back=91)

    @patch("app.services.sam_gov.SAMGovClient.__init__", return_value=None)
    @patch("app.services.sam_gov.SAMGovClient.get_all_opportunities")
    def test_collects_and_deduplicates(self, mock_get_all, mock_init):
        # Same noticeId returned for two NAICS codes
        mock_get_all.side_effect = [
            [{"noticeId": "A", "type": "Solicitation", "title": "Opp A"}],
            [
                {"noticeId": "A", "type": "Solicitation", "title": "Opp A"},
                {"noticeId": "B", "type": "Solicitation", "title": "Opp B"},
            ],
        ]

        results = collect_opportunities("key", ["541511", "541512"], days_back=1)
        assert len(results) == 2
        notice_ids = {r["noticeId"] for r in results}
        assert notice_ids == {"A", "B"}

    @patch("app.services.sam_gov.SAMGovClient.__init__", return_value=None)
    @patch("app.services.sam_gov.SAMGovClient.get_all_opportunities")
    def test_filters_solicitations_only(self, mock_get_all, mock_init):
        mock_get_all.return_value = [
            {"noticeId": "A", "type": "Solicitation", "title": "Sol"},
            {"noticeId": "B", "type": "Award Notice", "title": "Award"},
            {"noticeId": "C", "type": "Pre-Solicitation", "title": "PreSol"},
        ]

        results = collect_opportunities("key", ["541511"], solicitations_only=True)
        # Only "Solicitation" and "Pre-Solicitation" contain "Solicitation"
        assert len(results) == 2

    @patch("app.services.sam_gov.SAMGovClient.__init__", return_value=None)
    @patch("app.services.sam_gov.SAMGovClient.get_all_opportunities")
    def test_no_filter_when_solicitations_only_false(self, mock_get_all, mock_init):
        mock_get_all.return_value = [
            {"noticeId": "A", "type": "Award Notice", "title": "Award"},
        ]

        results = collect_opportunities("key", ["541511"], solicitations_only=False)
        assert len(results) == 1

    @patch("app.services.sam_gov.SAMGovClient.__init__", return_value=None)
    @patch("app.services.sam_gov.SAMGovClient.get_all_opportunities")
    def test_skips_entries_without_notice_id(self, mock_get_all, mock_init):
        mock_get_all.return_value = [
            {"title": "No ID", "type": "Solicitation"},
            {"noticeId": "A", "type": "Solicitation", "title": "Has ID"},
        ]

        results = collect_opportunities("key", ["541511"])
        assert len(results) == 1


# --- Integration tests for /sam-gov/collect endpoint ---


SAMPLE_OPPORTUNITIES = [
    {
        "noticeId": "SAM-TEST-001",
        "title": "IT Services Contract",
        "solicitationNumber": "SOL-2024-001",
        "type": "Solicitation",
        "description": "Test opportunity description",
        "responseDeadLine": "2025-06-01T00:00:00+00:00",
        "postedDate": "2024-01-15",
        "naicsCode": "541511",
        "uiLink": "https://sam.gov/opp/test001",
        "pointOfContact": [
            {
                "email": "poc@agency.gov",
                "fullName": "Jane Smith",
                "phone": "555-0100",
            }
        ],
    },
    {
        "noticeId": "SAM-TEST-002",
        "title": "Consulting Services",
        "type": "Solicitation",
        "description": "Another test opportunity",
        "responseDeadLine": "2025-07-01",
        "naicsCode": "541611",
    },
]


class TestSAMGovCollectEndpoint:
    def test_requires_auth(self, client):
        response = client.post("/sam-gov/collect", json={"naics_codes": ["541511"]})
        assert response.status_code in (401, 403)

    @patch.dict("os.environ", {"SAM_GOV_API_KEY": ""}, clear=False)
    def test_requires_api_key_configured(self, client, admin_headers):
        with patch.dict("os.environ", {"SAM_GOV_API_KEY": ""}, clear=False):
            response = client.post(
                "/sam-gov/collect",
                json={"naics_codes": ["541511"]},
                headers=admin_headers,
            )
        assert response.status_code == 503
        assert "SAM_GOV_API_KEY" in response.json()["detail"]

    def test_requires_naics_codes(self, client, admin_headers):
        response = client.post(
            "/sam-gov/collect",
            json={"naics_codes": []},
            headers=admin_headers,
        )
        assert response.status_code == 422

    @patch("app.routers.sam_gov.collect_opportunities")
    @patch.dict("os.environ", {"SAM_GOV_API_KEY": "test-key-123"})
    def test_successful_collection(self, mock_collect, client, admin_headers):
        mock_collect.return_value = SAMPLE_OPPORTUNITIES

        response = client.post(
            "/sam-gov/collect",
            json={"naics_codes": ["541511"], "days_back": 7},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["opportunities_fetched"] == 2
        assert data["contracts_created"] == 2
        assert data["contracts_skipped"] == 0
        assert data["contacts_created"] == 1  # one POC had email+name

    @patch("app.routers.sam_gov.collect_opportunities")
    @patch.dict("os.environ", {"SAM_GOV_API_KEY": "test-key-123"})
    def test_deduplication(self, mock_collect, client, admin_headers):
        mock_collect.return_value = SAMPLE_OPPORTUNITIES

        # First collection
        response1 = client.post(
            "/sam-gov/collect",
            json={"naics_codes": ["541511"]},
            headers=admin_headers,
        )
        assert response1.json()["contracts_created"] == 2

        # Second collection with same data
        response2 = client.post(
            "/sam-gov/collect",
            json={"naics_codes": ["541511"]},
            headers=admin_headers,
        )
        assert response2.json()["contracts_created"] == 0
        assert response2.json()["contracts_skipped"] == 2

    @patch("app.routers.sam_gov.collect_opportunities")
    @patch.dict("os.environ", {"SAM_GOV_API_KEY": "test-key-123"})
    def test_no_contacts_when_disabled(self, mock_collect, client, admin_headers):
        mock_collect.return_value = SAMPLE_OPPORTUNITIES

        response = client.post(
            "/sam-gov/collect",
            json={"naics_codes": ["541511"], "auto_create_contacts": False},
            headers=admin_headers,
        )

        assert response.status_code == 200
        assert response.json()["contacts_created"] == 0

    @patch("app.routers.sam_gov.collect_opportunities")
    @patch.dict("os.environ", {"SAM_GOV_API_KEY": "test-key-123"})
    def test_handles_missing_deadline(self, mock_collect, client, admin_headers):
        mock_collect.return_value = [
            {
                "noticeId": "NO-DEADLINE",
                "title": "No Deadline Opp",
                "type": "Solicitation",
            }
        ]

        response = client.post(
            "/sam-gov/collect",
            json={"naics_codes": ["541511"]},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Opportunities don't require a deadline, import succeeds
        assert data["contracts_created"] == 1
        assert len(data["errors"]) == 0

    @patch("app.routers.sam_gov.collect_opportunities")
    @patch.dict("os.environ", {"SAM_GOV_API_KEY": "test-key-123"})
    def test_handles_empty_results(self, mock_collect, client, admin_headers):
        mock_collect.return_value = []

        response = client.post(
            "/sam-gov/collect",
            json={"naics_codes": ["541511"]},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["opportunities_fetched"] == 0
        assert data["contracts_created"] == 0

    @patch("app.routers.sam_gov.collect_opportunities", side_effect=ValueError("bad input"))
    @patch.dict("os.environ", {"SAM_GOV_API_KEY": "test-key-123"})
    def test_handles_value_error(self, mock_collect, client, admin_headers):
        response = client.post(
            "/sam-gov/collect",
            json={"naics_codes": ["541511"]},
            headers=admin_headers,
        )
        assert response.status_code == 422

    @patch(
        "app.routers.sam_gov.collect_opportunities",
        side_effect=ConnectionError("network fail"),
    )
    @patch.dict("os.environ", {"SAM_GOV_API_KEY": "test-key-123"})
    def test_handles_api_error(self, mock_collect, client, admin_headers):
        response = client.post(
            "/sam-gov/collect",
            json={"naics_codes": ["541511"]},
            headers=admin_headers,
        )
        assert response.status_code == 502

    @patch("app.routers.sam_gov.collect_opportunities")
    @patch.dict("os.environ", {"SAM_GOV_API_KEY": "test-key-123"})
    def test_api_key_auth(self, mock_collect, client, user_with_api_key):
        _, raw_key = user_with_api_key
        mock_collect.return_value = []

        response = client.post(
            "/sam-gov/collect",
            json={"naics_codes": ["541511"]},
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        assert response.status_code == 200

    @patch("app.routers.sam_gov.collect_opportunities")
    @patch.dict("os.environ", {"SAM_GOV_API_KEY": "test-key-123"})
    def test_opp_without_notice_id_skipped(self, mock_collect, client, admin_headers):
        mock_collect.return_value = [
            {"title": "No ID", "responseDeadLine": "2025-06-01"},
        ]

        response = client.post(
            "/sam-gov/collect",
            json={"naics_codes": ["541511"]},
            headers=admin_headers,
        )

        data = response.json()
        assert data["contracts_created"] == 0

    def test_import_exception_captured_in_errors(self):
        """An exception during individual opportunity import is captured, not raised."""
        from app.services.import_service import import_opportunities

        mock_db = MagicMock()
        mock_savepoint = MagicMock()
        mock_savepoint.commit.side_effect = Exception("db boom")
        mock_db.begin_nested.return_value = mock_savepoint
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_user = MagicMock()
        mock_user.id = "user-123"

        result = import_opportunities(
            opportunities=[
                {
                    "noticeId": "EXCEPT-001",
                    "title": "Exploding Opp",
                    "responseDeadLine": "2025-06-01",
                }
            ],
            auto_create_contacts=False,
            current_user=mock_user,
            db=mock_db,
        )

        assert result["contracts_created"] == 0
        assert any("db boom" in e for e in result["errors"])

    def test_commit_failure_returns_500(self):
        """If the final commit fails, a 500 error is returned."""
        from fastapi import HTTPException

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
                        "noticeId": "FAIL-001",
                        "title": "Fail",
                        "responseDeadLine": "2025-06-01",
                    }
                ],
                auto_create_contacts=False,
                current_user=mock_user,
                db=mock_db,
            )
        assert exc_info.value.status_code == 500

    @patch("app.routers.sam_gov.collect_opportunities")
    @patch.dict("os.environ", {"SAM_GOV_API_KEY": "test-key-123"})
    def test_existing_contact_reused(self, mock_collect, client, admin_headers, db, admin_user):
        """When a contact with matching email exists, it's linked rather than duplicated."""
        from app.models.models import Contact
        from app.utils import generate_id

        existing = Contact(
            id=generate_id(),
            first_name="Jane",
            last_name="Smith",
            email="poc@agency.gov",
            phone="555-0100",
            organization="Agency",
            contact_type="government",
            status="warm",
            assigned_user_id=admin_user.id,
        )
        db.add(existing)
        db.commit()

        mock_collect.return_value = [SAMPLE_OPPORTUNITIES[0]]

        response = client.post(
            "/sam-gov/collect",
            json={"naics_codes": ["541511"]},
            headers=admin_headers,
        )

        data = response.json()
        assert data["contacts_created"] == 0  # reused existing
        assert data["contracts_created"] == 1

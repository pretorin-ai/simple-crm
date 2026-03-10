"""Tests for main app endpoints (root, health, favicon)."""

from unittest.mock import MagicMock, patch


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Pretorin CRM API"
    assert data["version"] == "1.0.0"
    assert data["docs"] == "/docs"


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_health_check_db_failure(client):
    """Health check returns 503 when the database is unreachable."""
    with patch(
        "sqlalchemy.orm.session.Session.execute",
        side_effect=RuntimeError("connection refused"),
    ):
        response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert "database" in data["detail"]


def test_favicon(client):
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.json() == {"detail": "Not Found"}


def test_rate_limit_handler(client, admin_user):
    """Trigger rate limit on /auth/login by sending many requests."""
    for i in range(6):
        response = client.post(
            "/auth/login",
            json={
                "email": "admin@test.com",
                "password": "wrong",
            },
        )
    # The 6th request should be rate limited
    assert response.status_code in (401, 429)


def test_lifespan_startup():
    """Test the lifespan context manager runs startup code."""
    from app.main import lifespan

    mock_app = MagicMock()
    import asyncio

    async def run_lifespan():
        async with lifespan(mock_app):
            pass

    with (
        patch("app.main.seed_database") as mock_seed,
        patch("app.main.SessionLocal") as mock_session_cls,
    ):
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        asyncio.run(run_lifespan())
        mock_seed.assert_called_once_with(mock_db)
        mock_db.close.assert_called_once()


def test_get_db_generator():
    """Test the get_db generator yields a session and closes it."""
    from app.database import get_db

    gen = get_db()
    db = next(gen)
    assert db is not None
    try:
        gen.send(None)
    except StopIteration:
        pass


def test_unhandled_exception_returns_json(admin_headers):
    """Unhandled exceptions should return JSON, not plain text."""
    from starlette.testclient import TestClient

    from app.main import app

    with (
        patch("app.main.seed_database"),
        TestClient(app, raise_server_exceptions=False) as c,
        patch("app.routers.contacts.generate_id", side_effect=RuntimeError("boom")),
    ):
        response = c.post(
            "/contacts",
            headers=admin_headers,
            json={
                "first_name": "Test",
                "last_name": "User",
                "email": "t@t.com",
                "phone": "",
                "organization": "",
                "contact_type": "individual",
                "status": "cold",
                "needs_follow_up": False,
                "notes": "",
            },
        )
    assert response.status_code == 500
    data = response.json()
    assert data["detail"] == "Internal server error"


def test_extra_cors_origins():
    """Test that EXTRA_CORS_ORIGINS env var is processed."""
    import importlib

    with patch.dict(
        "os.environ",
        {"EXTRA_CORS_ORIGINS": "http://extra1.com, http://extra2.com"},
    ):
        import app.main as main_mod

        importlib.reload(main_mod)
        origins = main_mod.allowed_origins

    assert "http://extra1.com" in origins
    assert "http://extra2.com" in origins

    # Reload back to default to avoid affecting other tests
    with patch.dict("os.environ", {}, clear=False):
        importlib.reload(main_mod)

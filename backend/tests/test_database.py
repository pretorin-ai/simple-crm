"""Tests for database configuration."""

from unittest.mock import patch


def test_sqlite_no_pool_kwargs():
    """SQLite engine should not use PostgreSQL pool settings."""
    with patch.dict("os.environ", {"DATABASE_URL": "sqlite:///test.db"}):
        import importlib

        import app.database as db_mod

        importlib.reload(db_mod)
        # SQLite uses StaticPool or QueuePool without pool_pre_ping
        # Just verify it doesn't set PostgreSQL-specific pool args
        pool = db_mod.engine.pool
        # SQLite should NOT have pool_pre_ping set (or it should be falsy)
        assert not getattr(pool, "_pre_ping", False)

    # Reload back to default
    importlib.reload(db_mod)


def test_postgres_pool_config():
    """PostgreSQL engine should have pool tuning configured."""
    with patch.dict(
        "os.environ",
        {"DATABASE_URL": "postgresql://u:p@localhost/db"},
    ):
        import importlib

        import app.database as db_mod

        importlib.reload(db_mod)
        pool = db_mod.engine.pool
        assert pool.size() == 10
        assert pool._max_overflow == 20
        assert pool._pre_ping is True
        assert pool._recycle == 3600

    # Reload back to default
    importlib.reload(db_mod)

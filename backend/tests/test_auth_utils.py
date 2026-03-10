"""Tests for auth utility functions."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import jwt
import pytest
from fastapi import HTTPException

from app.auth import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_refresh_token,
    generate_api_key,
    generate_password_reset_token,
    get_password_hash,
    hash_api_key,
    hash_token,
    validate_password,
    verify_password,
    verify_reset_token,
)
from app.models.models import User
from app.utils import generate_id


def test_get_password_hash():
    hashed = get_password_hash("testpassword")
    assert hashed != "testpassword"
    assert hashed.startswith("$2b$")


def test_verify_password_correct():
    hashed = get_password_hash("testpassword")
    assert verify_password("testpassword", hashed) is True


def test_verify_password_incorrect():
    hashed = get_password_hash("testpassword")
    assert verify_password("wrongpassword", hashed) is False


def test_create_access_token_with_expiry():
    data = {"sub": "test@example.com"}
    delta = timedelta(minutes=30)
    token = create_access_token(data=data, expires_delta=delta)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "test@example.com"
    assert "exp" in payload


def test_create_access_token_default_expiry():
    data = {"sub": "test@example.com"}
    token = create_access_token(data=data)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "test@example.com"


def test_hash_api_key():
    key = "crm_abc123"
    result = hash_api_key(key)
    # HMAC-SHA256 should produce deterministic output
    assert len(result) == 64  # SHA256 hex digest length
    assert hash_api_key(key) == result  # Same input, same output
    assert hash_api_key("crm_different") != result  # Different input, different output


def test_generate_api_key():
    key = generate_api_key()
    assert key.startswith("crm_")
    assert len(key) == 4 + 48  # "crm_" + 48 hex chars


def test_generate_api_key_unique():
    key1 = generate_api_key()
    key2 = generate_api_key()
    assert key1 != key2


def test_generate_password_reset_token():
    token = generate_password_reset_token()
    assert isinstance(token, str)
    assert len(token) > 20


def test_generate_password_reset_token_unique():
    t1 = generate_password_reset_token()
    t2 = generate_password_reset_token()
    assert t1 != t2


def test_create_password_reset_token(db):
    user = User(
        id=generate_id(),
        email="reset@test.com",
        name="Reset User",
        hashed_password=get_password_hash("password123"),
        role="user",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()

    token = create_password_reset_token(user, db)
    assert isinstance(token, str)
    db.refresh(user)
    # Token is now hashed before storage
    assert user.password_reset_token == hash_token(token)
    assert user.password_reset_expires is not None


def test_verify_reset_token_valid(db):
    raw_token = "validtoken123"
    user = User(
        id=generate_id(),
        email="verify@test.com",
        name="Verify User",
        hashed_password=get_password_hash("password123"),
        role="user",
        is_active=True,
        password_reset_token=hash_token(raw_token),
        password_reset_expires=datetime.now(timezone.utc) + timedelta(hours=24),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()

    result = verify_reset_token(raw_token, db)
    assert result is not None
    assert result.email == "verify@test.com"


def test_verify_reset_token_expired(db):
    raw_token = "expiredtoken"
    user = User(
        id=generate_id(),
        email="expired@test.com",
        name="Expired User",
        hashed_password=get_password_hash("password123"),
        role="user",
        is_active=True,
        password_reset_token=hash_token(raw_token),
        password_reset_expires=datetime.now(timezone.utc) - timedelta(hours=1),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()

    result = verify_reset_token(raw_token, db)
    assert result is None


def test_verify_reset_token_invalid(db):
    result = verify_reset_token("nonexistent_token", db)
    assert result is None


def test_validate_password_valid():
    validate_password("validpass123")  # Should not raise


def test_validate_password_too_short():
    with pytest.raises(HTTPException) as exc_info:
        validate_password("short")
    assert exc_info.value.status_code == 400
    assert "8 characters" in exc_info.value.detail


def test_validate_password_exactly_8():
    validate_password("12345678")  # Should not raise


def test_validate_password_empty():
    with pytest.raises(HTTPException):
        validate_password("")


def test_get_user_from_api_key_valid(db):
    """Test get_user_from_api_key with a valid API key."""
    from app.auth import generate_api_key, get_user_from_api_key, hash_api_key

    raw_key = generate_api_key()
    user = User(
        id=generate_id(),
        email="apitest@test.com",
        name="API Test",
        hashed_password=get_password_hash("password123"),
        role="user",
        is_active=True,
        api_key_hash=hash_api_key(raw_key),
        api_key_prefix=raw_key[:12] + "...",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()

    creds = MagicMock()
    creds.credentials = raw_key
    result = get_user_from_api_key(credentials=creds, db=db)
    assert result is not None
    assert result.email == "apitest@test.com"


def test_get_user_from_api_key_invalid(db):
    """Test get_user_from_api_key with an invalid API key."""
    from app.auth import get_user_from_api_key

    creds = MagicMock()
    creds.credentials = "crm_invalidkey"
    result = get_user_from_api_key(credentials=creds, db=db)
    assert result is None


def test_get_user_from_api_key_not_api_key(db):
    """Test get_user_from_api_key with a JWT-style token."""
    from app.auth import get_user_from_api_key

    creds = MagicMock()
    creds.credentials = "some.jwt.token"
    result = get_user_from_api_key(credentials=creds, db=db)
    assert result is None


def test_get_user_from_api_key_inactive_user(db):
    """Inactive user's API key should return None."""
    from app.auth import generate_api_key, get_user_from_api_key, hash_api_key

    raw_key = generate_api_key()
    user = User(
        id=generate_id(),
        email="inactive_api@test.com",
        name="Inactive API",
        hashed_password=get_password_hash("password123"),
        role="user",
        is_active=False,
        api_key_hash=hash_api_key(raw_key),
        api_key_prefix=raw_key[:12] + "...",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()

    creds = MagicMock()
    creds.credentials = raw_key
    result = get_user_from_api_key(credentials=creds, db=db)
    assert result is None


def test_get_user_from_api_key_exception(db):
    """Test get_user_from_api_key handles exceptions gracefully."""
    from app.auth import get_user_from_api_key

    creds = MagicMock()
    creds.credentials = property(lambda self: (_ for _ in ()).throw(Exception("boom")))
    # Accessing .credentials raises
    result = get_user_from_api_key(credentials=creds, db=db)
    assert result is None


# --- Refresh token tests ---


def test_create_refresh_token():
    token = create_refresh_token(data={"sub": "test@example.com"})
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "test@example.com"
    assert payload["type"] == "refresh"


def test_create_refresh_token_custom_expiry():
    token = create_refresh_token(data={"sub": "test@example.com"}, expires_delta=timedelta(days=1))
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "test@example.com"
    assert payload["type"] == "refresh"


def test_decode_refresh_token_valid():
    token = create_refresh_token(data={"sub": "test@example.com"})
    email = decode_refresh_token(token)
    assert email == "test@example.com"


def test_decode_refresh_token_invalid():
    assert decode_refresh_token("invalid.token.here") is None


def test_decode_refresh_token_wrong_type():
    """Access tokens should not be accepted as refresh tokens."""
    access = create_access_token(data={"sub": "test@example.com"})
    assert decode_refresh_token(access) is None


def test_decode_refresh_token_expired():
    token = create_refresh_token(
        data={"sub": "test@example.com"}, expires_delta=timedelta(seconds=-1)
    )
    assert decode_refresh_token(token) is None

"""Tests for token encryption module."""

from unittest.mock import patch

from cryptography.fernet import Fernet

from app.encryption import decrypt_value, encrypt_value, is_encryption_configured


class TestWithoutKey:
    """Tests when TOKEN_ENCRYPTION_KEY is not set."""

    def test_encrypt_returns_plaintext(self):
        with (
            patch("app.encryption._fernet", None),
            patch("app.encryption.TOKEN_ENCRYPTION_KEY", ""),
        ):
            assert encrypt_value("secret") == "secret"

    def test_decrypt_returns_plaintext(self):
        with (
            patch("app.encryption._fernet", None),
            patch("app.encryption.TOKEN_ENCRYPTION_KEY", ""),
        ):
            assert decrypt_value("secret") == "secret"

    def test_is_encryption_configured_false(self):
        with (
            patch("app.encryption._fernet", None),
            patch("app.encryption.TOKEN_ENCRYPTION_KEY", ""),
        ):
            assert is_encryption_configured() is False


class TestWithValidKey:
    """Tests when TOKEN_ENCRYPTION_KEY is set to a valid Fernet key."""

    def setup_method(self):
        self.key = Fernet.generate_key().decode()
        self.fernet = Fernet(self.key.encode())

    def test_encrypt_decrypt_roundtrip(self):
        with (
            patch("app.encryption._fernet", self.fernet),
            patch("app.encryption.TOKEN_ENCRYPTION_KEY", self.key),
        ):
            encrypted = encrypt_value("my_access_token")
            assert encrypted != "my_access_token"
            decrypted = decrypt_value(encrypted)
            assert decrypted == "my_access_token"

    def test_is_encryption_configured_true(self):
        with (
            patch("app.encryption._fernet", self.fernet),
            patch("app.encryption.TOKEN_ENCRYPTION_KEY", self.key),
        ):
            assert is_encryption_configured() is True

    def test_decrypt_unencrypted_value_returns_as_is(self):
        """Supports migration path: values stored before encryption was enabled."""
        with (
            patch("app.encryption._fernet", self.fernet),
            patch("app.encryption.TOKEN_ENCRYPTION_KEY", self.key),
        ):
            result = decrypt_value("plain_text_token")
            assert result == "plain_text_token"


class TestWithInvalidKey:
    """Tests when TOKEN_ENCRYPTION_KEY is invalid."""

    def test_invalid_key_falls_back_to_passthrough(self):
        import app.encryption as enc

        original_fernet = enc._fernet
        original_key = enc.TOKEN_ENCRYPTION_KEY
        try:
            enc._fernet = None
            enc.TOKEN_ENCRYPTION_KEY = "not-a-valid-fernet-key"
            assert encrypt_value("secret") == "secret"
            assert decrypt_value("secret") == "secret"
            assert is_encryption_configured() is False
        finally:
            enc._fernet = original_fernet
            enc.TOKEN_ENCRYPTION_KEY = original_key


class TestGetFernetCaching:
    """Test that _get_fernet caches the Fernet instance."""

    def test_fernet_is_cached(self):
        import app.encryption as enc

        key = Fernet.generate_key().decode()
        original_fernet = enc._fernet
        original_key = enc.TOKEN_ENCRYPTION_KEY
        try:
            enc._fernet = None
            enc.TOKEN_ENCRYPTION_KEY = key
            result1 = enc._get_fernet()
            result2 = enc._get_fernet()
            assert result1 is result2
            assert result1 is not None
        finally:
            enc._fernet = original_fernet
            enc.TOKEN_ENCRYPTION_KEY = original_key

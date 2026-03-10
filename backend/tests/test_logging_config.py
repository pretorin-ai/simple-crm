"""Tests for structured JSON logging and request ID correlation."""

import json
import logging
from unittest.mock import patch

from app.logging_config import (
    RequestIdFilter,
    generate_request_id,
    request_id_ctx,
    setup_logging,
)


def test_generate_request_id_length():
    rid = generate_request_id()
    assert len(rid) == 16
    assert rid.isalnum()


def test_generate_request_id_unique():
    ids = {generate_request_id() for _ in range(100)}
    assert len(ids) == 100


def test_request_id_filter_injects_context():
    token = request_id_ctx.set("abc123")
    try:
        f = RequestIdFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        assert f.filter(record) is True
        assert record.request_id == "abc123"  # type: ignore[attr-defined]
    finally:
        request_id_ctx.reset(token)


def test_request_id_filter_default_empty():
    f = RequestIdFilter()
    record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
    f.filter(record)
    assert record.request_id == ""  # type: ignore[attr-defined]


def test_setup_logging_configures_json_handler():
    setup_logging()
    root = logging.getLogger()
    assert len(root.handlers) >= 1
    handler = root.handlers[0]
    # Verify JSON formatter is attached
    from pythonjsonlogger.json import JsonFormatter

    assert isinstance(handler.formatter, JsonFormatter)


def test_setup_logging_respects_log_level():
    with patch.dict("os.environ", {"LOG_LEVEL": "DEBUG"}):
        setup_logging()
    assert logging.getLogger().level == logging.DEBUG
    # Reset
    with patch.dict("os.environ", {"LOG_LEVEL": "INFO"}):
        setup_logging()


def test_json_log_output(capfd):
    """Verify log output is valid JSON with expected fields."""
    setup_logging()
    token = request_id_ctx.set("test-rid-123")
    try:
        test_logger = logging.getLogger("test.json_output")
        test_logger.info("hello world")
    finally:
        request_id_ctx.reset(token)
    captured = capfd.readouterr()
    line = captured.err.strip()
    data = json.loads(line)
    assert data["message"] == "hello world"
    assert data["request_id"] == "test-rid-123"
    assert "timestamp" in data
    assert data["level"] == "INFO"

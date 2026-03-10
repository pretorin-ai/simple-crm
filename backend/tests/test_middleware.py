"""Tests for request ID middleware and Prometheus metrics."""


def test_request_id_generated(client):
    """Every response should include an X-Request-ID header."""
    response = client.get("/health")
    rid = response.headers.get("X-Request-ID")
    assert rid is not None
    assert len(rid) == 16


def test_request_id_echoed(client):
    """Client-provided X-Request-ID should be echoed back."""
    response = client.get("/health", headers={"X-Request-ID": "my-custom-id"})
    assert response.headers["X-Request-ID"] == "my-custom-id"


def test_metrics_endpoint(client):
    """Prometheus /metrics endpoint should return text metrics."""
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "http_requests_total" in body or "http_request_duration" in body

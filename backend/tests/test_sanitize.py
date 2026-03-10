"""Tests for HTML sanitization module."""

from app.sanitize import sanitize_html


def test_strips_script_tags():
    html = '<p>Hello</p><script>alert("xss")</script>'
    result = sanitize_html(html)
    assert "<script>" not in result
    assert "<p>Hello</p>" in result


def test_strips_event_handlers():
    html = '<img src="x" onerror="alert(1)">'
    result = sanitize_html(html)
    assert "onerror" not in result


def test_preserves_safe_tags():
    html = "<p>Hello <strong>world</strong></p>"
    assert sanitize_html(html) == html


def test_preserves_links():
    html = '<a href="https://example.com" title="Example">Link</a>'
    result = sanitize_html(html)
    assert 'href="https://example.com"' in result
    assert ">Link</a>" in result


def test_preserves_images():
    html = '<img src="https://example.com/img.png" alt="Logo">'
    result = sanitize_html(html)
    assert "src=" in result
    assert "alt=" in result


def test_preserves_tables():
    html = (
        "<table><thead><tr><th>Header</th></tr></thead>"
        "<tbody><tr><td>Cell</td></tr></tbody></table>"
    )
    result = sanitize_html(html)
    assert "<table>" in result
    assert "<td>Cell</td>" in result


def test_strips_javascript_protocol():
    html = '<a href="javascript:alert(1)">Click</a>'
    result = sanitize_html(html)
    assert "javascript:" not in result


def test_empty_string_passthrough():
    assert sanitize_html("") == ""


def test_none_passthrough():
    assert sanitize_html(None) is None


def test_strips_style_attribute():
    """Style attributes are stripped to prevent CSS-based attacks."""
    html = '<span style="color: red">Red text</span>'
    result = sanitize_html(html)
    assert "style=" not in result
    assert "<span>Red text</span>" in result


def test_strips_iframe():
    html = '<iframe src="https://evil.com"></iframe><p>Safe</p>'
    result = sanitize_html(html)
    assert "<iframe" not in result
    assert "<p>Safe</p>" in result

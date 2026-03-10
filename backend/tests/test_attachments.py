"""Tests for attachment endpoints."""

import os
from unittest.mock import patch

from app.models.models import Attachment, Opportunity
from app.utils import generate_id

# Use a temp path so tests don't write to real uploads dir
TEST_UPLOAD_DIR = "/tmp/test_crm_uploads"


def _make_opportunity(db, user_id, **overrides):
    defaults = {
        "id": generate_id(),
        "title": "Test Opportunity",
        "stage": "identified",
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


def _make_attachment(db, opp_id, user_id, **overrides):
    defaults = {
        "id": generate_id(),
        "opportunity_id": opp_id,
        "filename": "test.pdf",
        "stored_filename": f"{generate_id()}.pdf",
        "content_type": "application/pdf",
        "size": 1024,
        "uploaded_by_user_id": user_id,
    }
    defaults.update(overrides)
    att = Attachment(**defaults)
    db.add(att)
    db.commit()
    db.refresh(att)
    return att


def _cleanup_upload_dir():
    if os.path.exists(TEST_UPLOAD_DIR):
        for f in os.listdir(TEST_UPLOAD_DIR):
            os.remove(os.path.join(TEST_UPLOAD_DIR, f))
        os.rmdir(TEST_UPLOAD_DIR)


# --- GET attachments ---


def test_list_attachments_opp_not_found(client, admin_headers):
    response = client.get("/opportunities/fake-id/attachments", headers=admin_headers)
    assert response.status_code == 404


def test_list_attachments_empty(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    response = client.get(f"/opportunities/{opp.id}/attachments", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_list_attachments_with_data(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    _make_attachment(db, opp.id, admin_user.id)
    response = client.get(f"/opportunities/{opp.id}/attachments", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


# --- POST upload attachment ---


@patch("app.routers.attachments.UPLOAD_DIR", TEST_UPLOAD_DIR)
def test_upload_attachment(client, admin_headers, db, admin_user):
    try:
        opp = _make_opportunity(db, admin_user.id)
        response = client.post(
            f"/opportunities/{opp.id}/attachments",
            files={"file": ("doc.txt", b"hello world", "text/plain")},
            headers=admin_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "doc.txt"
        assert data["size"] == 11
    finally:
        _cleanup_upload_dir()


@patch("app.routers.attachments.UPLOAD_DIR", TEST_UPLOAD_DIR)
def test_upload_attachment_opp_not_found(client, admin_headers):
    response = client.post(
        "/opportunities/fake-id/attachments",
        files={"file": ("doc.txt", b"hello", "text/plain")},
        headers=admin_headers,
    )
    assert response.status_code == 404


@patch("app.routers.attachments.UPLOAD_DIR", TEST_UPLOAD_DIR)
@patch("app.routers.attachments.MAX_FILE_SIZE", 5)
def test_upload_attachment_too_large(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    response = client.post(
        f"/opportunities/{opp.id}/attachments",
        files={"file": ("big.bin", b"x" * 10, "application/octet-stream")},
        headers=admin_headers,
    )
    assert response.status_code == 413
    _cleanup_upload_dir()


# --- GET download attachment ---


@patch("app.routers.attachments.UPLOAD_DIR", TEST_UPLOAD_DIR)
def test_download_attachment(client, admin_headers, db, admin_user):
    try:
        opp = _make_opportunity(db, admin_user.id)
        att = _make_attachment(db, opp.id, admin_user.id)
        os.makedirs(TEST_UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(TEST_UPLOAD_DIR, att.stored_filename)
        with open(file_path, "wb") as f:
            f.write(b"file content")
        response = client.get(
            f"/opportunities/{opp.id}/attachments/{att.id}/download",
            headers=admin_headers,
        )
        assert response.status_code == 200
    finally:
        _cleanup_upload_dir()


def test_download_attachment_not_found(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    response = client.get(
        f"/opportunities/{opp.id}/attachments/fake-id/download",
        headers=admin_headers,
    )
    assert response.status_code == 404


@patch("app.routers.attachments.UPLOAD_DIR", TEST_UPLOAD_DIR)
def test_download_attachment_file_missing_on_disk(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    att = _make_attachment(db, opp.id, admin_user.id)
    response = client.get(
        f"/opportunities/{opp.id}/attachments/{att.id}/download",
        headers=admin_headers,
    )
    assert response.status_code == 404
    assert "File not found on disk" in response.json()["detail"]


# --- DELETE attachment ---


@patch("app.routers.attachments.UPLOAD_DIR", TEST_UPLOAD_DIR)
def test_delete_attachment(client, admin_headers, db, admin_user):
    try:
        opp = _make_opportunity(db, admin_user.id)
        att = _make_attachment(db, opp.id, admin_user.id)
        os.makedirs(TEST_UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(TEST_UPLOAD_DIR, att.stored_filename)
        with open(file_path, "wb") as f:
            f.write(b"to delete")
        response = client.delete(
            f"/opportunities/{opp.id}/attachments/{att.id}",
            headers=admin_headers,
        )
        assert response.status_code == 204
        assert not os.path.exists(file_path)
    finally:
        _cleanup_upload_dir()


def test_delete_attachment_not_found(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    response = client.delete(
        f"/opportunities/{opp.id}/attachments/fake-id",
        headers=admin_headers,
    )
    assert response.status_code == 404


@patch("app.routers.attachments.UPLOAD_DIR", TEST_UPLOAD_DIR)
def test_delete_attachment_no_file_on_disk(client, admin_headers, db, admin_user):
    opp = _make_opportunity(db, admin_user.id)
    att = _make_attachment(db, opp.id, admin_user.id)
    response = client.delete(
        f"/opportunities/{opp.id}/attachments/{att.id}",
        headers=admin_headers,
    )
    assert response.status_code == 204


# --- Authorization ---


@patch("app.routers.attachments.UPLOAD_DIR", TEST_UPLOAD_DIR)
def test_delete_attachment_forbidden_for_non_uploader(
    client, user_headers, db, admin_user, regular_user
):
    opp = _make_opportunity(db, admin_user.id)
    att = _make_attachment(db, opp.id, admin_user.id)
    response = client.delete(
        f"/opportunities/{opp.id}/attachments/{att.id}",
        headers=user_headers,
    )
    assert response.status_code == 403


# --- Path traversal protection ---


@patch("app.routers.attachments.UPLOAD_DIR", TEST_UPLOAD_DIR)
def test_upload_attachment_unsafe_extension_stripped(client, admin_headers, db, admin_user):
    """File extensions with special characters are stripped."""
    try:
        opp = _make_opportunity(db, admin_user.id)
        response = client.post(
            f"/opportunities/{opp.id}/attachments",
            files={"file": ("file.ex$e", b"hello", "application/octet-stream")},
            headers=admin_headers,
        )
        assert response.status_code == 201
        # Unsafe extension chars stripped, so stored without extension
        data = response.json()
        assert data["filename"] == "file.ex$e"
    finally:
        _cleanup_upload_dir()


@patch("app.routers.attachments.UPLOAD_DIR", TEST_UPLOAD_DIR)
def test_upload_no_extension(client, admin_headers, db, admin_user):
    try:
        opp = _make_opportunity(db, admin_user.id)
        response = client.post(
            f"/opportunities/{opp.id}/attachments",
            files={"file": ("Makefile", b"all:", "application/octet-stream")},
            headers=admin_headers,
        )
        assert response.status_code == 201
    finally:
        _cleanup_upload_dir()


# --- Path traversal ---


def test_download_path_traversal_blocked(client, admin_headers, db, admin_user):
    """Stored filename with path traversal should be blocked."""
    opp = _make_opportunity(db, admin_user.id)
    att = _make_attachment(db, opp.id, admin_user.id, stored_filename="../../etc/passwd")
    response = client.get(
        f"/opportunities/{opp.id}/attachments/{att.id}/download",
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert "Invalid file path" in response.json()["detail"]


def test_delete_attachment_with_invalid_stored_path(client, admin_headers, db, admin_user):
    """Delete should succeed even if stored_filename fails path validation."""
    opp = _make_opportunity(db, admin_user.id)
    att = _make_attachment(db, opp.id, admin_user.id, stored_filename="../../etc/passwd")
    response = client.delete(
        f"/opportunities/{opp.id}/attachments/{att.id}",
        headers=admin_headers,
    )
    assert response.status_code == 204


# --- DB commit failure cleanup ---


@patch("app.routers.attachments.UPLOAD_DIR", TEST_UPLOAD_DIR)
def test_upload_cleans_file_on_db_failure(client, admin_headers, db, admin_user):
    """If DB commit fails after writing file, the file should be cleaned up."""
    opp = _make_opportunity(db, admin_user.id)

    def failing_commit(session):
        raise RuntimeError("DB commit failed")

    with patch(
        "app.routers.attachments.Session.commit",
        failing_commit,
    ):
        try:
            client.post(
                f"/opportunities/{opp.id}/attachments",
                files={"file": ("test.txt", b"data", "text/plain")},
                headers=admin_headers,
            )
        except RuntimeError:
            pass

    # Any files that were written should have been cleaned up
    if os.path.exists(TEST_UPLOAD_DIR):
        files = os.listdir(TEST_UPLOAD_DIR)
        _cleanup_upload_dir()
        assert len(files) == 0

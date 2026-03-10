import os
import re
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.database import get_db
from app.models.models import Attachment, Opportunity, User
from app.schemas.schemas import AttachmentSchema
from app.utils import generate_id

router = APIRouter(prefix="/opportunities", tags=["attachments"])

UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "uploads",
)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# Only allow safe characters in file extensions
_SAFE_EXT_RE = re.compile(r"^[a-zA-Z0-9]+$")


def _ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def _safe_file_path(stored_filename: str) -> str:
    """Resolve file path and verify it stays within UPLOAD_DIR."""
    file_path = os.path.join(UPLOAD_DIR, stored_filename)
    real_path = os.path.realpath(file_path)
    real_upload_dir = os.path.realpath(UPLOAD_DIR)
    if not real_path.startswith(real_upload_dir + os.sep) and real_path != real_upload_dir:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path",
        )
    return real_path


def _check_opportunity_access(opportunity_id: str, current_user: User, db: Session):
    """Verify opportunity exists and user has access."""
    opp = (
        db.query(Opportunity)
        .filter(Opportunity.id == opportunity_id, Opportunity.deleted_at.is_(None))
        .first()
    )
    if not opp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found",
        )
    return opp


@router.get(
    "/{opportunity_id}/attachments",
    response_model=List[AttachmentSchema],
)
def list_attachments(
    opportunity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _check_opportunity_access(opportunity_id, current_user, db)
    return (
        db.query(Attachment)
        .filter(Attachment.opportunity_id == opportunity_id)
        .order_by(Attachment.created_at.desc())
        .all()
    )


@router.post(
    "/{opportunity_id}/attachments",
    response_model=AttachmentSchema,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    opportunity_id: str,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _check_opportunity_access(opportunity_id, current_user, db)
    _ensure_upload_dir()

    file_id = generate_id()
    # Safely extract and validate extension
    ext = ""
    if file.filename and "." in file.filename:
        raw_ext = file.filename.rsplit(".", 1)[1][:10]
        if _SAFE_EXT_RE.match(raw_ext):
            ext = "." + raw_ext
    stored_filename = f"{file_id}{ext}"

    # Read and validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File too large. Maximum size is 50 MB.",
        )

    # Write to disk with validated path
    file_path = _safe_file_path(stored_filename)
    with open(file_path, "wb") as f:
        f.write(content)

    attachment = Attachment(
        id=file_id,
        opportunity_id=opportunity_id,
        filename=file.filename or "unnamed",
        stored_filename=stored_filename,
        content_type=file.content_type,
        size=len(content),
        uploaded_by_user_id=current_user.id,
    )
    db.add(attachment)
    try:
        db.commit()
    except Exception:
        # Clean up file if DB commit fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise
    db.refresh(attachment)
    return attachment


@router.get("/{opportunity_id}/attachments/{attachment_id}/download")
def download_attachment(
    opportunity_id: str,
    attachment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    attachment = (
        db.query(Attachment)
        .filter(
            Attachment.id == attachment_id,
            Attachment.opportunity_id == opportunity_id,
        )
        .first()
    )
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    file_path = _safe_file_path(attachment.stored_filename)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk",
        )

    return FileResponse(
        path=file_path,
        filename=attachment.filename,
        media_type=attachment.content_type or "application/octet-stream",
    )


@router.delete(
    "/{opportunity_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_attachment(
    opportunity_id: str,
    attachment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    attachment = (
        db.query(Attachment)
        .filter(
            Attachment.id == attachment_id,
            Attachment.opportunity_id == opportunity_id,
        )
        .first()
    )
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    # Only uploader or admin can delete
    if attachment.uploaded_by_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this attachment",
        )

    # Remove file from disk
    try:
        file_path = _safe_file_path(attachment.stored_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    except HTTPException:
        pass  # File path validation failed, skip disk cleanup

    db.delete(attachment)
    db.commit()
    return None

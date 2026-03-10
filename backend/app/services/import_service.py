"""
Shared import logic for SAM.gov opportunities.

Used by both the manual import endpoint (contracts router)
and the automated collection endpoint (sam_gov router).
"""

import logging
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import Contact, Contract, Opportunity, User
from app.utils import generate_id

logger = logging.getLogger(__name__)


def _parse_deadline(raw_deadline: str | None) -> datetime | None:
    """Parse a deadline string into a datetime, trying multiple formats."""
    if not raw_deadline:
        return None
    # Try ISO format with timezone
    try:
        return datetime.fromisoformat(raw_deadline.replace("Z", "+00:00"))
    except ValueError:
        pass
    # Try date-only format
    try:
        return datetime.strptime(raw_deadline[:10], "%Y-%m-%d")
    except ValueError:
        pass
    return None


def import_opportunities(
    opportunities: list[dict],
    auto_create_contacts: bool,
    current_user: User,
    db: Session,
) -> dict:
    """
    Import SAM.gov opportunities as Opportunity records.

    Accepts a list of opportunity dicts with keys:
        noticeId, title, description, responseDeadLine, solicitationNumber,
        naicsCode, uiLink, pointOfContact, source, notes

    Returns a dict with:
        contracts_created, contracts_skipped, contacts_created, errors.
    (Keys kept as contracts_created/skipped for API compatibility.)
    """
    contracts_created = 0
    contracts_skipped = 0
    contacts_created = 0
    errors: list[str] = []

    # Check for duplicates against both Opportunity and legacy Contract tables
    notice_ids = [opp.get("noticeId") or getattr(opp, "noticeId", None) for opp in opportunities]
    notice_ids = [nid for nid in notice_ids if nid]
    existing_notice_ids: set[str] = set()
    if notice_ids:
        # Check opportunities table
        opp_rows = (
            db.query(Opportunity.sam_gov_notice_id)
            .filter(Opportunity.sam_gov_notice_id.in_(notice_ids))
            .all()
        )
        existing_notice_ids.update(row[0] for row in opp_rows if row[0])
        # Check legacy contracts table
        contract_rows = (
            db.query(Contract.sam_gov_notice_id)
            .filter(Contract.sam_gov_notice_id.in_(notice_ids))
            .all()
        )
        existing_notice_ids.update(row[0] for row in contract_rows if row[0])

    # Batch-load existing contact emails to avoid O(n*m) queries
    all_poc_emails: set[str] = set()
    if auto_create_contacts:
        for opp in opportunities:
            pocs = _get_field(opp, "pointOfContact") or []
            for poc in pocs:
                email = _get_field(poc, "email")
                if email:
                    all_poc_emails.add(email)

    existing_contacts_by_email: dict[str, Contact] = {}
    if all_poc_emails:
        existing_contacts = db.query(Contact).filter(Contact.email.in_(all_poc_emails)).all()
        existing_contacts_by_email = {c.email: c for c in existing_contacts}

    for opp in opportunities:
        notice_id = _get_field(opp, "noticeId")
        if not notice_id:
            continue

        savepoint = db.begin_nested()
        try:
            # Deduplicate
            if notice_id in existing_notice_ids:
                contracts_skipped += 1
                savepoint.rollback()
                continue

            title = (_get_field(opp, "title") or "Untitled Opportunity")[:300]

            # Parse deadline
            raw_deadline = _get_field(opp, "responseDeadLine")
            deadline = _parse_deadline(raw_deadline)

            # Auto-create contacts from point of contact
            if auto_create_contacts:
                pocs = _get_field(opp, "pointOfContact") or []
                for poc in pocs:
                    poc_email = _get_field(poc, "email")
                    poc_name = _get_field(poc, "fullName")
                    if poc_email and poc_name:
                        existing_contact = existing_contacts_by_email.get(poc_email)
                        if not existing_contact:
                            name_parts = poc_name.strip().split()
                            first_name = name_parts[0] if name_parts else "Unknown"
                            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                            new_contact = Contact(
                                id=generate_id(),
                                first_name=first_name,
                                last_name=last_name,
                                email=poc_email,
                                phone=_get_field(poc, "phone") or "",
                                organization=title[:100],
                                contact_type="government",
                                status="warm",
                                needs_follow_up=True,
                                notes=(f"Auto-imported from SAM.gov opportunity: {title}"),
                                assigned_user_id=current_user.id,
                            )
                            db.add(new_contact)
                            db.flush()
                            contacts_created += 1
                            existing_contacts_by_email[poc_email] = new_contact

            sol_num = _get_field(opp, "solicitationNumber")
            naics = _get_field(opp, "naicsCode")

            new_opp = Opportunity(
                id=generate_id(),
                title=title,
                is_government_contract=True,
                description=_get_field(opp, "description") or "",
                agency="",
                solicitation_number=sol_num,
                sam_gov_notice_id=notice_id,
                naics_code=naics,
                submission_link=_get_field(opp, "uiLink"),
                deadline=deadline,
                proposal_due_date=deadline,
                source="sam_gov",
                stage="identified",
                notes=_get_field(opp, "notes") or "",
                created_by_user_id=current_user.id,
            )

            db.add(new_opp)
            savepoint.commit()
            contracts_created += 1
            existing_notice_ids.add(notice_id)

        except Exception as e:
            savepoint.rollback()
            errors.append(f"Error importing {_get_field(opp, 'title') or '?'}: {e}")

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save imports: {e}",
        )

    return {
        "contracts_created": contracts_created,
        "contracts_skipped": contracts_skipped,
        "contacts_created": contacts_created,
        "errors": errors,
    }


def _get_field(obj, field: str):
    """Get a field from either a dict or a Pydantic model / object."""
    if isinstance(obj, dict):
        return obj.get(field)
    return getattr(obj, field, None)

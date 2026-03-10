import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_active_user
from app.database import get_db
from app.models.models import ContractVehicle, Opportunity, Proposal, User
from app.schemas.schemas import (
    Opportunity as OpportunitySchema,
)
from app.schemas.schemas import (
    OpportunityCreate,
    OpportunityPatch,
    OpportunityUpdate,
    PipelineMetrics,
)
from app.utils import generate_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/opportunities", tags=["opportunities"])

# Base filter to exclude soft-deleted opportunities
_active = Opportunity.deleted_at.is_(None)


@router.get("", response_model=List[OpportunitySchema])
def get_opportunities(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    stage: Optional[str] = Query(default=None),
    agency: Optional[str] = Query(default=None),
    naics_code: Optional[str] = Query(default=None),
    set_aside_type: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    min_value: Optional[float] = Query(default=None),
    max_value: Optional[float] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(Opportunity).options(selectinload(Opportunity.vehicles)).filter(_active)

    if stage:
        query = query.filter(Opportunity.stage == stage)
    if agency:
        query = query.filter(Opportunity.agency.ilike(f"%{agency}%"))
    if naics_code:
        query = query.filter(Opportunity.naics_code == naics_code)
    if set_aside_type:
        query = query.filter(Opportunity.set_aside_type == set_aside_type)
    if source:
        query = query.filter(Opportunity.source == source)
    if min_value is not None:
        query = query.filter(Opportunity.estimated_value >= min_value)
    if max_value is not None:
        query = query.filter(Opportunity.estimated_value <= max_value)
    if search:
        query = query.filter(
            Opportunity.title.ilike(f"%{search}%")
            | Opportunity.solicitation_number.ilike(f"%{search}%")
            | Opportunity.agency.ilike(f"%{search}%")
        )

    return query.order_by(Opportunity.updated_at.desc()).offset(skip).limit(limit).all()


@router.get("/pipeline", response_model=PipelineMetrics)
def get_pipeline_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Total count and pipeline value in a single query
    totals = (
        db.query(
            func.count(Opportunity.id).label("total"),
            func.coalesce(func.sum(Opportunity.estimated_value), 0).label("pipeline_value"),
        )
        .filter(_active)
        .first()
    )
    total = totals.total
    pipeline_value = float(totals.pipeline_value)

    # Expected revenue weighted by win probability
    expected_revenue_row = (
        db.query(
            func.coalesce(
                func.sum(Opportunity.estimated_value * Opportunity.win_probability / 100), 0
            ).label("expected"),
        )
        .filter(_active)
        .first()
    )
    expected_revenue = float(expected_revenue_row.expected)

    # Win rate
    awarded = (
        db.query(func.count(Opportunity.id))
        .filter(_active, Opportunity.stage == "awarded")
        .scalar()
    )
    lost = (
        db.query(func.count(Opportunity.id)).filter(_active, Opportunity.stage == "lost").scalar()
    )
    win_rate = (awarded / (awarded + lost) * 100) if (awarded + lost) > 0 else 0

    # Average deal size (excluding zero/null)
    avg_deal = (
        db.query(func.coalesce(func.avg(Opportunity.estimated_value), 0))
        .filter(
            _active,
            Opportunity.estimated_value.isnot(None),
            Opportunity.estimated_value > 0,
        )
        .scalar()
    )

    # By stage (aggregated in SQL)
    stage_rows = (
        db.query(
            Opportunity.stage,
            func.count(Opportunity.id).label("count"),
            func.coalesce(func.sum(Opportunity.estimated_value), 0).label("value"),
        )
        .filter(_active)
        .group_by(Opportunity.stage)
        .all()
    )
    by_stage = {row.stage: {"count": row.count, "value": float(row.value)} for row in stage_rows}

    # By agency (aggregated in SQL)
    agency_rows = (
        db.query(
            func.coalesce(Opportunity.agency, "Unknown").label("agency_name"),
            func.count(Opportunity.id).label("count"),
            func.coalesce(func.sum(Opportunity.estimated_value), 0).label("value"),
        )
        .filter(_active)
        .group_by(func.coalesce(Opportunity.agency, "Unknown"))
        .all()
    )
    by_agency = {
        row.agency_name: {"count": row.count, "value": float(row.value)} for row in agency_rows
    }

    return PipelineMetrics(
        total_opportunities=total,
        pipeline_value=pipeline_value,
        expected_award_revenue=round(expected_revenue, 2),
        win_rate=round(win_rate, 1),
        average_deal_size=round(float(avg_deal), 2),
        by_stage=by_stage,
        by_agency=by_agency,
    )


@router.get("/{opportunity_id}", response_model=OpportunitySchema)
def get_opportunity(
    opportunity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    opportunity = (
        db.query(Opportunity)
        .options(selectinload(Opportunity.vehicles))
        .filter(Opportunity.id == opportunity_id, _active)
        .first()
    )
    if not opportunity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    return opportunity


def _resolve_vehicles(vehicle_ids: List[str], db: Session) -> list:
    if not vehicle_ids:
        return []
    return db.query(ContractVehicle).filter(ContractVehicle.id.in_(vehicle_ids)).all()


def _auto_create_proposal(opp: Opportunity, current_user: User, db: Session):
    """Safely auto-create a proposal, handling concurrent creation."""
    existing = db.query(Proposal).filter(Proposal.opportunity_id == opp.id).first()
    if existing:
        return
    try:
        savepoint = db.begin_nested()
        proposal = Proposal(
            id=generate_id(),
            opportunity_id=opp.id,
            proposal_manager_id=current_user.id,
            status="not_started",
            submission_deadline=opp.proposal_due_date,
        )
        db.add(proposal)
        savepoint.commit()
    except IntegrityError:
        savepoint.rollback()
        logger.info("Proposal already exists for opportunity %s (concurrent creation)", opp.id)


@router.post("", response_model=OpportunitySchema, status_code=status.HTTP_201_CREATED)
def create_opportunity(
    opp: OpportunityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    new_opp = Opportunity(
        id=generate_id(),
        title=opp.title,
        is_government_contract=opp.is_government_contract,
        description=opp.description,
        agency=opp.agency,
        account_id=opp.account_id,
        naics_code=opp.naics_code,
        set_aside_type=opp.set_aside_type,
        estimated_value=opp.estimated_value,
        solicitation_number=opp.solicitation_number,
        sam_gov_notice_id=opp.sam_gov_notice_id,
        submission_link=opp.submission_link,
        deadline=opp.deadline,
        source=opp.source,
        stage=opp.stage,
        capture_manager_id=opp.capture_manager_id or current_user.id,
        expected_release_date=opp.expected_release_date,
        proposal_due_date=opp.proposal_due_date,
        award_date_estimate=opp.award_date_estimate,
        win_probability=opp.win_probability,
        notes=opp.notes,
        created_by_user_id=current_user.id,
    )

    new_opp.vehicles = _resolve_vehicles(opp.vehicle_ids, db)

    # Auto-create proposal when stage is "proposal"
    if opp.stage == "proposal":
        proposal = Proposal(
            id=generate_id(),
            opportunity_id=new_opp.id,
            proposal_manager_id=current_user.id,
            status="not_started",
            submission_deadline=opp.proposal_due_date,
        )
        db.add(proposal)

    db.add(new_opp)
    db.commit()
    db.refresh(new_opp)
    return new_opp


@router.put("/{opportunity_id}", response_model=OpportunitySchema)
def update_opportunity(
    opportunity_id: str,
    opp_update: OpportunityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id, _active).first()
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")

    old_stage = opp.stage

    opp.title = opp_update.title
    opp.is_government_contract = opp_update.is_government_contract
    opp.description = opp_update.description
    opp.agency = opp_update.agency
    opp.account_id = opp_update.account_id
    opp.naics_code = opp_update.naics_code
    opp.set_aside_type = opp_update.set_aside_type
    opp.estimated_value = opp_update.estimated_value
    opp.solicitation_number = opp_update.solicitation_number
    opp.sam_gov_notice_id = opp_update.sam_gov_notice_id
    opp.submission_link = opp_update.submission_link
    opp.deadline = opp_update.deadline
    opp.source = opp_update.source
    opp.stage = opp_update.stage
    opp.capture_manager_id = opp_update.capture_manager_id
    opp.expected_release_date = opp_update.expected_release_date
    opp.proposal_due_date = opp_update.proposal_due_date
    opp.award_date_estimate = opp_update.award_date_estimate
    opp.win_probability = opp_update.win_probability
    opp.notes = opp_update.notes

    opp.vehicles = _resolve_vehicles(opp_update.vehicle_ids, db)

    # Auto-create proposal when moving to proposal stage
    if opp_update.stage == "proposal" and old_stage != "proposal":
        _auto_create_proposal(opp, current_user, db)

    db.commit()
    db.refresh(opp)
    return opp


@router.patch("/{opportunity_id}", response_model=OpportunitySchema)
def patch_opportunity(
    opportunity_id: str,
    updates: OpportunityPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id, _active).first()
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")

    old_stage = opp.stage
    update_data = updates.model_dump(exclude_unset=True)

    if "vehicle_ids" in update_data:
        vehicle_ids = update_data.pop("vehicle_ids")
        opp.vehicles = _resolve_vehicles(vehicle_ids, db)

    for field, value in update_data.items():
        setattr(opp, field, value)

    # Auto-create proposal when moving to proposal stage
    new_stage = update_data.get("stage")
    if new_stage == "proposal" and old_stage != "proposal":
        _auto_create_proposal(opp, current_user, db)

    db.commit()
    db.refresh(opp)
    return opp


@router.delete("/{opportunity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_opportunity(
    opportunity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id, _active).first()
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")

    from app.routers.audit import create_audit_entry

    opp.deleted_at = datetime.now(timezone.utc)
    db.commit()

    create_audit_entry(
        db,
        user_id=current_user.id,
        action="delete",
        entity_type="opportunity",
        entity_id=opportunity_id,
        details=f"Soft-deleted opportunity: {opp.title}",
    )
    return None


@router.post("/{opportunity_id}/restore", response_model=OpportunitySchema)
def restore_opportunity(
    opportunity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Restore a soft-deleted opportunity. Admin only."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    opp = (
        db.query(Opportunity)
        .options(selectinload(Opportunity.vehicles))
        .filter(Opportunity.id == opportunity_id, Opportunity.deleted_at.isnot(None))
        .first()
    )
    if not opp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Deleted opportunity not found"
        )

    from app.routers.audit import create_audit_entry

    opp.deleted_at = None
    db.commit()
    db.refresh(opp)

    create_audit_entry(
        db,
        user_id=current_user.id,
        action="restore",
        entity_type="opportunity",
        entity_id=opportunity_id,
        details=f"Restored opportunity: {opp.title}",
    )
    return opp

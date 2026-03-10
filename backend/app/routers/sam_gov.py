"""
SAM.gov collection endpoints.

Fetches opportunities from the SAM.gov API and imports them as contracts
using the shared import service.
"""

import asyncio
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user_or_api_key
from app.database import get_db
from app.models.models import User
from app.schemas.schemas import (
    SAMGovCollectRequest,
    SAMGovCollectResponse,
)
from app.services.import_service import import_opportunities
from app.services.sam_gov import collect_opportunities

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sam-gov", tags=["sam-gov"])


@router.post("/collect", response_model=SAMGovCollectResponse)
async def collect_samgov_opportunities(
    request: SAMGovCollectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_api_key),
):
    """
    Fetch opportunities from SAM.gov API and import them as contracts.

    Requires SAM_GOV_API_KEY environment variable to be set.
    Searches by NAICS codes over the specified date range, deduplicates,
    and imports new opportunities as prospective contracts.
    """
    api_key = os.getenv("SAM_GOV_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SAM_GOV_API_KEY not configured",
        )

    naics_codes = request.naics_codes

    try:
        # Run the synchronous API calls in a thread to avoid blocking
        opportunities = await asyncio.to_thread(
            collect_opportunities,
            api_key=api_key,
            naics_codes=naics_codes,
            days_back=request.days_back,
            solicitations_only=request.solicitations_only,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("SAM.gov collection failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"SAM.gov API error: {e}",
        )

    result = import_opportunities(
        opportunities=opportunities,
        auto_create_contacts=request.auto_create_contacts,
        current_user=current_user,
        db=db,
    )
    return SAMGovCollectResponse(
        opportunities_fetched=len(opportunities),
        **result,
    )

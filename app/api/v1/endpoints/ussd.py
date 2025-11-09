from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.ussd import USSDRequest, USSDResponse
from app.db.session import get_db
from app.services.ussd import ussd_service

router = APIRouter()

@router.post("/ussd", response_model=USSDResponse)
async def process_ussd_request(
    ussd_request: USSDRequest,
    db: AsyncSession = Depends(get_db)
) -> USSDResponse:
    """
    Process USSD requests from mobile networks.
    
    This endpoint handles all USSD interactions, maintaining session state
    and guiding users through the banking menu.
    """
    try:
        return await ussd_service.process_ussd_request(db, ussd_request)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to process USSD request: {str(e)}"
        )
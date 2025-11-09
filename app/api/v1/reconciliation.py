from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import require_roles
from app.models.user import User
from app.models.enums import UserRole
from app.services.reconciliation_service import ReconciliationService
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


@router.post("/upload", response_model=Dict[str, Any])
@require_roles([UserRole.ADMIN, UserRole.BANK_STAFF])
async def upload_reconciliation_file(
    file: UploadFile = File(...),
    record_type: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload and process reconciliation file"""
    try:
        # Validate file type
        if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="Only CSV and Excel files are supported"
            )
        
        # Read file content
        content = await file.read()
        
        # Process the file
        reconciliation_service = ReconciliationService(db)
        result = await reconciliation_service.process_bulk_upload(
            file_content=content,
            file_name=file.filename,
            record_type=record_type,
            uploaded_by=current_user.email
        )
        
        # Audit log
        audit_service = AuditService(db)
        await audit_service.log_activity(
            user_id=current_user.id,
            action="reconciliation_upload",
            resource_type="reconciliation",
            resource_id=result["reconciliation_id"],
            details={
                "file_name": file.filename,
                "record_type": record_type,
                "total_records": result["total_records"]
            }
        )
        
        return result
        
    except ValueError as e:
        logger.error(f"Validation error in reconciliation upload: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing reconciliation file: {e}")
        raise HTTPException(status_code=500, detail="Error processing reconciliation file")


@router.post("/auto-match", response_model=Dict[str, Any])
@require_roles([UserRole.ADMIN, UserRole.BANK_STAFF])
async def auto_match_transactions(
    start_date: date,
    end_date: date,
    transaction_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Auto-match transactions within a date range"""
    try:
        reconciliation_service = ReconciliationService(db)
        result = await reconciliation_service.auto_match_transactions(
            start_date=start_date,
            end_date=end_date,
            transaction_type=transaction_type
        )
        
        # Audit log
        audit_service = AuditService(db)
        await audit_service.log_activity(
            user_id=current_user.id,
            action="auto_match_transactions",
            resource_type="reconciliation",
            resource_id="auto_match",
            details={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "transaction_type": transaction_type,
                "matched": result["matched"],
                "unmatched": result["unmatched"]
            }
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in auto-match transactions: {e}")
        raise HTTPException(status_code=500, detail="Error performing auto-match")


@router.get("/summary/{reconciliation_id}", response_model=Dict[str, Any])
@require_roles([UserRole.ADMIN, UserRole.BANK_STAFF])
async def get_reconciliation_summary(
    reconciliation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed reconciliation summary"""
    try:
        reconciliation_service = ReconciliationService(db)
        summary = await reconciliation_service.get_reconciliation_summary(reconciliation_id)
        
        return summary
        
    except ValueError as e:
        logger.error(f"Reconciliation record not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting reconciliation summary: {e}")
        raise HTTPException(status_code=500, detail="Error getting reconciliation summary")


@router.get("/report", response_model=Dict[str, Any])
@require_roles([UserRole.ADMIN, UserRole.BANK_STAFF])
async def generate_reconciliation_report(
    start_date: date,
    end_date: date,
    record_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate comprehensive reconciliation report"""
    try:
        reconciliation_service = ReconciliationService(db)
        report = await reconciliation_service.generate_reconciliation_report(
            start_date=start_date,
            end_date=end_date,
            record_type=record_type
        )
        
        # Audit log
        audit_service = AuditService(db)
        await audit_service.log_activity(
            user_id=current_user.id,
            action="generate_reconciliation_report",
            resource_type="reconciliation",
            resource_id="report",
            details={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "record_type": record_type
            }
        )
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating reconciliation report: {e}")
        raise HTTPException(status_code=500, detail="Error generating reconciliation report")
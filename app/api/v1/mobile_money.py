from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import asyncio

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.enums import UserRole
from app.services.mobile_money_service import MobileMoneyService
from app.services.messaging_service import MessagingService
from app.services.payment_service import PaymentService
from app.schemas.mobile_money import (
    MobileMoneyPaymentRequest,
    MobileMoneyPaymentResponse,
    TransactionStatusResponse,
    RefundRequest,
    RefundResponse,
    ProviderListResponse
)
from app.core.permissions import require_roles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mobile-money", tags=["mobile-money"])


@router.post("/payment", response_model=MobileMoneyPaymentResponse)
async def create_mobile_money_payment(
    payment_request: MobileMoneyPaymentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new mobile money payment"""
    try:
        # Initialize services
        mobile_money_service = MobileMoneyService()
        payment_service = PaymentService(db)
        
        # Create transaction record first
        transaction = payment_service.create_deposit(
            account_id=payment_request.account_id,
            amount=payment_request.amount,
            currency=payment_request.currency,
            description=f"Mobile money payment via {payment_request.provider}",
            metadata={
                "provider": payment_request.provider,
                "phone_number": payment_request.phone_number,
                "type": "mobile_money"
            }
        )
        
        # Process mobile money payment
        result = await mobile_money_service.process_mobile_money_payment(
            provider=payment_request.provider,
            transaction_id=transaction.transaction_id,
            phone_number=payment_request.phone_number,
            amount=payment_request.amount,
            currency=payment_request.currency,
            description=payment_request.description or "Banking transaction"
        )
        
        if result["status"] == "initiated":
            # Update transaction status
            transaction.status = "pending"
            transaction.provider_transaction_id = result.get("provider_transaction_id")
            db.commit()
            
            # Add background task to check status
            background_tasks.add_task(
                check_mobile_money_status,
                payment_request.provider,
                transaction.transaction_id,
                result.get("provider_transaction_id")
            )
        
        return MobileMoneyPaymentResponse(
            transaction_id=transaction.transaction_id,
            status=result["status"],
            provider_transaction_id=result.get("provider_transaction_id"),
            message=result.get("message"),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"Error creating mobile money payment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{transaction_id}", response_model=TransactionStatusResponse)
async def get_transaction_status(
    transaction_id: str,
    provider_transaction_id: Optional[str] = None,
    provider: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get mobile money transaction status"""
    try:
        mobile_money_service = MobileMoneyService()
        
        result = await mobile_money_service.check_transaction_status(
            provider=provider or "ecocash",  # Default to ecocash
            transaction_id=transaction_id,
            provider_transaction_id=provider_transaction_id
        )
        
        return TransactionStatusResponse(
            transaction_id=transaction_id,
            status=result["status"],
            provider_transaction_id=result.get("provider_transaction_id"),
            amount=result.get("amount"),
            currency=result.get("currency"),
            timestamp=result.get("timestamp"),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"Error checking transaction status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refund", response_model=RefundResponse)
async def refund_mobile_money_transaction(
    refund_request: RefundRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(require_roles([UserRole.ADMIN, UserRole.BANK_STAFF]))
):
    """Refund a mobile money transaction"""
    try:
        mobile_money_service = MobileMoneyService()
        
        result = await mobile_money_service.refund_transaction(
            provider=refund_request.provider,
            transaction_id=refund_request.transaction_id,
            provider_transaction_id=refund_request.provider_transaction_id,
            amount=refund_request.amount,
            reason=refund_request.reason
        )
        
        return RefundResponse(
            transaction_id=refund_request.transaction_id,
            status=result["status"],
            refund_transaction_id=result.get("refund_transaction_id"),
            message=result.get("message"),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"Error refunding mobile money transaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers", response_model=ProviderListResponse)
async def get_supported_providers(
    current_user: User = Depends(get_current_user)
):
    """Get list of supported mobile money providers"""
    try:
        mobile_money_service = MobileMoneyService()
        providers = mobile_money_service.get_supported_providers()
        
        return ProviderListResponse(providers=providers)
        
    except Exception as e:
        logger.error(f"Error getting supported providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/callback/{provider}")
async def handle_mobile_money_callback(
    provider: str,
    callback_data: dict,
    db: Session = Depends(get_db)
):
    """Handle mobile money provider callbacks"""
    try:
        messaging_service = MessagingService()
        
        # Extract transaction information from callback
        transaction_id = callback_data.get("transaction_id")
        status = callback_data.get("status")
        
        # Publish callback message for processing
        await messaging_service.publish_mobile_money_request(
            transaction_id=transaction_id,
            provider=provider,
            status=status,
            provider_transaction_id=callback_data.get("provider_transaction_id"),
            phone_number=callback_data.get("phone_number"),
            amount=callback_data.get("amount"),
            error=callback_data.get("error")
        )
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"Error handling mobile money callback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def check_mobile_money_status(
    provider: str,
    transaction_id: str,
    provider_transaction_id: Optional[str] = None,
    max_attempts: int = 10,
    delay_seconds: int = 30
):
    """Background task to check mobile money transaction status"""
    try:
        mobile_money_service = MobileMoneyService()
        messaging_service = MessagingService()
        
        for attempt in range(max_attempts):
            # Check transaction status
            result = await mobile_money_service.check_transaction_status(
                provider=provider,
                transaction_id=transaction_id,
                provider_transaction_id=provider_transaction_id
            )
            
            status = result.get("status", "unknown")
            
            # If transaction is completed or failed, update and break
            if status in ["completed", "failed", "cancelled", "expired"]:
                await messaging_service.publish_transaction_completed(
                    transaction_id=transaction_id,
                    status="completed" if status == "completed" else "failed",
                    metadata={
                        "provider": provider,
                        "provider_transaction_id": result.get("provider_transaction_id"),
                        "final_status": status
                    }
                )
                break
            
            # Wait before next check
            await asyncio.sleep(delay_seconds)
            
    except Exception as e:
        logger.error(f"Error in background status check: {e}")
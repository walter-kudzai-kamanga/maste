from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from app.core.database import get_db
from app.models.schemas import (
    DepositRequest, WithdrawalRequest, TransferRequest,
    TransactionResponse, ErrorResponse, PaginatedTransactions
)
from app.models.user import User
from app.models.enums import UserRole, TransactionStatus
from app.api.dependencies import (
    get_current_active_user, get_current_active_agent,
    get_current_active_staff
)
from app.services.payment_service import PaymentService
from app.services.audit_service import AuditService


router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/deposit", response_model=TransactionResponse, responses={400: {"model": ErrorResponse}})
async def create_deposit(
    deposit_data: DepositRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_agent)
):
    """Create a deposit transaction (agents only)."""
    payment_service = PaymentService(db)
    audit_service = AuditService(db)
    
    try:
        # Create deposit transaction
        transaction = await payment_service.create_deposit(
            deposit_data, current_user.id, idempotency_key
        )
        
        # Process the transaction immediately (in production, this would be queued)
        success = await payment_service.process_transaction(transaction.id)
        
        if not success:
            # Log failed transaction
            await audit_service.log_action(
                action="TRANSACTION_FAILED",
                user_id=current_user.id,
                username=current_user.username,
                user_role=current_user.role.value,
                resource_type="Transaction",
                resource_id=str(transaction.id),
                action_details={
                    "transaction_type": "DEPOSIT",
                    "amount": float(deposit_data.amount),
                    "reason": "Processing failed"
                },
                success=False,
                error_message="Transaction processing failed"
            )
            raise HTTPException(status_code=400, detail="Transaction processing failed")
        
        # Log successful transaction
        await audit_service.log_action(
            action="TRANSACTION_COMPLETED",
            user_id=current_user.id,
            username=current_user.username,
            user_role=current_user.role.value,
            resource_type="Transaction",
            resource_id=str(transaction.id),
            action_details={
                "transaction_type": "DEPOSIT",
                "amount": float(deposit_data.amount),
                "account_id": str(deposit_data.account_id)
            }
        )
        
        return transaction
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/withdrawal", response_model=TransactionResponse, responses={400: {"model": ErrorResponse}})
async def create_withdrawal(
    withdrawal_data: WithdrawalRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_agent)
):
    """Create a withdrawal transaction (agents only)."""
    payment_service = PaymentService(db)
    audit_service = AuditService(db)
    
    try:
        # Create withdrawal transaction
        transaction = await payment_service.create_withdrawal(
            withdrawal_data, current_user.id, idempotency_key
        )
        
        # Process the transaction immediately (in production, this would be queued)
        success = await payment_service.process_transaction(transaction.id)
        
        if not success:
            # Log failed transaction
            await audit_service.log_action(
                action="TRANSACTION_FAILED",
                user_id=current_user.id,
                username=current_user.username,
                user_role=current_user.role.value,
                resource_type="Transaction",
                resource_id=str(transaction.id),
                action_details={
                    "transaction_type": "WITHDRAWAL",
                    "amount": float(withdrawal_data.amount),
                    "reason": "Processing failed"
                },
                success=False,
                error_message="Transaction processing failed"
            )
            raise HTTPException(status_code=400, detail="Transaction processing failed")
        
        # Log successful transaction
        await audit_service.log_action(
            action="TRANSACTION_COMPLETED",
            user_id=current_user.id,
            username=current_user.username,
            user_role=current_user.role.value,
            resource_type="Transaction",
            resource_id=str(transaction.id),
            action_details={
                "transaction_type": "WITHDRAWAL",
                "amount": float(withdrawal_data.amount),
                "account_id": str(withdrawal_data.account_id)
            }
        )
        
        return transaction
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transfer", response_model=TransactionResponse, responses={400: {"model": ErrorResponse}})
async def create_transfer(
    transfer_data: TransferRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a transfer transaction (customers and staff)."""
    payment_service = PaymentService(db)
    audit_service = AuditService(db)
    
    try:
        # Create transfer transaction
        transaction = await payment_service.create_transfer(
            transfer_data, current_user.id, idempotency_key
        )
        
        # Process the transaction immediately (in production, this would be queued)
        success = await payment_service.process_transaction(transaction.id)
        
        if not success:
            # Log failed transaction
            await audit_service.log_action(
                action="TRANSACTION_FAILED",
                user_id=current_user.id,
                username=current_user.username,
                user_role=current_user.role.value,
                resource_type="Transaction",
                resource_id=str(transaction.id),
                action_details={
                    "transaction_type": "TRANSFER",
                    "amount": float(transfer_data.amount),
                    "from_account": str(transfer_data.from_account_id),
                    "to_account": str(transfer_data.to_account_id),
                    "reason": "Processing failed"
                },
                success=False,
                error_message="Transaction processing failed"
            )
            raise HTTPException(status_code=400, detail="Transaction processing failed")
        
        # Log successful transaction
        await audit_service.log_action(
            action="TRANSACTION_COMPLETED",
            user_id=current_user.id,
            username=current_user.username,
            user_role=current_user.role.value,
            resource_type="Transaction",
            resource_id=str(transaction.id),
            action_details={
                "transaction_type": "TRANSFER",
                "amount": float(transfer_data.amount),
                "from_account": str(transfer_data.from_account_id),
                "to_account": str(transfer_data.to_account_id)
            }
        )
        
        return transaction
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/transactions", response_model=PaginatedTransactions)
async def list_transactions(
    skip: int = 0,
    limit: int = 100,
    status: Optional[TransactionStatus] = None,
    account_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List transactions for the current user."""
    payment_service = PaymentService(db)
    
    # Filter by user ID for customers, or get all for staff
    user_id = current_user.id if current_user.role == UserRole.CUSTOMER else None
    
    transactions = await payment_service.get_transactions(
        user_id=user_id,
        account_id=account_id,
        status=status,
        skip=skip,
        limit=limit
    )
    
    return PaginatedTransactions(
        items=transactions,
        total=len(transactions),
        skip=skip,
        limit=limit
    )


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get transaction by ID."""
    payment_service = PaymentService(db)
    transaction = await payment_service.get_transaction_by_id(transaction_id)
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Check if user has access to this transaction
    if (current_user.role == UserRole.CUSTOMER and 
        transaction.initiated_by != current_user.id and
        transaction.from_account_id not in [acc.id for acc in current_user.accounts] and
        transaction.to_account_id not in [acc.id for acc in current_user.accounts]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return transaction


@router.get("/transactions/by-reference/{reference}", response_model=TransactionResponse)
async def get_transaction_by_reference(
    reference: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get transaction by reference."""
    payment_service = PaymentService(db)
    transaction = await payment_service.get_transaction_by_transaction_id(reference)
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Check if user has access to this transaction
    if (current_user.role == UserRole.CUSTOMER and 
        transaction.initiated_by != current_user.id and
        transaction.from_account_id not in [acc.id for acc in current_user.accounts] and
        transaction.to_account_id not in [acc.id for acc in current_user.accounts]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return transaction
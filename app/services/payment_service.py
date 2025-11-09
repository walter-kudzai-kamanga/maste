from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID, uuid4
from decimal import Decimal
from datetime import datetime, timedelta
import json

from app.models.transaction import Transaction
from app.models.account import Account
from app.models.ledger import LedgerEntry
from app.models.enums import (
    TransactionType, TransactionStatus, MobileMoneyProvider
)
from app.models.schemas import (
    DepositRequest, WithdrawalRequest, TransferRequest,
    TransactionResponse
)
from app.services.account_service import AccountService
from app.services.audit_service import AuditService
from app.services.messaging_service import MessagingService


class PaymentService:
    """Service for processing payments and transactions."""
    
    def __init__(self, db: AsyncSession, messaging_service: Optional[MessagingService] = None):
        self.db = db
        self.account_service = AccountService(db)
        self.messaging_service = messaging_service
    
    def generate_transaction_id(self) -> str:
        """Generate unique transaction ID."""
        import random
        import string
        
        # Generate a 16-character transaction ID
        prefix = "TXN"
        digits = ''.join(random.choices(string.digits + string.ascii_uppercase, k=13))
        return f"{prefix}{digits}"
    
    async def check_idempotency_key(self, idempotency_key: str) -> Optional[Transaction]:
        """Check if transaction with idempotency key already exists."""
        result = await self.db.execute(
            select(Transaction).where(Transaction.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()
    
    async def create_deposit(
        self,
        deposit_data: DepositRequest,
        agent_id: UUID,
        idempotency_key: Optional[str] = None
    ) -> Transaction:
        """Process a deposit transaction."""
        # Check idempotency key
        if idempotency_key:
            existing_txn = await self.check_idempotency_key(idempotency_key)
            if existing_txn:
                return existing_txn
        
        # Get target account
        target_account = await self.account_service.get_account_by_id(deposit_data.account_id)
        if not target_account:
            raise ValueError("Target account not found")
        
        # Check if account can be credited
        if not await self.account_service.can_credit_account(deposit_data.account_id):
            raise ValueError("Account cannot receive deposits")
        
        # Create transaction
        transaction = Transaction(
            id=uuid4(),
            transaction_id=self.generate_transaction_id(),
            idempotency_key=idempotency_key,
            transaction_type=TransactionType.DEPOSIT,
            status=TransactionStatus.PENDING,
            amount=deposit_data.amount,
            currency=deposit_data.currency or "USD",
            to_account_id=deposit_data.account_id,
            agent_id=agent_id,
            description=deposit_data.description or "Cash deposit",
            reference=deposit_data.reference,
            initiated_by=agent_id,
            created_at=datetime.utcnow()
        )
        
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        
        # Publish message if messaging service is available
        if self.messaging_service:
            await self.messaging_service.publish_deposit_request(
                transaction_id=transaction.transaction_id,
                account_id=str(deposit_data.account_id),
                amount=float(deposit_data.amount),
                currency=deposit_data.currency or "USD",
                agent_id=str(agent_id),
                mobile_number=deposit_data.mobile_number
            )
        
        return transaction
    
    async def create_withdrawal(
        self,
        withdrawal_data: WithdrawalRequest,
        agent_id: UUID,
        idempotency_key: Optional[str] = None
    ) -> Transaction:
        """Process a withdrawal transaction."""
        # Check idempotency key
        if idempotency_key:
            existing_txn = await self.check_idempotency_key(idempotency_key)
            if existing_txn:
                return existing_txn
        
        # Get source account
        source_account = await self.account_service.get_account_by_id(withdrawal_data.account_id)
        if not source_account:
            raise ValueError("Source account not found")
        
        # Check if account can be debited
        if not await self.account_service.can_debit_account(
            withdrawal_data.account_id, withdrawal_data.amount
        ):
            raise ValueError("Insufficient funds or account not eligible for withdrawal")
        
        # Create transaction
        transaction = Transaction(
            id=uuid4(),
            transaction_id=self.generate_transaction_id(),
            idempotency_key=idempotency_key,
            transaction_type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.PENDING,
            amount=withdrawal_data.amount,
            currency=withdrawal_data.currency or "USD",
            from_account_id=withdrawal_data.account_id,
            agent_id=agent_id,
            description=withdrawal_data.description or "Cash withdrawal",
            reference=withdrawal_data.reference,
            initiated_by=agent_id,
            created_at=datetime.utcnow()
        )
        
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        
        # Publish message if messaging service is available
        if self.messaging_service:
            await self.messaging_service.publish_withdrawal_request(
                transaction_id=transaction.transaction_id,
                account_id=str(withdrawal_data.account_id),
                amount=float(withdrawal_data.amount),
                currency=withdrawal_data.currency or "USD",
                agent_id=str(agent_id),
                mobile_number=withdrawal_data.mobile_number
            )
        
        return transaction
    
    async def create_transfer(
        self,
        transfer_data: TransferRequest,
        user_id: UUID,
        idempotency_key: Optional[str] = None
    ) -> Transaction:
        """Process a transfer transaction."""
        # Check idempotency key
        if idempotency_key:
            existing_txn = await self.check_idempotency_key(idempotency_key)
            if existing_txn:
                return existing_txn
        
        # Get source and target accounts
        source_account = await self.account_service.get_account_by_id(transfer_data.from_account_id)
        target_account = await self.account_service.get_account_by_id(transfer_data.to_account_id)
        
        if not source_account:
            raise ValueError("Source account not found")
        if not target_account:
            raise ValueError("Target account not found")
        
        # Check if accounts belong to the same user (for customer transfers)
        if source_account.user_id != user_id:
            raise ValueError("Source account does not belong to user")
        
        # Check if source account can be debited
        if not await self.account_service.can_debit_account(
            transfer_data.from_account_id, transfer_data.amount
        ):
            raise ValueError("Insufficient funds or account not eligible for transfer")
        
        # Check if target account can be credited
        if not await self.account_service.can_credit_account(transfer_data.to_account_id):
            raise ValueError("Target account cannot receive transfers")
        
        # Create transaction
        transaction = Transaction(
            id=uuid4(),
            transaction_id=self.generate_transaction_id(),
            idempotency_key=idempotency_key,
            transaction_type=TransactionType.TRANSFER,
            status=TransactionStatus.PENDING,
            amount=transfer_data.amount,
            currency=transfer_data.currency or "USD",
            from_account_id=transfer_data.from_account_id,
            to_account_id=transfer_data.to_account_id,
            description=transfer_data.description or "Account transfer",
            reference=transfer_data.reference,
            initiated_by=user_id,
            created_at=datetime.utcnow()
        )
        
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        
        # Publish message if messaging service is available
        if self.messaging_service:
            await self.messaging_service.publish_transfer_request(
                transaction_id=transaction.transaction_id,
                from_account_id=str(transfer_data.from_account_id),
                to_account_id=str(transfer_data.to_account_id),
                amount=float(transfer_data.amount),
                currency=transfer_data.currency or "USD",
                description=transfer_data.description
            )
        
        return transaction
    
    async def process_transaction(self, transaction_id: UUID) -> bool:
        """Process a pending transaction."""
        # Get transaction
        result = await self.db.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            return False
        
        if transaction.status != TransactionStatus.PENDING:
            return False
        
        try:
            # Process based on transaction type
            if transaction.transaction_type == TransactionType.DEPOSIT:
                success = await self._process_deposit(transaction)
            elif transaction.transaction_type == TransactionType.WITHDRAWAL:
                success = await self._process_withdrawal(transaction)
            elif transaction.transaction_type == TransactionType.TRANSFER:
                success = await self._process_transfer(transaction)
            else:
                success = False
            
            if success:
                transaction.status = TransactionStatus.COMPLETED
                transaction.completed_at = datetime.utcnow()
            else:
                transaction.status = TransactionStatus.FAILED
                transaction.failed_at = datetime.utcnow()
            
            await self.db.commit()
            return success
            
        except Exception as e:
            transaction.status = TransactionStatus.FAILED
            transaction.failed_at = datetime.utcnow()
            transaction.failure_reason = str(e)
            await self.db.commit()
            return False
    
    async def _process_deposit(self, transaction: Transaction) -> bool:
        """Process deposit transaction."""
        try:
            # Credit target account
            target_account = await self.account_service.get_account_by_id(transaction.to_account_id)
            if not target_account:
                return False
            
            # Update account balance
            await self.account_service.update_balance(
                transaction.to_account_id, transaction.amount, is_credit=True
            )
            
            # Create ledger entry
            ledger_entry = LedgerEntry(
                transaction_id=transaction.id,
                account_id=transaction.to_account_id,
                entry_type="CREDIT",
                amount=transaction.amount,
                running_balance=target_account.balance + transaction.amount,
                is_credit=True,
                description=f"Deposit: {transaction.description}",
                reference=transaction.transaction_id
            )
            
            self.db.add(ledger_entry)
            return True
            
        except Exception:
            return False
    
    async def _process_withdrawal(self, transaction: Transaction) -> bool:
        """Process withdrawal transaction."""
        try:
            # Debit source account
            source_account = await self.account_service.get_account_by_id(transaction.from_account_id)
            if not source_account:
                return False
            
            # Update account balance
            await self.account_service.update_balance(
                transaction.from_account_id, transaction.amount, is_credit=False
            )
            
            # Create ledger entry
            ledger_entry = LedgerEntry(
                transaction_id=transaction.id,
                account_id=transaction.from_account_id,
                entry_type="DEBIT",
                amount=transaction.amount,
                running_balance=source_account.balance - transaction.amount,
                is_credit=False,
                description=f"Withdrawal: {transaction.description}",
                reference=transaction.transaction_id
            )
            
            self.db.add(ledger_entry)
            return True
            
        except Exception:
            return False
    
    async def _process_transfer(self, transaction: Transaction) -> bool:
        """Process transfer transaction."""
        try:
            # Debit source account
            source_account = await self.account_service.get_account_by_id(transaction.from_account_id)
            if not source_account:
                return False
            
            # Credit target account
            target_account = await self.account_service.get_account_by_id(transaction.to_account_id)
            if not target_account:
                return False
            
            # Update balances
            await self.account_service.update_balance(
                transaction.from_account_id, transaction.amount, is_credit=False
            )
            await self.account_service.update_balance(
                transaction.to_account_id, transaction.amount, is_credit=True
            )
            
            # Create ledger entries for both accounts
            source_ledger = LedgerEntry(
                transaction_id=transaction.id,
                account_id=transaction.from_account_id,
                entry_type="DEBIT",
                amount=transaction.amount,
                running_balance=source_account.balance - transaction.amount,
                is_credit=False,
                description=f"Transfer to {target_account.account_number}",
                reference=transaction.transaction_id
            )
            
            target_ledger = LedgerEntry(
                transaction_id=transaction.id,
                account_id=transaction.to_account_id,
                entry_type="CREDIT",
                amount=transaction.amount,
                running_balance=target_account.balance + transaction.amount,
                is_credit=True,
                description=f"Transfer from {source_account.account_number}",
                reference=transaction.transaction_id
            )
            
            self.db.add(source_ledger)
            self.db.add(target_ledger)
            
            return True
            
        except Exception:
            return False
    
    async def get_transaction_by_id(self, transaction_id: UUID) -> Optional[Transaction]:
        """Get transaction by ID."""
        result = await self.db.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        return result.scalar_one_or_none()
    
    async def get_transaction_by_transaction_id(self, transaction_id: str) -> Optional[Transaction]:
        """Get transaction by transaction ID."""
        result = await self.db.execute(
            select(Transaction).where(Transaction.transaction_id == transaction_id)
        )
        return result.scalar_one_or_none()
    
    async def get_transactions(
        self,
        user_id: Optional[UUID] = None,
        account_id: Optional[UUID] = None,
        transaction_type: Optional[TransactionType] = None,
        status: Optional[TransactionStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Transaction]:
        """Get transactions with filters."""
        query = select(Transaction)
        
        if user_id:
            query = query.where(
                or_(
                    Transaction.initiated_by == user_id,
                    Transaction.agent_id == user_id
                )
            )
        if account_id:
            query = query.where(
                or_(
                    Transaction.from_account_id == account_id,
                    Transaction.to_account_id == account_id
                )
            )
        if transaction_type:
            query = query.where(Transaction.transaction_type == transaction_type)
        if status:
            query = query.where(Transaction.status == status)
        
        query = query.order_by(Transaction.created_at.desc())
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
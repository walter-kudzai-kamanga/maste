from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, Enum, Index, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4
from decimal import Decimal
from datetime import datetime
from app.core.database import Base
from app.core.db_utils import get_uuid_column, get_foreign_key_uuid_column
from app.models.enums import TransactionType, TransactionStatus
from app.core.config import TABLE_PREFIX


class Transaction(Base):
    __tablename__ = f"{TABLE_PREFIX}transactions"
    
    id = get_uuid_column()
    
    # Transaction identifiers
    transaction_id = Column(String(100), unique=True, index=True, nullable=False)
    idempotency_key = Column(String(255), unique=True, index=True, nullable=True)
    reference = Column(String(100), nullable=True)
    external_reference = Column(String(100), nullable=True)
    
    # Transaction details
    transaction_type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING)
    
    # Amount and currency
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    fee = Column(Numeric(10, 2), nullable=True, default=Decimal("0.00"))
    
    # Accounts involved
    from_account_id = get_foreign_key_uuid_column(ForeignKey(f"{TABLE_PREFIX}accounts.id"), nullable=True)
    to_account_id = get_foreign_key_uuid_column(ForeignKey(f"{TABLE_PREFIX}accounts.id"), nullable=True)
    
    # Agent information (for agent transactions)
    agent_id = get_foreign_key_uuid_column(ForeignKey(f"{TABLE_PREFIX}agents.id"), nullable=True)
    
    # Mobile money integration
    mobile_money_provider = Column(String(50), nullable=True)
    mobile_money_reference = Column(String(100), nullable=True)
    
    # User information
    initiated_by = get_foreign_key_uuid_column(ForeignKey(f"{TABLE_PREFIX}users.id"), nullable=False)
    
    # Additional information
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Failure information
    failure_reason = Column(Text, nullable=True)
    failure_code = Column(String(50), nullable=True)
    
    # Relationships
    from_account = relationship("Account", foreign_keys=[from_account_id], back_populates="outgoing_transactions")
    to_account = relationship("Account", foreign_keys=[to_account_id], back_populates="incoming_transactions")
    agent = relationship("Agent", back_populates="transactions")
    initiated_by_user = relationship("User", foreign_keys=[initiated_by])
    ledger_entries = relationship("LedgerEntry", back_populates="transaction")
    
    # Indexes for performance
    __table_args__ = (
        Index(f"idx_{TABLE_PREFIX}transactions_status", "status"),
        Index(f"idx_{TABLE_PREFIX}transactions_type", "transaction_type"),
        Index(f"idx_{TABLE_PREFIX}transactions_created", "created_at"),
        Index(f"idx_{TABLE_PREFIX}transactions_from_account", "from_account_id"),
        Index(f"idx_{TABLE_PREFIX}transactions_to_account", "to_account_id"),
        Index(f"idx_{TABLE_PREFIX}transactions_agent", "agent_id"),
    )
    
    def __repr__(self):
        return f"<Transaction(transaction_id='{self.transaction_id}', type='{self.transaction_type}', amount={self.amount})>"
    
    def mark_as_processing(self):
        """Mark transaction as processing."""
        self.status = TransactionStatus.PROCESSING
        self.processed_at = datetime.utcnow()
    
    def mark_as_completed(self):
        """Mark transaction as completed."""
        self.status = TransactionStatus.COMPLETED
        self.completed_at = datetime.utcnow()
    
    def mark_as_failed(self, reason: str, failure_code: str = None):
        """Mark transaction as failed."""
        self.status = TransactionStatus.FAILED
        self.failure_reason = reason
        self.failure_code = failure_code
        self.failed_at = datetime.utcnow()
    
    def is_reversible(self) -> bool:
        """Check if transaction can be reversed."""
        return self.status == TransactionStatus.COMPLETED and self.transaction_type in [
            TransactionType.DEPOSIT,
            TransactionType.WITHDRAWAL,
            TransactionType.TRANSFER
        ]
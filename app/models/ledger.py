from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, Enum, Index, Text, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4
from decimal import Decimal
from app.core.database import Base
from app.core.db_utils import get_uuid_column, get_foreign_key_uuid_column
from app.models.enums import TransactionType
from app.core.config import TABLE_PREFIX


class LedgerEntry(Base):
    """
    Immutable ledger entries for audit trail and reconciliation.
    Every transaction creates corresponding ledger entries.
    """
    __tablename__ = f"{TABLE_PREFIX}ledger"
    
    entry_id = Column(Integer, primary_key=True, index=True)
    account_id = get_foreign_key_uuid_column(ForeignKey(f"{TABLE_PREFIX}accounts.id"), nullable=False)
    transaction_id = get_foreign_key_uuid_column(ForeignKey(f"{TABLE_PREFIX}transactions.id"), nullable=True)
    amount = Column(Numeric(15, 2), nullable=False)
    balance_after = Column(Numeric(15, 2), nullable=False)
    entry_type = Column(String, nullable=False)
    trace_id = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    account = relationship("Account", back_populates="ledger_entries")
    transaction = relationship("Transaction", back_populates="ledger_entries")
    
    __table_args__ = (
        Index(f"idx_{TABLE_PREFIX}ledger_account", "account_id"),
        Index(f"idx_{TABLE_PREFIX}ledger_created", "created_at"),
        Index(f"idx_{TABLE_PREFIX}ledger_trace", "trace_id"),
        Index(f"idx_{TABLE_PREFIX}ledger_tx", "transaction_id"),
        Index(f"idx_{TABLE_PREFIX}ledger_account_created", "account_id", "created_at"),
    )
from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, Enum, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4
from decimal import Decimal
from app.core.database import Base
from app.core.db_utils import get_uuid_column, get_foreign_key_uuid_column
from app.models.enums import AccountType, AccountStatus
from app.core.config import TABLE_PREFIX


class Account(Base):
    __tablename__ = f"{TABLE_PREFIX}accounts"
    
    id = get_uuid_column()
    account_number = Column(String(50), unique=True, index=True, nullable=False)
    customer_id = get_foreign_key_uuid_column(ForeignKey(f"{TABLE_PREFIX}users.id"), nullable=False)
    
    # Account details
    account_type = Column(Enum(AccountType), nullable=False, default=AccountType.CUSTOMER)
    status = Column(Enum(AccountStatus), nullable=False, default=AccountStatus.ACTIVE)
    currency = Column(String(3), nullable=False, default="USD")
    
    # Balance (stored as decimal for precision)
    balance = Column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    available_balance = Column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    
    # Limits and controls
    daily_limit = Column(Numeric(15, 2), nullable=True)
    monthly_limit = Column(Numeric(15, 2), nullable=True)
    single_transaction_limit = Column(Numeric(15, 2), nullable=True)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional fields
    branch_code = Column(String(20), nullable=True)
    description = Column(String(255), nullable=True)
    
    # Relationships
    customer = relationship("User", back_populates="accounts")
    ledger_entries = relationship("LedgerEntry", back_populates="account")
    
    # Indexes for performance
    __table_args__ = (
        Index(f"idx_{TABLE_PREFIX}accounts_customer", "customer_id"),
        Index(f"idx_{TABLE_PREFIX}accounts_type_status", "account_type", "status"),
    )
    
    def __repr__(self):
        return f"<Account(account_number='{self.account_number}', balance={self.balance})>"
    
    def can_debit(self, amount: Decimal) -> bool:
        """Check if account can be debited by the given amount."""
        if self.status != AccountStatus.ACTIVE:
            return False
        return self.available_balance >= amount
    
    def can_credit(self, amount: Decimal) -> bool:
        """Check if account can be credited (always true for active accounts)."""
        return self.status == AccountStatus.ACTIVE
    
    def update_balance(self, amount: Decimal, is_credit: bool):
        """Update account balance."""
        if is_credit:
            self.balance += amount
            self.available_balance += amount
        else:
            self.balance -= amount
            self.available_balance -= amount
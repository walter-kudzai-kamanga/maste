# Models package initialization
from .enums import *
from .user import User
from .account import Account
from .transaction import Transaction
from .ledger import LedgerEntry
from .agent import Agent, AgentFloatAdjustment
from .audit import AuditLog, ReconciliationRecord
from sqlalchemy.orm import relationship

# Fix relationships after all models are defined
from .user import User
from .account import Account
from .transaction import Transaction
from .ledger import LedgerEntry
from .agent import Agent, AgentFloatAdjustment
from .audit import AuditLog, ReconciliationRecord

# User relationships
User.accounts = relationship("Account", back_populates="customer")
User.agent_profile = relationship("Agent", back_populates="user", foreign_keys="Agent.user_id", uselist=False)

# Account relationships
Account.outgoing_transactions = relationship("Transaction", foreign_keys="Transaction.from_account_id", back_populates="from_account")
Account.incoming_transactions = relationship("Transaction", foreign_keys="Transaction.to_account_id", back_populates="to_account")
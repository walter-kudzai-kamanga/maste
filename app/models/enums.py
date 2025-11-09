from enum import Enum


class UserRole(str, Enum):
    """User roles in the system."""
    ADMIN = "admin"
    BANK_STAFF = "bank_staff"
    AGENT = "agent"
    CUSTOMER = "customer"


class TransactionType(str, Enum):
    """Types of transactions."""
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    AGENT_FLOAT_ASSIGNMENT = "agent_float_assignment"
    AGENT_FLOAT_TOPUP = "agent_float_topup"
    RECONCILIATION_ADJUSTMENT = "reconciliation_adjustment"


class TransactionStatus(str, Enum):
    """Transaction statuses."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"
    CANCELLED = "cancelled"


class AccountType(str, Enum):
    """Types of accounts."""
    CUSTOMER = "customer"
    AGENT_FLOAT = "agent_float"
    BANK_SETTLEMENT = "bank_settlement"
    MOBILE_MONEY_FLOAT = "mobile_money_float"


class AccountStatus(str, Enum):
    """Account statuses."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class AgentStatus(str, Enum):
    """Agent statuses."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_APPROVAL = "pending_approval"


class AdjustmentType(str, Enum):
    ASSIGNMENT = "assignment"
    TOPUP = "topup"
    WITHDRAWAL = "withdrawal"


class ReconciliationStatus(str, Enum):
    """Reconciliation statuses."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXCEPTIONS_FOUND = "exceptions_found"


class MobileMoneyProvider(str, Enum):
    """Mobile money providers."""
    ECOCASH = "ecocash"
    AIRTEL_MONEY = "airtel_money"
    ONE_MONEY = "one_money"


class AuditAction(str, Enum):
    """Audit log actions."""
    LOGIN = "login"
    LOGOUT = "logout"
    CREATE_ACCOUNT = "create_account"
    UPDATE_ACCOUNT = "update_account"
    CREATE_TRANSACTION = "create_transaction"
    UPDATE_TRANSACTION = "update_transaction"
    CREATE_AGENT = "create_agent"
    UPDATE_AGENT = "update_agent"
    RECONCILIATION_UPLOAD = "reconciliation_upload"
    RECONCILIATION_MATCH = "reconciliation_match"
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel


class MessageType(str, Enum):
    """Message types for the message queue system"""
    TRANSACTION_CREATED = "transaction.created"
    TRANSACTION_PROCESSING = "transaction.processing"
    TRANSACTION_COMPLETED = "transaction.completed"
    TRANSACTION_FAILED = "transaction.failed"
    TRANSACTION_REVERSED = "transaction.reversed"
    
    DEPOSIT_REQUEST = "deposit.request"
    WITHDRAWAL_REQUEST = "withdrawal.request"
    TRANSFER_REQUEST = "transfer.request"
    
    ACCOUNT_CREATED = "account.created"
    ACCOUNT_UPDATED = "account.updated"
    ACCOUNT_ACTIVATED = "account.activated"
    ACCOUNT_DEACTIVATED = "account.deactivated"
    
    AGENT_FLOAT_ADJUSTMENT = "agent.float.adjustment"
    AGENT_FLOAT_LOW = "agent.float.low"
    AGENT_PERFORMANCE_UPDATE = "agent.performance.update"
    
    RECONCILIATION_STARTED = "reconciliation.started"
    RECONCILIATION_COMPLETED = "reconciliation.completed"
    RECONCILIATION_FAILED = "reconciliation.failed"
    
    SETTLEMENT_REQUEST = "settlement.request"
    SETTLEMENT_COMPLETED = "settlement.completed"
    SETTLEMENT_FAILED = "settlement.failed"
    
    NOTIFICATION_EMAIL = "notification.email"
    NOTIFICATION_SMS = "notification.sms"
    NOTIFICATION_PUSH = "notification.push"
    
    AUDIT_LOG_CREATED = "audit.log.created"
    
    MOBILE_MONEY_REQUEST = "mobile.money.request"
    MOBILE_MONEY_CALLBACK = "mobile.money.callback"
    MOBILE_MONEY_STATUS_UPDATE = "mobile.money.status.update"


class QueueName(str, Enum):
    """Queue names for different message types"""
    TRANSACTIONS = "transactions"
    DEPOSITS = "deposits"
    WITHDRAWALS = "withdrawals"
    TRANSFERS = "transfers"
    RECONCILIATION = "reconciliation"
    SETTLEMENT = "settlement"
    NOTIFICATIONS = "notifications"
    AUDIT_LOGS = "audit_logs"
    MOBILE_MONEY = "mobile_money"
    AGENT_OPERATIONS = "agent_operations"
    HIGH_PRIORITY = "high_priority"
    LOW_PRIORITY = "low_priority"
    
    @classmethod
    def get_queue_for_message_type(cls, message_type: MessageType) -> str:
        """Get the appropriate queue name for a message type"""
        mapping = {
            MessageType.TRANSACTION_CREATED: cls.TRANSACTIONS,
            MessageType.TRANSACTION_PROCESSING: cls.TRANSACTIONS,
            MessageType.TRANSACTION_COMPLETED: cls.TRANSACTIONS,
            MessageType.TRANSACTION_FAILED: cls.TRANSACTIONS,
            MessageType.TRANSACTION_REVERSED: cls.TRANSACTIONS,
            
            MessageType.DEPOSIT_REQUEST: cls.DEPOSITS,
            MessageType.WITHDRAWAL_REQUEST: cls.WITHDRAWALS,
            MessageType.TRANSFER_REQUEST: cls.TRANSFERS,
            
            MessageType.ACCOUNT_CREATED: cls.HIGH_PRIORITY,
            MessageType.ACCOUNT_UPDATED: cls.HIGH_PRIORITY,
            MessageType.ACCOUNT_ACTIVATED: cls.HIGH_PRIORITY,
            MessageType.ACCOUNT_DEACTIVATED: cls.HIGH_PRIORITY,
            
            MessageType.AGENT_FLOAT_ADJUSTMENT: cls.AGENT_OPERATIONS,
            MessageType.AGENT_FLOAT_LOW: cls.AGENT_OPERATIONS,
            MessageType.AGENT_PERFORMANCE_UPDATE: cls.AGENT_OPERATIONS,
            
            MessageType.RECONCILIATION_STARTED: cls.RECONCILIATION,
            MessageType.RECONCILIATION_COMPLETED: cls.RECONCILIATION,
            MessageType.RECONCILIATION_FAILED: cls.RECONCILIATION,
            
            MessageType.SETTLEMENT_REQUEST: cls.SETTLEMENT,
            MessageType.SETTLEMENT_COMPLETED: cls.SETTLEMENT,
            MessageType.SETTLEMENT_FAILED: cls.SETTLEMENT,
            
            MessageType.NOTIFICATION_EMAIL: cls.NOTIFICATIONS,
            MessageType.NOTIFICATION_SMS: cls.NOTIFICATIONS,
            MessageType.NOTIFICATION_PUSH: cls.NOTIFICATIONS,
            
            MessageType.AUDIT_LOG_CREATED: cls.AUDIT_LOGS,
            
            MessageType.MOBILE_MONEY_REQUEST: cls.MOBILE_MONEY,
            MessageType.MOBILE_MONEY_CALLBACK: cls.MOBILE_MONEY,
            MessageType.MOBILE_MONEY_STATUS_UPDATE: cls.MOBILE_MONEY,
        }
        return mapping.get(message_type, cls.LOW_PRIORITY)


class Message(BaseModel):
    """Base message model"""
    id: str
    type: MessageType
    timestamp: datetime
    payload: Dict[str, Any]
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    priority: int = 0  # Higher number = higher priority
    retry_count: int = 0
    max_retries: int = 3
    
    class Config:
        use_enum_values = True


class TransactionMessage(Message):
    """Message for transaction-related events"""
    transaction_id: str
    account_id: str
    amount: float
    currency: str


class AccountMessage(Message):
    """Message for account-related events"""
    account_id: str
    customer_id: str


class AgentMessage(Message):
    """Message for agent-related events"""
    agent_id: str
    agent_code: str


class ReconciliationMessage(Message):
    """Message for reconciliation events"""
    reconciliation_id: str
    file_name: str
    total_records: int


class MobileMoneyMessage(Message):
    """Message for mobile money events"""
    provider: str  # e.g., 'ecocash', 'airtel_money'
    mobile_number: str
    transaction_id: str
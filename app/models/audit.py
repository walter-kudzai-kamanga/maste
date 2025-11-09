from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Index, Text, JSON, Integer, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4
from app.core.database import Base
from app.core.db_utils import get_uuid_column, get_foreign_key_uuid_column
from app.models.enums import AuditAction
from app.core.config import TABLE_PREFIX


class AuditLog(Base):
    """
    Comprehensive audit log for all system activities.
    """
    __tablename__ = f"{TABLE_PREFIX}audit_logs"
    
    id = get_uuid_column()
    
    # User who performed the action
    user_id = get_foreign_key_uuid_column(ForeignKey(f"{TABLE_PREFIX}users.id"), nullable=True)
    username = Column(String(50), nullable=True)
    user_role = Column(String(50), nullable=True)
    
    # Action details
    action = Column(Enum(AuditAction), nullable=False)
    resource_type = Column(String(50), nullable=True)  # 'transaction', 'account', 'agent', etc.
    resource_id = Column(String(100), nullable=True)
    
    # Request information
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    request_method = Column(String(10), nullable=True)
    request_path = Column(String(500), nullable=True)
    request_id = Column(String(100), nullable=True)
    
    # Action details
    action_details = Column(JSON, nullable=True)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    
    # Result
    success = Column(String(1), nullable=False, default='Y')
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")
    
    # Indexes for performance
    __table_args__ = (
        Index(f"idx_{TABLE_PREFIX}audit_user", "user_id"),
        Index(f"idx_{TABLE_PREFIX}audit_action", "action"),
        Index(f"idx_{TABLE_PREFIX}audit_resource", "resource_type", "resource_id"),
        Index(f"idx_{TABLE_PREFIX}audit_created", "created_at"),
        Index(f"idx_{TABLE_PREFIX}audit_request", "request_id"),
    )
    
    def __repr__(self):
        return f"<AuditLog(user='{self.username}', action='{self.action}', resource='{self.resource_type}')>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id) if self.user_id else None,
            'username': self.username,
            'user_role': self.user_role,
            'action': self.action.value,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'request_method': self.request_method,
            'request_path': self.request_path,
            'request_id': self.request_id,
            'action_details': self.action_details,
            'old_values': self.old_values,
            'new_values': self.new_values,
            'success': self.success == 'Y',
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat()
        }


class ReconciliationRecord(Base):
    """
    Track reconciliation processes and their results.
    """
    __tablename__ = f"{TABLE_PREFIX}reconciliation_records"
    
    id = get_uuid_column()
    
    # Process information
    reconciliation_id = Column(String(100), unique=True, index=True, nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_hash = Column(String(64), nullable=False)  # SHA-256 hash
    
    # Bank statement details
    statement_date = Column(DateTime(timezone=True), nullable=False)
    account_number = Column(String(50), nullable=False)
    statement_balance = Column(Numeric(15, 2), nullable=False)
    
    # Processing results
    total_transactions = Column(Integer, nullable=False, default=0)
    matched_transactions = Column(Integer, nullable=False, default=0)
    exception_transactions = Column(Integer, nullable=False, default=0)
    unmatched_transactions = Column(Integer, nullable=False, default=0)
    
    # Status
    status = Column(String(50), nullable=False, default='pending')
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processing_completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # User who uploaded the file
    uploaded_by = get_foreign_key_uuid_column(ForeignKey(f"{TABLE_PREFIX}users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    uploaded_by_user = relationship("User")
    
    def __repr__(self):
        return f"<ReconciliationRecord(reconciliation_id='{self.reconciliation_id}', file='{self.file_name}')>"
    
    @property
    def match_percentage(self) -> float:
        """Calculate percentage of matched transactions."""
        if self.total_transactions == 0:
            return 0.0
        return (self.matched_transactions / self.total_transactions) * 100
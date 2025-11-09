from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, Enum, Index, Text, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4
from decimal import Decimal
from app.core.database import Base
from app.core.db_utils import get_uuid_column, get_foreign_key_uuid_column
from app.models.enums import AgentStatus
from app.core.config import TABLE_PREFIX


class Agent(Base):
    """
    Agent model for managing banking agents and their float.
    """
    __tablename__ = f"{TABLE_PREFIX}agents"
    
    id = get_uuid_column()
    agent_code = Column(String(50), unique=True, index=True, nullable=False)
    
    # Personal information
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False)
    email = Column(String(100), nullable=True)
    national_id = Column(String(50), nullable=False)
    
    # Location information
    location = Column(String(255), nullable=False)
    region = Column(String(100), nullable=True)
    branch_code = Column(String(20), nullable=True)
    
    # Float management
    assigned_float = Column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    current_float = Column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    minimum_float = Column(Numeric(15, 2), nullable=False, default=Decimal("100.00"))
    maximum_float = Column(Numeric(15, 2), nullable=False, default=Decimal("10000.00"))
    
    # Status and controls
    status = Column(Enum(AgentStatus), nullable=False, default=AgentStatus.PENDING_APPROVAL)
    is_active = Column(String(1), nullable=False, default='Y')
    
    # Performance metrics
    total_transactions = Column(Integer, nullable=False, default=0)
    successful_transactions = Column(Integer, nullable=False, default=0)
    failed_transactions = Column(Integer, nullable=False, default=0)
    last_transaction_at = Column(DateTime(timezone=True), nullable=True)
    
    # Sync information (for offline capability)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    sync_version = Column(Integer, nullable=False, default=1)
    
    # User account link
    user_id = get_foreign_key_uuid_column(ForeignKey(f"{TABLE_PREFIX}users.id"), nullable=False)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = get_foreign_key_uuid_column(ForeignKey(f"{TABLE_PREFIX}users.id"), nullable=True)
    
    # Additional information
    notes = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="agent_profile")
    approved_by_user = relationship("User", foreign_keys=[approved_by])
    transactions = relationship("Transaction", back_populates="agent")
    float_adjustments = relationship("AgentFloatAdjustment", back_populates="agent")
    
    # Indexes for performance
    __table_args__ = (
        Index(f"idx_{TABLE_PREFIX}agents_status", "status"),
        Index(f"idx_{TABLE_PREFIX}agents_branch", "branch_code"),
        Index(f"idx_{TABLE_PREFIX}agents_region", "region"),
    )
    
    def __repr__(self):
        return f"<Agent(agent_code='{self.agent_code}', name='{self.full_name}')>"
    
    @property
    def float_utilization(self) -> Decimal:
        """Calculate float utilization percentage."""
        if self.assigned_float == 0:
            return Decimal("0.00")
        return (self.current_float / self.assigned_float) * 100
    
    def needs_float_topup(self) -> bool:
        """Check if agent needs float top-up."""
        return self.current_float < self.minimum_float
    
    def can_assign_float(self, amount: Decimal) -> bool:
        """Check if float can be assigned without exceeding maximum."""
        return (self.current_float + amount) <= self.maximum_float
    
    def update_float(self, amount: Decimal, is_addition: bool):
        """Update agent float."""
        if is_addition:
            self.current_float += amount
        else:
            self.current_float -= amount
    
    def increment_transaction_count(self, success: bool):
        """Increment transaction counters."""
        self.total_transactions += 1
        if success:
            self.successful_transactions += 1
        else:
            self.failed_transactions += 1
        self.last_transaction_at = func.now()


class AgentFloatAdjustment(Base):
    """
    Track all float adjustments for audit purposes.
    """
    __tablename__ = f"{TABLE_PREFIX}agent_float_adjustments"
    
    id = get_uuid_column()
    
    agent_id = get_foreign_key_uuid_column(ForeignKey(f"{TABLE_PREFIX}agents.id"), nullable=False)
    adjustment_type = Column(String(50), nullable=False)  # 'assignment', 'topup', 'withdrawal'
    amount = Column(Numeric(15, 2), nullable=False)
    previous_float = Column(Numeric(15, 2), nullable=False)
    new_float = Column(Numeric(15, 2), nullable=False)
    
    # Reference information
    reference = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    # User who performed the adjustment
    performed_by = get_foreign_key_uuid_column(ForeignKey(f"{TABLE_PREFIX}users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    agent = relationship("Agent", back_populates="float_adjustments")
    performed_by_user = relationship("User")
    
    def __repr__(self):
        return f"<AgentFloatAdjustment(agent_id='{self.agent_id}', type='{self.adjustment_type}', amount={self.amount})>"
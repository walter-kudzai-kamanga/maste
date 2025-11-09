from sqlalchemy import Column, String, DateTime, Boolean, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4
from datetime import datetime
from app.core.database import Base
from app.core.db_utils import get_uuid_column, get_foreign_key_uuid_column
from app.models.enums import UserRole
from app.core.config import TABLE_PREFIX


class User(Base):
    __tablename__ = f"{TABLE_PREFIX}users"
    
    id = get_uuid_column()
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.CUSTOMER)
    
    # Security fields
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(32), nullable=True)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional fields
    phone_number = Column(String(20), nullable=True)
    branch_code = Column(String(20), nullable=True)
    employee_id = Column(String(50), nullable=True)
    
    # Relationships
    agent_profile = relationship("Agent", back_populates="user", foreign_keys="Agent.user_id", uselist=False)
    
    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"
    
    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN
    
    @property
    def is_bank_staff(self) -> bool:
        return self.role in [UserRole.ADMIN, UserRole.BANK_STAFF]
    
    @property
    def is_agent(self) -> bool:
        return self.role == UserRole.AGENT
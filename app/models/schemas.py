from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from app.models.enums import UserRole, TransactionType, TransactionStatus, AccountType, AccountStatus, AgentStatus


# Base schemas
class BaseResponse(BaseModel):
    success: bool = True
    message: str = "Success"


# User schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    role: UserRole = UserRole.CUSTOMER


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)
    branch_code: Optional[str] = None
    employee_id: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, max_length=20)
    branch_code: Optional[str] = None
    employee_id: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: UUID
    is_active: bool
    is_verified: bool
    mfa_enabled: bool
    created_at: datetime
    last_login_at: Optional[datetime]
    branch_code: Optional[str]
    employee_id: Optional[str]

    class Config:
        orm_mode = True


# Authentication schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[UUID] = None
    role: Optional[UserRole] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Account schemas
class AccountBase(BaseModel):
    account_number: str = Field(..., min_length=1, max_length=50)
    account_type: AccountType = AccountType.CUSTOMER
    currency: str = Field("USD", regex=r"^[A-Z]{3}$")
    description: Optional[str] = None


class AccountCreate(AccountBase):
    customer_id: UUID
    initial_balance: Decimal = Field(0, ge=0)
    branch_code: Optional[str] = None


class AccountUpdate(BaseModel):
    status: Optional[AccountStatus] = None
    daily_limit: Optional[Decimal] = Field(None, ge=0)
    monthly_limit: Optional[Decimal] = Field(None, ge=0)
    single_transaction_limit: Optional[Decimal] = Field(None, ge=0)
    description: Optional[str] = None


class AccountResponse(AccountBase):
    id: UUID
    customer_id: UUID
    status: AccountStatus
    balance: Decimal
    available_balance: Decimal
    created_at: datetime
    branch_code: Optional[str]

    class Config:
        orm_mode = True


# Transaction schemas
class TransactionBase(BaseModel):
    transaction_type: TransactionType
    amount: Decimal = Field(..., gt=0)
    currency: str = Field("USD", regex=r"^[A-Z]{3}$")
    description: Optional[str] = None
    reference: Optional[str] = None
    idempotency_key: Optional[str] = None


class DepositRequest(TransactionBase):
    transaction_type: TransactionType = TransactionType.DEPOSIT
    to_account_id: UUID
    agent_id: Optional[UUID] = None


class WithdrawalRequest(TransactionBase):
    transaction_type: TransactionType = TransactionType.WITHDRAWAL
    from_account_id: UUID
    agent_id: Optional[UUID] = None


class TransferRequest(TransactionBase):
    transaction_type: TransactionType = TransactionType.TRANSFER
    from_account_id: UUID
    to_account_id: UUID


class TransactionResponse(TransactionBase):
    id: UUID
    transaction_id: str
    status: TransactionStatus
    from_account_id: Optional[UUID]
    to_account_id: Optional[UUID]
    agent_id: Optional[UUID]
    fee: Decimal
    created_at: datetime
    processed_at: Optional[datetime]
    completed_at: Optional[datetime]
    failure_reason: Optional[str]

    class Config:
        orm_mode = True


# Agent schemas
class AgentBase(BaseModel):
    agent_code: str = Field(..., min_length=1, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=100)
    phone_number: str = Field(..., max_length=20)
    email: Optional[EmailStr] = None
    national_id: str = Field(..., min_length=1, max_length=50)
    location: str = Field(..., min_length=1, max_length=255)
    region: Optional[str] = Field(None, max_length=100)
    branch_code: Optional[str] = None


class AgentCreate(AgentBase):
    user_id: UUID
    minimum_float: Decimal = Field(100, ge=0)
    maximum_float: Decimal = Field(10000, ge=0)


class AgentUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    location: Optional[str] = Field(None, min_length=1, max_length=255)
    region: Optional[str] = Field(None, max_length=100)
    minimum_float: Optional[Decimal] = Field(None, ge=0)
    maximum_float: Optional[Decimal] = Field(None, ge=0)
    status: Optional[AgentStatus] = None
    notes: Optional[str] = None


class FloatAdjustmentRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    adjustment_type: str = Field(..., regex=r"^(assignment|topup|withdrawal)$")
    reference: Optional[str] = None
    notes: Optional[str] = None


class FloatAdjustmentResponse(BaseModel):
    id: UUID
    agent_id: UUID
    amount: Decimal
    adjustment_type: str
    status: str
    created_at: datetime
    processed_at: Optional[datetime]
    reference: Optional[str]
    notes: Optional[str]

    class Config:
        orm_mode = True


class AgentResponse(AgentBase):
    id: UUID
    user_id: UUID
    status: AgentStatus
    assigned_float: Decimal
    current_float: Decimal
    minimum_float: Decimal
    maximum_float: Decimal


class PaginatedAgents(BaseModel):
    items: List[AgentResponse]
    total: int
    page: int
    size: int
    float_utilization: Decimal
    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    last_transaction_at: Optional[datetime]
    last_sync_at: Optional[datetime]
    created_at: datetime
    approved_at: Optional[datetime]

    class Config:
        orm_mode = True


# Pagination schemas
class PaginatedResponse(BaseResponse):
    total: int
    page: int
    size: int
    pages: int


class PaginatedUsers(PaginatedResponse):
    data: List[UserResponse]


class PaginatedAccounts(PaginatedResponse):
    data: List[AccountResponse]


class PaginatedTransactions(PaginatedResponse):
    data: List[TransactionResponse]


# Error schemas
class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    errors: Optional[dict] = None
    request_id: Optional[str] = None
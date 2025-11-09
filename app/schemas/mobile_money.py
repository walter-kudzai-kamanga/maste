from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class MobileMoneyPaymentRequest(BaseModel):
    """Request schema for mobile money payment"""
    account_id: str = Field(..., description="Bank account ID")
    provider: str = Field(..., description="Mobile money provider (ecocash, airtel_money)")
    phone_number: str = Field(..., description="Customer phone number")
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    currency: str = Field(default="MWK", description="Currency code")
    description: Optional[str] = Field(None, description="Payment description")


class MobileMoneyPaymentResponse(BaseModel):
    """Response schema for mobile money payment"""
    transaction_id: str = Field(..., description="Bank transaction ID")
    status: str = Field(..., description="Payment status (initiated, failed)")
    provider_transaction_id: Optional[str] = Field(None, description="Provider transaction ID")
    message: Optional[str] = Field(None, description="Status message")
    error: Optional[str] = Field(None, description="Error message if failed")


class TransactionStatusResponse(BaseModel):
    """Response schema for transaction status check"""
    transaction_id: str = Field(..., description="Bank transaction ID")
    status: str = Field(..., description="Transaction status")
    provider_transaction_id: Optional[str] = Field(None, description="Provider transaction ID")
    amount: Optional[Decimal] = Field(None, description="Transaction amount")
    currency: Optional[str] = Field(None, description="Currency code")
    timestamp: Optional[datetime] = Field(None, description="Transaction timestamp")
    error: Optional[str] = Field(None, description="Error message if any")


class RefundRequest(BaseModel):
    """Request schema for mobile money refund"""
    transaction_id: str = Field(..., description="Original bank transaction ID")
    provider_transaction_id: str = Field(..., description="Provider transaction ID")
    provider: str = Field(..., description="Mobile money provider")
    amount: Decimal = Field(..., gt=0, description="Refund amount")
    reason: str = Field(..., description="Refund reason")


class RefundResponse(BaseModel):
    """Response schema for mobile money refund"""
    transaction_id: str = Field(..., description="Original bank transaction ID")
    status: str = Field(..., description="Refund status")
    refund_transaction_id: Optional[str] = Field(None, description="Refund transaction ID")
    message: Optional[str] = Field(None, description="Status message")
    error: Optional[str] = Field(None, description="Error message if failed")


class ProviderListResponse(BaseModel):
    """Response schema for supported providers list"""
    providers: List[str] = Field(..., description="List of supported mobile money providers")


class MobileMoneyCallbackData(BaseModel):
    """Schema for mobile money callback data"""
    transaction_id: str = Field(..., description="Bank transaction ID")
    provider_transaction_id: str = Field(..., description="Provider transaction ID")
    status: str = Field(..., description="Transaction status")
    phone_number: Optional[str] = Field(None, description="Customer phone number")
    amount: Optional[Decimal] = Field(None, description="Transaction amount")
    currency: Optional[str] = Field(None, description="Currency code")
    timestamp: Optional[datetime] = Field(None, description="Transaction timestamp")
    error: Optional[str] = Field(None, description="Error message if any")
    metadata: Optional[dict] = Field(None, description="Additional metadata")
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class USSDRequest(BaseModel):
    """Request model for USSD API"""
    session_id: str = Field(..., description="Unique session ID for the USSD session")
    phone_number: str = Field(..., description="User's phone number in international format")
    text: str = Field(..., description="User input text (empty for first request)")
    service_code: str = Field(..., description="USSD service code (e.g., *123#)")
    network_code: Optional[str] = Field(None, description="Mobile network code")
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "12345",
                "phone_number": "263771234567",
                "text": "",
                "service_code": "*123#",
                "network_code": "Econet"
            }
        }

class USSDResponse(BaseModel):
    """Response model for USSD API"""
    message: str = Field(..., description="Response message to show to user")
    next_state: Optional[str] = Field(None, description="Next state in the USSD flow")
    is_end: bool = Field(False, description="Whether the USSD session should end")
    
    class Config:
        schema_extra = {
            "example": {
                "message": "Welcome to Agent Banking\n1. Login\n2. Register",
                "next_state": "WELCOME",
                "is_end": False
            }
        }

class USSDMenu(BaseModel):
    """Model for USSD menu options"""
    title: str
    options: List[Dict[str, str]]
    back_option: bool = True
    home_option: bool = True

class USSDState(str, Enum):
    """USSD flow states"""
    WELCOME = "WELCOME"
    ENTER_PHONE = "ENTER_PHONE"
    ENTER_PIN = "ENTER_PIN"
    MAIN_MENU = "MAIN_MENU"
    CHECK_BALANCE = "CHECK_BALANCE"
    SEND_MONEY_MENU = "SEND_MONEY_MENU"
    ENTER_RECIPIENT = "ENTER_RECIPIENT"
    ENTER_AMOUNT = "ENTER_AMOUNT"
    ENTER_REFERENCE = "ENTER_REFERENCE"
    CONFIRM_SEND_MONEY = "CONFIRM_SEND_MONEY"
    TRANSACTION_HISTORY = "TRANSACTION_HISTORY"
    BUY_AIRTIME = "BUY_AIRTIME"
    ENTER_AIRTIME_AMOUNT = "ENTER_AIRTIME_AMOUNT"
    CONFIRM_AIRTIME = "CONFIRM_AIRTIME"
    CHANGE_PIN = "CHANGE_PIN"
    ENTER_NEW_PIN = "ENTER_NEW_PIN"
    CONFIRM_NEW_PIN = "CONFIRM_NEW_PIN"
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime
import re
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.ussd import USSDRequest, USSDResponse, USSDMenu
from app.services import user_service, account_service, transaction_service
from app.models import Transaction, Account
from app.core.security import verify_pin

class USSDState(str, Enum):
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

class USSDSession:
    def __init__(self, session_id: str, phone_number: str):
        self.session_id = session_id
        self.phone_number = phone_number
        self.state = USSDState.WELCOME
        self.user = None
        self.accounts = []
        self.recipient_phone = None
        self.amount = None
        self.reference = None
        self.selected_account = None
        self.airtime_amount = None
        self.new_pin = None
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def update_state(self, state: USSDState):
        self.state = state
        self.updated_at = datetime.utcnow()

class USSDService:
    def __init__(self):
        self.sessions: Dict[str, USSDSession] = {}
        self.menu_options = {
            USSDState.MAIN_MENU: [
                {"option": "1", "text": "Check Balance", "next_state": USSDState.CHECK_BALANCE},
                {"option": "2", "text": "Send Money", "next_state": USSDState.SEND_MONEY_MENU},
                {"option": "3", "text": "Buy Airtime", "next_state": USSDState.BUY_AIRTIME},
                {"option": "4", "text": "Transaction History", "next_state": USSDState.TRANSACTION_HISTORY},
                {"option": "5", "text": "Change PIN", "next_state": USSDState.CHANGE_PIN},
            ],
            USSDState.SEND_MONEY_MENU: [
                {"option": "1", "text": "To Mobile Number", "next_state": USSDState.ENTER_RECIPIENT},
                {"option": "2", "text": "To Bank Account", "next_state": USSDState.ENTER_RECIPIENT},
                {"option": "0", "text": "Back", "next_state": USSDState.MAIN_MENU},
            ]
        }

    async def process_ussd_request(
        self, 
        db: AsyncSession,
        ussd_request: USSDRequest
    ) -> USSDResponse:
        session = self._get_or_create_session(ussd_request)
        
        try:
            if ussd_request.text == "":
                return self._handle_welcome(session)
            
            if session.state == USSDState.WELCOME:
                return await self._handle_welcome_response(db, session, ussd_request.text)
            
            elif session.state == USSDState.ENTER_PHONE:
                return await self._handle_phone_number(db, session, ussd_request.text)
            
            elif session.state == USSDState.ENTER_PIN:
                return await self._handle_pin_verification(db, session, ussd_request.text)
            
            elif session.state == USSDState.MAIN_MENU:
                return await self._handle_main_menu(session, ussd_request.text)
            
            elif session.state == USSDState.CHECK_BALANCE:
                return await self._handle_check_balance(db, session)
            
            elif session.state == USSDState.SEND_MONEY_MENU:
                return await self._handle_send_money_menu(session, ussd_request.text)
            
            elif session.state == USSDState.ENTER_RECIPIENT:
                return await self._handle_enter_recipient(db, session, ussd_request.text)
            
            elif session.state == USSDState.ENTER_AMOUNT:
                return await self._handle_enter_amount(session, ussd_request.text)
            
            elif session.state == USSDState.ENTER_REFERENCE:
                return await self._handle_enter_reference(session, ussd_request.text)
            
            elif session.state == USSDState.CONFIRM_SEND_MONEY:
                return await self._handle_confirm_send_money(db, session, ussd_request.text)
            
            elif session.state == USSDState.BUY_AIRTIME:
                return await self._handle_buy_airtime_menu(session, ussd_request.text)
            
            elif session.state == USSDState.ENTER_AIRTIME_AMOUNT:
                return await self._handle_enter_airtime_amount(session, ussd_request.text)
            
            elif session.state == USSDState.CONFIRM_AIRTIME:
                return await self._handle_confirm_airtime(db, session, ussd_request.text)
            
            elif session.state == USSDState.CHANGE_PIN:
                return await self._handle_change_pin(session, ussd_request.text)
            
            elif session.state == USSDState.ENTER_NEW_PIN:
                return await self._handle_enter_new_pin(session, ussd_request.text)
            
            elif session.state == USSDState.CONFIRM_NEW_PIN:
                return await self._handle_confirm_new_pin(db, session, ussd_request.text)
            
            return self._create_response("Invalid option. Please try again.", session.state)
            
        except Exception as e:
            # Clear session on error
            if session.session_id in self.sessions:
                del self.sessions[session.session_id]
            return self._create_response(f"An error occurred: {str(e)}", is_end=True)

    def _get_or_create_session(self, ussd_request: USSDRequest) -> USSDSession:
        if ussd_request.session_id in self.sessions:
            session = self.sessions[ussd_request.session_id]
            # Clear session if it's too old (30 minutes)
            if (datetime.utcnow() - session.updated_at).total_seconds() > 1800:
                del self.sessions[ussd_request.session_id]
                return self._create_new_session(ussd_request)
            return session
        return self._create_new_session(ussd_request)

    def _create_new_session(self, ussd_request: USSDRequest) -> USSDSession:
        session = USSDSession(
            session_id=ussd_request.session_id,
            phone_number=ussd_request.phone_number
        )
        self.sessions[ussd_request.session_id] = session
        return session

    def _handle_welcome(self, session: USSDSession) -> USSDResponse:
        session.update_state(USSDState.WELCOME)
        welcome_message = (
            "Welcome to Agent Banking\n"
            "1. Login\n"
            "2. Register\n"
            "3. Help"
        )
        return self._create_response(welcome_message, USSDState.ENTER_PHONE)

    async def _handle_welcome_response(
        self, 
        db: AsyncSession,
        session: USSDSession, 
        user_input: str
    ) -> USSDResponse:
        if user_input == "1":  # Login
            session.update_state(USSDState.ENTER_PHONE)
            return self._create_response("Enter your phone number (e.g., 0771234567):")
        elif user_input == "2":  # Register
            return self._create_response(
                "To register, please visit our nearest agent or branch with your ID.",
                is_end=True
            )
        elif user_input == "3":  # Help
            return self._create_response(
                "For assistance, call 1234 or visit our branches.",
                is_end=True
            )
        else:
            return self._create_response("Invalid option. Please try again.", USSDState.WELCOME)

    async def _handle_phone_number(
        self,
        db: AsyncSession,
        session: USSDSession,
        phone_number: str
    ) -> USSDResponse:
        # Clean and validate phone number
        phone_number = self._clean_phone_number(phone_number)
        if not self._is_valid_phone_number(phone_number):
            return self._create_response(
                "Invalid phone number. Please enter a valid number (e.g., 0771234567):",
                USSDState.ENTER_PHONE
            )
        
        # Check if user exists
        user = await user_service.get_by_phone(db, phone_number=phone_number)
        if not user:
            return self._create_response(
                "Phone number not registered. Please visit our branch to register.",
                is_end=True
            )
        
        session.user = user
        session.phone_number = phone_number
        session.update_state(USSDState.ENTER_PIN)
        return self._create_response("Enter your 4-digit PIN:")

    async def _handle_pin_verification(
        self,
        db: AsyncSession,
        session: USSDSession,
        pin: str
    ) -> USSDResponse:
        if not session.user:
            return self._handle_error("Session expired. Please start again.", is_end=True)
        
        # Verify PIN (in a real app, this would verify against hashed PIN)
        if not verify_pin(pin, session.user.hashed_pin):
            session.retry_count = getattr(session, 'retry_count', 0) + 1
            if session.retry_count >= 3:
                # Lock account after 3 failed attempts
                session.user.is_locked = True
                await db.commit()
                return self._handle_error(
                    "Too many failed attempts. Account locked. Please visit a branch.",
                    is_end=True
                )
            return self._create_response(
                f"Invalid PIN. {3 - session.retry_count} attempts remaining. Try again:",
                USSDState.ENTER_PIN
            )
        
        # Get user accounts
        session.accounts = await account_service.get_user_accounts(db, user_id=session.user.id)
        if not session.accounts:
            return self._handle_error("No accounts found for this user.", is_end=True)
        
        session.update_state(USSDState.MAIN_MENU)
        return self._show_menu(session, USSDState.MAIN_MENU)

    def _show_menu(self, session: USSDSession, menu_state: USSDState) -> USSDResponse:
        menu = self.menu_options.get(menu_state, [])
        menu_text = "\n".join([f"{item['option']}. {item['text']}" for item in menu])
        return self._create_response(menu_text, menu_state)

    async def _handle_main_menu(
        self,
        session: USSDSession,
        option: str
    ) -> USSDResponse:
        menu = self.menu_options.get(USSDState.MAIN_MENU, [])
        selected = next((item for item in menu if item["option"] == option), None)
        
        if not selected:
            return self._create_response(
                "Invalid option. Please try again:",
                USSDState.MAIN_MENU
            )
        
        next_state = selected["next_state"]
        session.update_state(next_state)
        
        if next_state == USSDState.CHECK_BALANCE:
            return await self._handle_check_balance(session)
        elif next_state == USSDState.SEND_MONEY_MENU:
            return self._show_menu(session, USSDState.SEND_MONEY_MENU)
        elif next_state == USSDState.BUY_AIRTIME:
            return self._create_response(
                "Enter phone number to buy airtime:",
                USSDState.ENTER_AIRTIME_AMOUNT
            )
        elif next_state == USSDState.TRANSACTION_HISTORY:
            return await self._handle_transaction_history(session)
        elif next_state == USSDState.CHANGE_PIN:
            return self._create_response(
                "Enter your current 4-digit PIN:",
                USSDState.CHANGE_PIN
            )
        
        return self._create_response("Invalid option. Please try again.", USSDState.MAIN_MENU)

    async def _handle_check_balance(
        self,
        session: USSDSession
    ) -> USSDResponse:
        if not session.accounts:
            return self._handle_error("No accounts found.", is_end=True)
        
        # For simplicity, show first account balance
        account = session.accounts[0]
        session.selected_account = account
        session.update_state(USSDState.MAIN_MENU)
        
        return self._create_response(
            f"Account: {account.account_number}\n"
            f"Balance: {account.currency} {account.balance:.2f}\n\n"
            "0. Back\n"
            "00. Home",
            USSDState.MAIN_MENU
        )

    async def _handle_send_money_menu(
        self,
        session: USSDSession,
        option: str
    ) -> USSDResponse:
        menu = self.menu_options.get(USSDState.SEND_MONEY_MENU, [])
        selected = next((item for item in menu if item["option"] == option), None)
        
        if not selected and option not in ["0", "00"]:
            return self._create_response(
                "Invalid option. Please try again:",
                USSDState.SEND_MONEY_MENU
            )
        
        if option == "0":  # Back
            session.update_state(USSDState.MAIN_MENU)
            return self._show_menu(session, USSDState.MAIN_MENU)
        elif option == "00":  # Home
            session.update_state(USSDState.MAIN_MENU)
            return self._show_menu(session, USSDState.MAIN_MENU)
        
        next_state = selected["next_state"]
        session.update_state(next_state)
        
        if next_state == USSDState.ENTER_RECIPIENT:
            return self._create_response(
                "Enter recipient's phone number:",
                USSDState.ENTER_RECIPIENT
            )
        
        return self._create_response("Invalid option. Please try again.", USSDState.SEND_MONEY_MENU)

    async def _handle_enter_recipient(
        self,
        db: AsyncSession,
        session: USSDSession,
        phone_number: str
    ) -> USSDResponse:
        # Clean and validate phone number
        phone_number = self._clean_phone_number(phone_number)
        if not self._is_valid_phone_number(phone_number):
            return self._create_response(
                "Invalid phone number. Please enter a valid number (e.g., 0771234567):",
                USSDState.ENTER_RECIPIENT
            )
        
        # Check if sending to self
        if phone_number == session.phone_number:
            return self._create_response(
                "Cannot send money to your own number. Please enter a different number:",
                USSDState.ENTER_RECIPIENT
            )
        
        # In a real app, you might want to verify the recipient exists
        session.recipient_phone = phone_number
        session.update_state(USSDState.ENTER_AMOUNT)
        
        return self._create_response(
            "Enter amount to send:",
            USSDState.ENTER_AMOUNT
        )

    async def _handle_enter_amount(
        self,
        session: USSDSession,
        amount_str: str
    ) -> USSDResponse:
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Amount must be greater than zero")
            
            # Check if user has sufficient balance
            if not session.accounts:
                return self._handle_error("No accounts found.", is_end=True)
            
            account = session.accounts[0]  # For simplicity, use first account
            if account.balance < amount:
                return self._create_response(
                    f"Insufficient balance. Your balance is {account.currency} {account.balance:.2f}\n"
                    "Enter a different amount:",
                    USSDState.ENTER_AMOUNT
                )
            
            session.amount = amount
            session.selected_account = account
            session.update_state(USSDState.ENTER_REFERENCE)
            
            return self._create_response(
                "Enter reference (optional):",
                USSDState.ENTER_REFERENCE
            )
        except ValueError:
            return self._create_response(
                "Invalid amount. Please enter a valid number:",
                USSDState.ENTER_AMOUNT
            )

    async def _handle_enter_reference(
        self,
        session: USSDSession,
        reference: str
    ) -> USSDResponse:
        session.reference = reference or "USSD Transfer"
        session.update_state(USSDState.CONFIRM_SEND_MONEY)
        
        return self._create_response(
            f"Send {session.amount:.2f} to {session.recipient_phone}\n"
            f"Ref: {session.reference}\n\n"
            "1. Confirm\n"
            "2. Cancel",
            USSDState.CONFIRM_SEND_MONEY
        )

    async def _handle_confirm_send_money(
        self,
        db: AsyncSession,
        session: USSDSession,
        option: str
    ) -> USSDResponse:
        if option == "2":  # Cancel
            return self._handle_transaction_cancelled(session)
        
        if option != "1":  # Not Confirm
            return self._create_response(
                "Invalid option. Please try again:",
                USSDState.CONFIRM_SEND_MONEY
            )
        
        # Process the transaction
        try:
            # In a real app, you would call your transaction service here
            transaction = await transaction_service.create_transfer(
                db=db,
                from_account_id=session.selected_account.id,
                to_phone=session.recipient_phone,
                amount=session.amount,
                reference=session.reference,
                user_id=session.user.id
            )
            
            # Clear session data
            session.recipient_phone = None
            session.amount = None
            session.reference = None
            session.update_state(USSDState.MAIN_MENU)
            
            return self._create_response(
                f"Success! You have sent {session.selected_account.currency} {session.amount:.2f} "
                f"to {session.recipient_phone}\n"
                f"New balance: {session.selected_account.currency} {session.selected_account.balance:.2f}\n\n"
                "0. Back\n"
                "00. Home",
                USSDState.MAIN_MENU
            )
        except Exception as e:
            return self._handle_error(
                f"Transaction failed: {str(e)}",
                is_end=True
            )

    async def _handle_buy_airtime_menu(
        self,
        session: USSDSession,
        option: str
    ) -> USSDResponse:
        if option == "0":  # Back
            session.update_state(USSDState.MAIN_MENU)
            return self._show_menu(session, USSDState.MAIN_MENU)
        elif option == "00":  # Home
            session.update_state(USSDState.MAIN_MENU)
            return self._show_menu(session, USSDState.MAIN_MENU)
        
        # For simplicity, assume any input is a phone number
        phone_number = self._clean_phone_number(option)
        if not self._is_valid_phone_number(phone_number):
            return self._create_response(
                "Invalid phone number. Please enter a valid number (e.g., 0771234567):",
                USSDState.BUY_AIRTIME
            )
        
        session.recipient_phone = phone_number
        session.update_state(USSDState.ENTER_AIRTIME_AMOUNT)
        
        return self._create_response(
            "Enter airtime amount:",
            USSDState.ENTER_AIRTIME_AMOUNT
        )

    async def _handle_enter_airtime_amount(
        self,
        session: USSDSession,
        amount_str: str
    ) -> USSDResponse:
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Amount must be greater than zero")
            
            # Check if user has sufficient balance
            if not session.accounts:
                return self._handle_error("No accounts found.", is_end=True)
            
            account = session.accounts[0]  # For simplicity, use first account
            if account.balance < amount:
                return self._create_response(
                    f"Insufficient balance. Your balance is {account.currency} {account.balance:.2f}\n"
                    "Enter a different amount:",
                    USSDState.ENTER_AIRTIME_AMOUNT
                )
            
            session.airtime_amount = amount
            session.selected_account = account
            session.update_state(USSDState.CONFIRM_AIRTIME)
            
            return self._create_response(
                f"Buy airtime for {session.recipient_phone}\n"
                f"Amount: {session.airtime_amount:.2f}\n\n"
                "1. Confirm\n"
                "2. Cancel",
                USSDState.CONFIRM_AIRTIME
            )
        except ValueError:
            return self._create_response(
                "Invalid amount. Please enter a valid number:",
                USSDState.ENTER_AIRTIME_AMOUNT
            )

    async def _handle_confirm_airtime(
        self,
        db: AsyncSession,
        session: USSDSession,
        option: str
    ) -> USSDResponse:
        if option == "2":  # Cancel
            return self._handle_transaction_cancelled(session)
        
        if option != "1":  # Not Confirm
            return self._create_response(
                "Invalid option. Please try again:",
                USSDState.CONFIRM_AIRTIME
            )
        
        # Process the airtime purchase
        try:
            # In a real app, you would integrate with an airtime vendor API here
            # For now, we'll just deduct from the account balance
            transaction = await transaction_service.create_airtime_purchase(
                db=db,
                account_id=session.selected_account.id,
                phone_number=session.recipient_phone,
                amount=session.airtime_amount,
                user_id=session.user.id
            )
            
            # Clear session data
            session.recipient_phone = None
            session.airtime_amount = None
            session.update_state(USSDState.MAIN_MENU)
            
            return self._create_response(
                f"Success! {session.airtime_amount:.2f} airtime purchased for {session.recipient_phone}\n"
                f"New balance: {session.selected_account.currency} {session.selected_account.balance:.2f}\n\n"
                "0. Back\n"
                "00. Home",
                USSDState.MAIN_MENU
            )
        except Exception as e:
            return self._handle_error(
                f"Failed to purchase airtime: {str(e)}",
                is_end=True
            )

    async def _handle_change_pin(
        self,
        session: USSDSession,
        current_pin: str
    ) -> USSDResponse:
        if not session.user:
            return self._handle_error("Session expired. Please start again.", is_end=True)
        
        # Verify current PIN
        if not verify_pin(current_pin, session.user.hashed_pin):
            session.retry_count = getattr(session, 'pin_retry_count', 0) + 1
            if session.pin_retry_count >= 3:
                # Lock account after 3 failed attempts
                session.user.is_locked = True
                await db.commit()
                return self._handle_error(
                    "Too many failed attempts. Account locked. Please visit a branch.",
                    is_end=True
                )
            return self._create_response(
                f"Invalid PIN. {3 - session.pin_retry_count} attempts remaining. Try again:",
                USSDState.CHANGE_PIN
            )
        
        session.update_state(USSDState.ENTER_NEW_PIN)
        return self._create_response(
            "Enter new 4-digit PIN:",
            USSDState.ENTER_NEW_PIN
        )

    async def _handle_enter_new_pin(
        self,
        session: USSDSession,
        new_pin: str
    ) -> USSDResponse:
        # Validate new PIN
        if not (new_pin.isdigit() and len(new_pin) == 4):
            return self._create_response(
                "PIN must be 4 digits. Please try again:",
                USSDState.ENTER_NEW_PIN
            )
        
        session.new_pin = new_pin
        session.update_state(USSDState.CONFIRM_NEW_PIN)
        
        return self._create_response(
            "Confirm new 4-digit PIN:",
            USSDState.CONFIRM_NEW_PIN
        )

    async def _handle_confirm_new_pin(
        self,
        db: AsyncSession,
        session: USSDSession,
        confirm_pin: str
    ) -> USSDResponse:
        if confirm_pin != session.new_pin:
            session.update_state(USSDState.ENTER_NEW_PIN)
            return self._create_response(
                "PINs do not match. Please try again.\n"
                "Enter new 4-digit PIN:",
                USSDState.ENTER_NEW_PIN
            )
        
        # Update user's PIN
        session.user.hashed_pin = get_password_hash(confirm_pin)
        await db.commit()
        
        session.update_state(USSDState.MAIN_MENU)
        return self._create_response(
            "PIN changed successfully!\n\n"
            "0. Back\n"
            "00. Home",
            USSDState.MAIN_MENU
        )

    async def _handle_transaction_history(
        self,
        session: USSDSession
    ) -> USSDResponse:
        if not session.accounts:
            return self._handle_error("No accounts found.", is_end=True)
        
        # For simplicity, show transactions for the first account
        account = session.accounts[0]
        transactions = await transaction_service.get_account_transactions(
            db=db,
            account_id=account.id,
            limit=5  # Show last 5 transactions
        )
        
        if not transactions:
            return self._create_response(
                "No recent transactions found.\n\n"
                "0. Back\n"
                "00. Home",
                USSDState.MAIN_MENU
            )
        
        transactions_text = "\n".join([
            f"{t.created_at.strftime('%d/%m %H:%M')} - {t.amount:.2f} - {t.reference}"
            for t in transactions
        ])
        
        return self._create_response(
            f"Last 5 transactions for {account.account_number}:\n"
            f"{transactions_text}\n\n"
            "0. Back\n"
            "00. Home",
            USSDState.MAIN_MENU
        )

    def _handle_transaction_cancelled(self, session: USSDSession) -> USSDResponse:
        # Clear transaction-related session data
        session.recipient_phone = None
        session.amount = None
        session.reference = None
        session.airtime_amount = None
        session.update_state(USSDState.MAIN_MENU)
        
        return self._create_response(
            "Transaction cancelled.\n\n"
            "0. Back\n"
            "00. Home",
            USSDState.MAIN_MENU
        )

    def _handle_error(self, message: str, is_end: bool = False) -> USSDResponse:
        return self._create_response(f"Error: {message}", is_end=is_end)

    def _create_response(
        self, 
        message: str, 
        next_state: Optional[USSDState] = None,
        is_end: bool = False
    ) -> USSDResponse:
        if next_state:
            return USSDResponse(
                message=message,
                next_state=next_state,
                is_end=is_end
            )
        return USSDResponse(
            message=message,
            is_end=is_end
        )

    def _clean_phone_number(self, phone: str) -> str:
        """Clean and standardize phone number format"""
        # Remove all non-digit characters
        cleaned = re.sub(r'\D', '', phone)
        
        # Handle Zimbabwean numbers (assume local format starts with 0)
        if cleaned.startswith('0') and len(cleaned) == 10:
            return '263' + cleaned[1:]  # Convert to international format
        elif cleaned.startswith('263') and len(cleaned) == 12:
            return cleaned  # Already in international format
        elif len(cleaned) == 9 and cleaned.startswith('7') or cleaned.startswith('77'):
            return '263' + cleaned  # Add country code
        
        return cleaned

    def _is_valid_phone_number(self, phone: str) -> bool:
        """Validate Zimbabwean phone numbers"""
        # Check if it's a valid Zimbabwean mobile number
        # Zimbabwe mobile numbers: 263 7[1-8] XXXXXXX
        pattern = r'^2637[1-8]\d{7}$'
        return bool(re.match(pattern, phone))

# Global instance of the USSD service
ussd_service = USSDService()
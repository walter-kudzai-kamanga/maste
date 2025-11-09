from typing import Optional, List, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from uuid import UUID, uuid4
from decimal import Decimal

from app.models.account import Account
from app.models.user import User
from app.models.schemas import AccountCreate, AccountUpdate
from app.models.enums import AccountType, AccountStatus
from app.core.config import settings


class AccountService:
    """Service for managing accounts."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def generate_account_number(self) -> str:
        """Generate a unique account number."""
        import random
        import string
        
        # Generate a 12-digit account number
        prefix = "ACC"
        digits = ''.join(random.choices(string.digits, k=9))
        return f"{prefix}{digits}"
    
    async def create_account(
        self, 
        account_data: AccountCreate, 
        created_by_user_id: UUID
    ) -> Account:
        """Create a new account."""
        # Check if user exists
        user_result = await self.db.execute(
            select(User).where(func.lower(User.id) == str(account_data.customer_id).lower())
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValueError("Customer not found")
        
        # Respect provided account number or generate one
        account_number = account_data.account_number or self.generate_account_number()
        
        # Create account
        account = Account(
            # Store primary key as string for SQLite
            id=str(uuid4()),
            account_number=account_number,
            # Store UUID as string for SQLite compatibility
            customer_id=str(account_data.customer_id),
            account_type=account_data.account_type,
            status=AccountStatus.ACTIVE,
            currency=account_data.currency or "USD",
            balance=account_data.initial_balance or Decimal("0.00"),
            available_balance=account_data.initial_balance or Decimal("0.00"),
            # Default limits; AccountCreate doesn't define these fields
            daily_limit=Decimal("1000.00"),
            monthly_limit=Decimal("10000.00"),
            single_transaction_limit=Decimal("500.00"),
            branch_code=getattr(account_data, "branch_code", None),
            description=getattr(account_data, "description", None)
        )
        
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        
        return account
    
    async def get_account_by_id(self, account_id: Union[str, UUID]) -> Optional[Account]:
        """Get account by ID.
        Cast ID to string for SQLite compatibility (UUID not supported as bind param)."""
        account_id_str = str(account_id)
        result = await self.db.execute(
            select(Account).where(Account.id == account_id_str)
        )
        return result.scalar_one_or_none()
    
    async def get_account_by_number(self, account_number: str) -> Optional[Account]:
        """Get account by account number."""
        result = await self.db.execute(
            select(Account).where(Account.account_number == account_number)
        )
        return result.scalar_one_or_none()
    
    async def get_user_accounts(self, user_id: Union[str, UUID]) -> List[Account]:
        """Get all accounts for a user (customer)."""
        result = await self.db.execute(
            select(Account).where(Account.customer_id == str(user_id))
        )
        return result.scalars().all()
    
    async def get_accounts(
        self,
        skip: int = 0,
        limit: int = 100,
        customer_id: Optional[str] = None,
        account_type: Optional[AccountType] = None,
        status: Optional[AccountStatus] = None
    ) -> List[Account]:
        """Get accounts with filters."""
        query = select(Account).options(selectinload(Account.customer))
        
        if customer_id:
            # customer_id stored as string for SQLite compatibility
            query = query.where(Account.customer_id == str(customer_id))
        if account_type:
            query = query.where(Account.account_type == account_type)
        if status:
            # allow string input from views
            if isinstance(status, str):
                try:
                    status = AccountStatus(status)
                except ValueError:
                    status = None
            if status:
                query = query.where(Account.status == status)
        
        query = query.order_by(Account.created_at.desc())
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_account_count(
        self,
        customer_id: Optional[str] = None,
        account_type: Optional[AccountType] = None,
        status: Optional[AccountStatus] = None
    ) -> int:
        """Get total count of accounts with filters."""
        from sqlalchemy import func

        query = select(func.count(Account.id))

        if customer_id:
            query = query.where(Account.customer_id == str(customer_id))
        if account_type:
            query = query.where(Account.account_type == account_type)
        if status:
            if isinstance(status, str):
                try:
                    status = AccountStatus(status)
                except ValueError:
                    status = None
            if status:
                query = query.where(Account.status == status)

        result = await self.db.execute(query)
        return result.scalar()
    
    async def update_account(
        self,
        account_id: Union[str, UUID],
        account_update: Union[AccountUpdate, dict]
    ) -> Optional[Account]:
        """Update account."""
        result = await self.db.execute(
            select(Account).where(Account.id == str(account_id))
        )
        account = result.scalar_one_or_none()

        if not account:
            return None

        # Update fields
        if hasattr(account_update, "dict"):
            update_data = account_update.dict(exclude_unset=True)
        elif isinstance(account_update, dict):
            update_data = account_update
        else:
            raise ValueError("Invalid account_update payload")

        for field, value in update_data.items():
            setattr(account, field, value)

        await self.db.commit()
        await self.db.refresh(account)

        return account
    
    async def activate_account(self, account_id: Union[str, UUID]) -> Optional[Account]:
        """Activate account."""
        result = await self.db.execute(
            select(Account).where(Account.id == str(account_id))
        )
        account = result.scalar_one_or_none()
        
        if not account:
            return None
        
        account.status = AccountStatus.ACTIVE
        await self.db.commit()
        await self.db.refresh(account)
        
        return account
    
    async def deactivate_account(self, account_id: Union[str, UUID]) -> Optional[Account]:
        """Deactivate account."""
        result = await self.db.execute(
            select(Account).where(Account.id == str(account_id))
        )
        account = result.scalar_one_or_none()
        
        if not account:
            return None
        
        account.status = AccountStatus.INACTIVE
        await self.db.commit()
        await self.db.refresh(account)
        
        return account
    
    async def update_balance(
        self,
        account_id: Union[str, UUID],
        amount: Decimal,
        is_credit: bool = False
    ) -> Optional[Account]:
        """Update account balance."""
        result = await self.db.execute(
            select(Account).where(Account.id == str(account_id))
        )
        account = result.scalar_one_or_none()
        
        if not account:
            return None
        
        if is_credit:
            account.balance += amount
            account.available_balance += amount
        else:
            account.balance -= amount
            account.available_balance -= amount
        
        await self.db.commit()
        await self.db.refresh(account)
        
        return account
    
    async def can_debit_account(self, account_id: Union[str, UUID], amount: Decimal) -> bool:
        """Check if account can be debited."""
        account = await self.get_account_by_id(account_id)
        if not account:
            return False
        
        # Check if account is active
        if account.status != AccountStatus.ACTIVE:
            return False
        
        # Check if sufficient balance
        if account.available_balance < amount:
            return False
        
        return True
    
    async def can_credit_account(self, account_id: Union[str, UUID]) -> bool:
        """Check if account can be credited."""
        account = await self.get_account_by_id(account_id)
        if not account:
            return False
        
        # Check if account is active
        if account.status != AccountStatus.ACTIVE:
            return False
        
        return True
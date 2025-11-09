from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.models.transaction import Transaction


class TransactionService:
    """Service for managing transactions."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_transactions(
        self,
        skip: int = 0,
        limit: int = 100,
        account_id: Optional[UUID] = None,
    ) -> List[Transaction]:
        """Get transactions with filters."""
        query = select(Transaction)
        
        if account_id:
            query = query.where(Transaction.account_id == account_id)
        
        query = query.order_by(Transaction.created_at.desc())
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
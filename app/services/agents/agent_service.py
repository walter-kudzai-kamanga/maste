from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from uuid import UUID, uuid4
from decimal import Decimal
from datetime import datetime, timedelta

from app.models.agent import Agent, AgentFloatAdjustment
from app.models.user import User
from app.models.schemas import AgentCreate, AgentUpdate, FloatAdjustmentRequest
from app.models.enums import AgentStatus, UserRole, AdjustmentType
from app.services.audit_service import AuditService


class AgentService:
    """Service for managing banking agents."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def generate_agent_code(self) -> str:
        """Generate unique agent code."""
        import random
        import string
        
        # Generate a 8-character agent code
        prefix = "AG"
        digits = ''.join(random.choices(string.digits, k=6))
        return f"{prefix}{digits}"
    
    async def create_agent(
        self, 
        agent_data: AgentCreate, 
        created_by_user_id: UUID
    ) -> Agent:
        """Create a new agent."""
        # Check if user exists and has agent role
        user_result = await self.db.execute(
            select(User).where(User.id == agent_data.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValueError("User not found")
        
        if user.role != UserRole.AGENT:
            raise ValueError("User does not have agent role")
        
        # Check if agent already exists for this user
        existing_agent = await self.get_agent_by_user_id(agent_data.user_id)
        if existing_agent:
            raise ValueError("Agent already exists for this user")
        
        # Generate unique agent code
        agent_code = self.generate_agent_code()
        
        # Create agent
        agent = Agent(
            id=uuid4(),
            user_id=agent_data.user_id,
            agent_code=agent_code,
            first_name=agent_data.first_name,
            last_name=agent_data.last_name,
            phone_number=agent_data.phone_number,
            email=agent_data.email,
            location=agent_data.location,
            region=agent_data.region,
            assigned_float=agent_data.assigned_float or Decimal("0.00"),
            current_float=agent_data.assigned_float or Decimal("0.00"),
            min_float=agent_data.min_float or Decimal("100.00"),
            max_float=agent_data.max_float or Decimal("10000.00"),
            status=AgentStatus.ACTIVE,
            created_by=created_by_user_id
        )
        
        self.db.add(agent)
        await self.db.commit()
        await self.db.refresh(agent)
        
        return agent
    
    async def get_agent_by_id(self, agent_id: UUID) -> Optional[Agent]:
        """Get agent by ID."""
        result = await self.db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        return result.scalar_one_or_none()
    
    async def get_agent_by_user_id(self, user_id: UUID) -> Optional[Agent]:
        """Get agent by user ID."""
        result = await self.db.execute(
            select(Agent).where(Agent.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_agent_by_code(self, agent_code: str) -> Optional[Agent]:
        """Get agent by agent code."""
        result = await self.db.execute(
            select(Agent).where(Agent.agent_code == agent_code)
        )
        return result.scalar_one_or_none()
    
    async def get_agents(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[AgentStatus] = None,
        region: Optional[str] = None
    ) -> List[Agent]:
        """Get agents with filters."""
        query = select(Agent)
        
        if status:
            query = query.where(Agent.status == status)
        if region:
            query = query.where(Agent.region == region)
        
        query = query.order_by(Agent.created_at.desc())
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update_agent(
        self, 
        agent_id: UUID, 
        agent_update: AgentUpdate
    ) -> Optional[Agent]:
        """Update agent."""
        result = await self.db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            return None
        
        # Update fields
        update_data = agent_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(agent, field, value)
        
        await self.db.commit()
        await self.db.refresh(agent)
        
        return agent
    
    async def adjust_float(
        self,
        agent_id: UUID,
        adjustment_data: FloatAdjustmentRequest,
        adjusted_by_user_id: UUID
    ) -> AgentFloatAdjustment:
        """Adjust agent float balance."""
        # Get agent
        agent = await self.get_agent_by_id(agent_id)
        if not agent:
            raise ValueError("Agent not found")
        
        # Calculate new float balance
        old_float = agent.current_float
        
        if adjustment_data.adjustment_type == AdjustmentType.INCREASE:
            new_float = old_float + adjustment_data.amount
        elif adjustment_data.adjustment_type == AdjustmentType.DECREASE:
            new_float = old_float - adjustment_data.amount
            if new_float < Decimal("0"):
                raise ValueError("Float balance cannot be negative")
        else:
            raise ValueError("Invalid adjustment type")
        
        # Check if new float is within limits
        if new_float < agent.min_float or new_float > agent.max_float:
            raise ValueError("New float balance is outside allowed limits")
        
        # Update agent float
        agent.current_float = new_float
        
        # Create adjustment record
        adjustment = AgentFloatAdjustment(
            id=uuid4(),
            agent_id=agent_id,
            adjustment_type=adjustment_data.adjustment_type,
            amount=adjustment_data.amount,
            previous_float=old_float,
            new_float=new_float,
            reason=adjustment_data.reason,
            adjusted_by=adjusted_by_user_id
        )
        
        self.db.add(adjustment)
        self.db.add(agent)
        await self.db.commit()
        await self.db.refresh(adjustment)
        
        return adjustment
    
    async def get_agent_float_adjustments(
        self,
        agent_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> List[AgentFloatAdjustment]:
        """Get float adjustment history for an agent."""
        result = await self.db.execute(
            select(AgentFloatAdjustment)
            .where(AgentFloatAdjustment.agent_id == agent_id)
            .order_by(AgentFloatAdjustment.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def activate_agent(self, agent_id: UUID) -> Optional[Agent]:
        """Activate agent."""
        result = await self.db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            return None
        
        agent.status = AgentStatus.ACTIVE
        await self.db.commit()
        await self.db.refresh(agent)
        
        return agent
    
    async def deactivate_agent(self, agent_id: UUID) -> Optional[Agent]:
        """Deactivate agent."""
        result = await self.db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            return None
        
        agent.status = AgentStatus.INACTIVE
        await self.db.commit()
        await self.db.refresh(agent)
        
        return agent
    
    async def update_agent_performance_metrics(
        self,
        agent_id: UUID,
        transactions_today: int = 0,
        total_transactions: int = 0,
        total_volume: Decimal = Decimal("0.00")
    ) -> Optional[Agent]:
        """Update agent performance metrics."""
        result = await self.db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            return None
        
        # Update metrics
        agent.transactions_today = transactions_today
        agent.total_transactions = total_transactions
        agent.total_volume = total_volume
        agent.last_transaction_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(agent)
        
        return agent
    
    async def get_low_float_agents(self, threshold: Decimal = Decimal("100.00")) -> List[Agent]:
        """Get agents with low float balance."""
        result = await self.db.execute(
            select(Agent).where(
                and_(
                    Agent.status == AgentStatus.ACTIVE,
                    Agent.current_float < threshold
                )
            )
        )
        return result.scalars().all()
    
    async def get_agent_statistics(self) -> Dict[str, Any]:
        """Get agent statistics."""
        from sqlalchemy import func
        
        # Total agents
        total_agents = await self.db.execute(select(func.count(Agent.id)))
        total_count = total_agents.scalar()
        
        # Active agents
        active_agents = await self.db.execute(
            select(func.count(Agent.id)).where(Agent.status == AgentStatus.ACTIVE)
        )
        active_count = active_agents.scalar()
        
        # Total float assigned
        total_float = await self.db.execute(
            select(func.sum(Agent.assigned_float))
        )
        total_float_sum = total_float.scalar() or Decimal("0.00")
        
        # Current total float
        current_float = await self.db.execute(
            select(func.sum(Agent.current_float))
        )
        current_float_sum = current_float.scalar() or Decimal("0.00")
        
        return {
            "total_agents": total_count,
            "active_agents": active_count,
            "inactive_agents": total_count - active_count,
            "total_float_assigned": float(total_float_sum),
            "current_total_float": float(current_float_sum)
        }
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Optional
from decimal import Decimal

from app.core.database import get_db
from app.models.schemas import (
    AgentCreate, AgentResponse, AgentUpdate, FloatAdjustmentRequest,
    FloatAdjustmentResponse, ErrorResponse, PaginatedAgents
)
from app.models.user import User
from app.models.enums import UserRole, AgentStatus
from app.api.dependencies import (
    get_current_active_staff, get_current_active_admin,
    get_current_active_agent
)
from app.services.agents.agent_service import AgentService
from app.services.audit_service import AuditService


router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/", response_model=AgentResponse, responses={400: {"model": ErrorResponse}})
async def create_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """Create a new agent (admin only)."""
    agent_service = AgentService(db)
    audit_service = AuditService(db)
    
    try:
        agent = await agent_service.create_agent(agent_data, current_user.id)
        
        # Log the action
        await audit_service.log_action(
            action="AGENT_CREATED",
            user_id=current_user.id,
            username=current_user.username,
            user_role=current_user.role.value,
            resource_type="Agent",
            resource_id=str(agent.id),
            action_details={
                "agent_code": agent.agent_code,
                "agent_name": f"{agent.first_name} {agent.last_name}",
                "assigned_float": float(agent.assigned_float)
            }
        )
        
        return agent
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=PaginatedAgents)
async def list_agents(
    skip: int = 0,
    limit: int = 100,
    status: Optional[AgentStatus] = None,
    region: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_staff)
):
    """List agents with filters (staff only)."""
    agent_service = AgentService(db)
    agents = await agent_service.get_agents(
        skip=skip, limit=limit, status=status, region=region
    )
    total = len(agents)  # In production, use separate count query
    
    return PaginatedAgents(
        items=agents,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/my-profile", response_model=AgentResponse)
async def get_my_agent_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_agent)
):
    """Get current user's agent profile."""
    agent_service = AgentService(db)
    agent = await agent_service.get_agent_by_user_id(current_user.id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent profile not found")
    
    return agent


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_staff)
):
    """Get agent by ID (staff only)."""
    agent_service = AgentService(db)
    agent = await agent_service.get_agent_by_id(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    agent_update: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """Update agent (admin only)."""
    agent_service = AgentService(db)
    audit_service = AuditService(db)
    
    # Get current agent for audit
    current_agent = await agent_service.get_agent_by_id(agent_id)
    if not current_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Store old values for audit
    old_values = {
        "status": current_agent.status.value,
        "location": current_agent.location,
        "region": current_agent.region,
        "min_float": float(current_agent.min_float),
        "max_float": float(current_agent.max_float)
    }
    
    updated_agent = await agent_service.update_agent(agent_id, agent_update)
    if not updated_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Log the update
    await audit_service.log_action(
        action="AGENT_UPDATED",
        user_id=current_user.id,
        username=current_user.username,
        user_role=current_user.role.value,
        resource_type="Agent",
        resource_id=str(agent_id),
        action_details={"updated_fields": list(agent_update.dict(exclude_unset=True).keys())},
        old_values=old_values,
        new_values=agent_update.dict(exclude_unset=True)
    )
    
    return updated_agent


@router.post("/{agent_id}/float-adjustment", response_model=FloatAdjustmentResponse)
async def adjust_agent_float(
    agent_id: UUID,
    adjustment_data: FloatAdjustmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_staff)
):
    """Adjust agent float balance (staff only)."""
    agent_service = AgentService(db)
    audit_service = AuditService(db)
    
    try:
        adjustment = await agent_service.adjust_float(
            agent_id, adjustment_data, current_user.id
        )
        
        # Log the adjustment
        await audit_service.log_action(
            action="AGENT_FLOAT_ADJUSTED",
            user_id=current_user.id,
            username=current_user.username,
            user_role=current_user.role.value,
            resource_type="Agent",
            resource_id=str(agent_id),
            action_details={
                "adjustment_type": adjustment_data.adjustment_type.value,
                "amount": float(adjustment_data.amount),
                "reason": adjustment_data.reason,
                "previous_float": float(adjustment.previous_float),
                "new_float": float(adjustment.new_float)
            }
        )
        
        return adjustment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}/float-history", response_model=List[FloatAdjustmentResponse])
async def get_agent_float_history(
    agent_id: UUID,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_staff)
):
    """Get agent float adjustment history (staff only)."""
    agent_service = AgentService(db)
    adjustments = await agent_service.get_agent_float_adjustments(agent_id, skip, limit)
    return adjustments


@router.post("/{agent_id}/activate")
async def activate_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """Activate agent (admin only)."""
    agent_service = AgentService(db)
    audit_service = AuditService(db)
    
    agent = await agent_service.activate_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Log the activation
    await audit_service.log_action(
        action="AGENT_ACTIVATED",
        user_id=current_user.id,
        username=current_user.username,
        user_role=current_user.role.value,
        resource_type="Agent",
        resource_id=str(agent_id),
        action_details={"activated_by": current_user.username}
    )
    
    return {"message": "Agent activated successfully"}


@router.post("/{agent_id}/deactivate")
async def deactivate_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """Deactivate agent (admin only)."""
    agent_service = AgentService(db)
    audit_service = AuditService(db)
    
    agent = await agent_service.deactivate_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Log the deactivation
    await audit_service.log_action(
        action="AGENT_DEACTIVATED",
        user_id=current_user.id,
        username=current_user.username,
        user_role=current_user.role.value,
        resource_type="Agent",
        resource_id=str(agent_id),
        action_details={"deactivated_by": current_user.username}
    )
    
    return {"message": "Agent deactivated successfully"}


@router.get("/statistics/overview")
async def get_agent_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_staff)
):
    """Get agent statistics (staff only)."""
    agent_service = AgentService(db)
    stats = await agent_service.get_agent_statistics()
    return stats


@router.get("/low-float", response_model=List[AgentResponse])
async def get_low_float_agents(
    threshold: float = 100.0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_staff)
):
    """Get agents with low float balance (staff only)."""
    agent_service = AgentService(db)
    agents = await agent_service.get_low_float_agents(Decimal(str(threshold)))
    return agents
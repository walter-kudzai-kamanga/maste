from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import json

from app.models.audit import AuditLog
from app.models.enums import AuditAction


class AuditService:
    """Service for managing audit logs."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log_action(
        self,
        action: AuditAction,
        user_id: Optional[UUID] = None,
        username: Optional[str] = None,
        user_role: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action_details: Optional[Dict[str, Any]] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> AuditLog:
        """Log an action to the audit log."""
        audit_log = AuditLog(
            user_id=user_id,
            username=username,
            user_role=user_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            action_details=action_details,
            old_values=old_values,
            new_values=new_values,
            success='Y' if success else 'N',
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            request_id=request_id
        )
        
        self.db.add(audit_log)
        await self.db.commit()
        await self.db.refresh(audit_log)
        
        return audit_log
    
    async def get_audit_logs(
        self,
        user_id: Optional[UUID] = None,
        action: Optional[AuditAction] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[AuditLog]:
        """Get audit logs with filters."""
        query = select(AuditLog)
        
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)
        
        query = query.order_by(AuditLog.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_audit_log_by_id(self, audit_id: UUID) -> Optional[AuditLog]:
        """Get audit log by ID."""
        result = await self.db.execute(
            select(AuditLog).where(AuditLog.id == audit_id)
        )
        return result.scalar_one_or_none()
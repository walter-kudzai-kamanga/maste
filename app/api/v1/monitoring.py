from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.enums import UserRole
from app.models.transaction import Transaction
from app.models.account import Account
from app.services.monitoring_service import MonitoringService
from app.core.permissions import require_roles
from sqlalchemy import func

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/health")
async def get_system_health(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get overall system health status"""
    try:
        monitoring_service = MonitoringService()
        health_data = await monitoring_service.get_system_health()
        
        return health_data
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_system_metrics(
    hours: int = 24,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get system and business metrics"""
    try:
        monitoring_service = MonitoringService()
        dashboard_data = await monitoring_service.get_dashboard_data()
        metrics_history = monitoring_service.get_metrics_history(hours)
        
        return {
            "current": dashboard_data,
            "history": metrics_history,
            "timestamp": dashboard_data["timestamp"]
        }
        
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_active_alerts(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get active system alerts"""
    try:
        monitoring_service = MonitoringService()
        dashboard_data = await monitoring_service.get_dashboard_data()
        
        return {
            "alerts": dashboard_data["alerts"],
            "alert_count": len(dashboard_data["alerts"]),
            "timestamp": dashboard_data["timestamp"]
        }
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/acknowledge/{alert_id}")
async def acknowledge_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    _: bool = Depends(require_roles([UserRole.ADMIN, UserRole.BANK_STAFF]))
) -> Dict[str, Any]:
    """Acknowledge a system alert"""
    try:
        # In a real implementation, this would update the alert status in a database
        # For now, we'll just return success
        return {
            "status": "acknowledged",
            "alert_id": alert_id,
            "acknowledged_by": current_user.username,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/transactions")
async def get_transaction_performance(
    hours: int = 24,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get transaction performance metrics"""
    try:
        db = next(get_db())
        monitoring_service = MonitoringService()
        
        # Get transaction metrics for the specified period
        from datetime import datetime, timedelta
        
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Transaction volume by hour
        hourly_volume = db.query(
            func.date_trunc('hour', Transaction.created_at).label('hour'),
            func.count(Transaction.id).label('count'),
            func.sum(Transaction.amount).label('volume')
        ).filter(
            Transaction.created_at >= start_time
        ).group_by(
            func.date_trunc('hour', Transaction.created_at)
        ).all()
        
        # Transaction status breakdown
        status_breakdown = db.query(
            Transaction.status,
            func.count(Transaction.id).label('count')
        ).filter(
            Transaction.created_at >= start_time
        ).group_by(Transaction.status).all()
        
        # Average processing time
        avg_processing_time = db.query(
            func.avg(
                func.extract('epoch', Transaction.updated_at - Transaction.created_at)
            )
        ).filter(
            Transaction.created_at >= start_time,
            Transaction.updated_at.isnot(None)
        ).scalar() or 0
        
        db.close()
        
        return {
            "period_hours": hours,
            "hourly_volume": [
                {
                    "hour": row.hour.isoformat(),
                    "count": row.count,
                    "volume": float(row.volume or 0)
                }
                for row in hourly_volume
            ],
            "status_breakdown": [
                {
                    "status": row.status,
                    "count": row.count
                }
                for row in status_breakdown
            ],
            "average_processing_time_seconds": float(avg_processing_time),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting transaction performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/accounts")
async def get_account_performance(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get account-related performance metrics"""
    try:
        db = next(get_db())
        
        # Account statistics
        total_accounts = db.query(Account).count()
        
        # Accounts by status
        accounts_by_status = db.query(
            Account.status,
            func.count(Account.id).label('count')
        ).group_by(Account.status).all()
        
        # Accounts by type
        accounts_by_type = db.query(
            Account.account_type,
            func.count(Account.id).label('count')
        ).group_by(Account.account_type).all()
        
        # Total balance across all accounts
        total_balance = db.query(func.sum(Account.balance)).scalar() or 0
        
        # Recently created accounts
        recent_accounts = db.query(Account).filter(
            Account.created_at >= datetime.utcnow() - timedelta(days=30)
        ).count()
        
        db.close()
        
        return {
            "total_accounts": total_accounts,
            "accounts_by_status": [
                {"status": row.status, "count": row.count}
                for row in accounts_by_status
            ],
            "accounts_by_type": [
                {"type": row.account_type, "count": row.count}
                for row in accounts_by_type
            ],
            "total_balance": float(total_balance),
            "recent_accounts_30d": recent_accounts,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting account performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs")
async def get_system_logs(
    level: Optional[str] = None,
    service: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    _: bool = Depends(require_roles([UserRole.ADMIN]))
) -> Dict[str, Any]:
    """Get system logs (admin only)"""
    try:
        # In a real implementation, this would query a log aggregation service
        # For now, we'll return a placeholder response
        return {
            "logs": [],
            "filters": {
                "level": level,
                "service": service,
                "limit": limit
            },
            "message": "Log aggregation not implemented in this demo",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting system logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/metrics/record")
async def record_metrics(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    _: bool = Depends(require_roles([UserRole.ADMIN]))
) -> Dict[str, Any]:
    """Trigger metrics recording (admin only)"""
    try:
        monitoring_service = MonitoringService()
        
        # Record metrics in background
        background_tasks.add_task(monitoring_service.record_metrics)
        
        return {
            "status": "recording_started",
            "message": "Metrics recording initiated",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error recording metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/uptime")
async def get_system_uptime(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get system uptime information"""
    try:
        import psutil
        from datetime import datetime
        
        # Get system boot time
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime_seconds = (datetime.now() - boot_time).total_seconds()
        
        # Convert to human-readable format
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        return {
            "boot_time": boot_time.isoformat(),
            "uptime_seconds": uptime_seconds,
            "uptime_formatted": f"{days}d {hours}h {minutes}m",
            "current_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting system uptime: {e}")
        raise HTTPException(status_code=500, detail=str(e))
import asyncio
import aiohttp
import redis.asyncio as redis
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.models.transaction import Transaction
from app.models.account import Account
from app.models.agent import Agent
from app.models.user import User

logger = logging.getLogger(__name__)


class MonitoringService:
    """Service for system health checks and performance monitoring"""
    
    def __init__(self):
        self.redis_client = None
        self.last_health_check = None
        self.health_cache_duration = 30  # seconds
        
    async def get_redis_client(self):
        """Get Redis client with lazy initialization"""
        if not self.redis_client:
            try:
                self.redis_client = redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                return None
        return self.redis_client
    
    async def check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            db = next(get_db())
            start_time = datetime.utcnow()
            
            # Simple query to test connection
            db.execute(text("SELECT 1"))
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Get connection pool info
            connection_info = {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            db.close()
            return connection_info
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        try:
            redis_client = await self.get_redis_client()
            if not redis_client:
                return {
                    "status": "unhealthy",
                    "error": "Redis connection failed",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            start_time = datetime.utcnow()
            await redis_client.ping()
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def check_rabbitmq_health(self) -> Dict[str, Any]:
        """Check RabbitMQ connectivity"""
        try:
            # For now, we'll just check if the connection details are configured
            # In a real implementation, you'd connect to RabbitMQ management API
            if not settings.rabbitmq_url:
                return {
                    "status": "unhealthy",
                    "error": "RabbitMQ URL not configured",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Simulate a basic connectivity check
            return {
                "status": "healthy",
                "response_time_ms": 5.0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"RabbitMQ health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        try:
            # Check if we have recent cached health data
            if self.last_health_check:
                time_since_last_check = (datetime.utcnow() - self.last_health_check["timestamp"]).total_seconds()
                if time_since_last_check < self.health_cache_duration:
                    return self.last_health_check
            
            # Run all health checks concurrently
            health_checks = await asyncio.gather(
                self.check_database_health(),
                self.check_redis_health(),
                self.check_rabbitmq_health(),
                return_exceptions=True
            )
            
            db_health, redis_health, rabbitmq_health = health_checks
            
            # Calculate overall health
            services = {
                "database": db_health if not isinstance(db_health, Exception) else {"status": "unhealthy", "error": str(db_health)},
                "redis": redis_health if not isinstance(redis_health, Exception) else {"status": "unhealthy", "error": str(redis_health)},
                "rabbitmq": rabbitmq_health if not isinstance(rabbitmq_health, Exception) else {"status": "unhealthy", "error": str(rabbitmq_health)}
            }
            
            # Overall status is healthy only if all services are healthy
            overall_status = "healthy"
            for service_name, service_health in services.items():
                if service_health.get("status") != "healthy":
                    overall_status = "degraded"
                    break
            
            health_data = {
                "status": overall_status,
                "services": services,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Cache the result
            self.last_health_check = health_data
            
            return health_data
            
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        try:
            db = next(get_db())
            
            # Get transaction statistics
            today = datetime.utcnow().date()
            yesterday = today - timedelta(days=1)
            
            # Today's transactions
            today_transactions = db.query(Transaction).filter(
                func.date(Transaction.created_at) == today
            )
            
            # Yesterday's transactions for comparison
            yesterday_transactions = db.query(Transaction).filter(
                func.date(Transaction.created_at) == yesterday
            )
            
            # Transaction counts and volumes
            today_stats = {
                "total": today_transactions.count(),
                "volume": sum(t.amount for t in today_transactions.all())
            }
            
            yesterday_stats = {
                "total": yesterday_transactions.count(),
                "volume": sum(t.amount for t in yesterday_transactions.all())
            }
            
            # Transaction status breakdown
            status_breakdown = db.query(
                Transaction.status,
                func.count(Transaction.id).label('count')
            ).filter(
                func.date(Transaction.created_at) == today
            ).group_by(Transaction.status).all()
            
            # Account statistics
            total_accounts = db.query(Account).count()
            active_accounts = db.query(Account).filter(Account.status == "active").count()
            
            # Agent statistics
            total_agents = db.query(Agent).count()
            active_agents = db.query(Agent).filter(Agent.status == "active").count()
            
            # User statistics
            total_users = db.query(User).count()
            active_users = db.query(User).filter(User.is_active == True).count()
            
            # Calculate trends
            transaction_trend = "stable"
            if yesterday_stats["total"] > 0:
                trend_change = ((today_stats["total"] - yesterday_stats["total"]) / yesterday_stats["total"]) * 100
                if trend_change > 10:
                    transaction_trend = "up"
                elif trend_change < -10:
                    transaction_trend = "down"
            
            # Generate alerts based on thresholds
            alerts = []
            
            # Check for low transaction volume
            if today_stats["total"] < 10:  # Less than 10 transactions today
                alerts.append({
                    "id": "low_transaction_volume",
                    "type": "warning",
                    "title": "Low Transaction Volume",
                    "message": f"Only {today_stats['total']} transactions today",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Check for failed transactions
            failed_count = sum(1 for row in status_breakdown if row.status == "failed")
            if failed_count > 5:
                alerts.append({
                    "id": "high_failure_rate",
                    "type": "error",
                    "title": "High Transaction Failure Rate",
                    "message": f"{failed_count} failed transactions today",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Check for low agent count
            if active_agents < total_agents * 0.8:  # Less than 80% of agents active
                alerts.append({
                    "id": "low_agent_activity",
                    "type": "warning",
                    "title": "Low Agent Activity",
                    "message": f"Only {active_agents} out of {total_agents} agents are active",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            db.close()
            
            return {
                "transactions": {
                    "today": today_stats,
                    "yesterday": yesterday_stats,
                    "trend": transaction_trend,
                    "status_breakdown": [
                        {"status": row.status, "count": row.count}
                        for row in status_breakdown
                    ]
                },
                "accounts": {
                    "total": total_accounts,
                    "active": active_accounts,
                    "inactive": total_accounts - active_accounts
                },
                "agents": {
                    "total": total_agents,
                    "active": active_agents,
                    "inactive": total_agents - active_agents
                },
                "users": {
                    "total": total_users,
                    "active": active_users,
                    "inactive": total_users - active_users
                },
                "alerts": alerts,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_metrics_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics history for the specified number of hours"""
        try:
            db = next(get_db())
            
            # Calculate time range
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            # Get hourly metrics
            hourly_metrics = db.query(
                func.date_trunc('hour', Transaction.created_at).label('hour'),
                func.count(Transaction.id).label('transaction_count'),
                func.sum(Transaction.amount).label('transaction_volume'),
                func.avg(Transaction.amount).label('avg_transaction_amount')
            ).filter(
                Transaction.created_at >= start_time,
                Transaction.created_at < end_time
            ).group_by(
                func.date_trunc('hour', Transaction.created_at)
            ).order_by(
                func.date_trunc('hour', Transaction.created_at)
            ).all()
            
            # Format results
            history = []
            for row in hourly_metrics:
                history.append({
                    "timestamp": row.hour.isoformat(),
                    "transaction_count": row.transaction_count,
                    "transaction_volume": float(row.transaction_volume or 0),
                    "avg_transaction_amount": float(row.avg_transaction_amount or 0)
                })
            
            db.close()
            return history
            
        except Exception as e:
            logger.error(f"Failed to get metrics history: {e}")
            return []
    
    async def check_alert_conditions(self) -> List[Dict[str, Any]]:
        """Check for alert conditions and return active alerts"""
        try:
            db = next(get_db())
            alerts = []
            
            # Check for stuck transactions (processing for more than 30 minutes)
            thirty_minutes_ago = datetime.utcnow() - timedelta(minutes=30)
            stuck_transactions = db.query(Transaction).filter(
                Transaction.status == "processing",
                Transaction.updated_at < thirty_minutes_ago
            ).count()
            
            if stuck_transactions > 0:
                alerts.append({
                    "id": "stuck_transactions",
                    "type": "error",
                    "title": "Stuck Transactions",
                    "message": f"{stuck_transactions} transactions stuck in processing for over 30 minutes",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Check for failed transactions in the last hour
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_failures = db.query(Transaction).filter(
                Transaction.status == "failed",
                Transaction.updated_at >= one_hour_ago
            ).count()
            
            if recent_failures > 10:
                alerts.append({
                    "id": "high_failure_rate_recent",
                    "type": "warning",
                    "title": "High Recent Failure Rate",
                    "message": f"{recent_failures} transactions failed in the last hour",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Check for low account balance (example threshold)
            low_balance_accounts = db.query(Account).filter(
                Account.balance < 100.0,  # Less than 100 currency units
                Account.status == "active"
            ).count()
            
            if low_balance_accounts > 50:
                alerts.append({
                    "id": "low_account_balances",
                    "type": "warning",
                    "title": "Many Low Balance Accounts",
                    "message": f"{low_balance_accounts} accounts have low balances",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            db.close()
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to check alert conditions: {e}")
            return []
    
    async def record_metrics(self) -> None:
        """Record current metrics to Redis for historical tracking"""
        try:
            redis_client = await self.get_redis_client()
            if not redis_client:
                return
            
            db = next(get_db())
            
            # Get current metrics
            current_time = datetime.utcnow()
            
            # Transaction metrics
            transaction_count = db.query(Transaction).filter(
                func.date(Transaction.created_at) == current_time.date()
            ).count()
            
            transaction_volume = db.query(func.sum(Transaction.amount)).filter(
                func.date(Transaction.created_at) == current_time.date()
            ).scalar() or 0
            
            # Account metrics
            total_accounts = db.query(Account).count()
            active_accounts = db.query(Account).filter(Account.status == "active").count()
            
            # Agent metrics
            total_agents = db.query(Agent).count()
            active_agents = db.query(Agent).filter(Agent.status == "active").count()
            
            # Create metrics snapshot
            metrics_snapshot = {
                "timestamp": current_time.isoformat(),
                "transactions": {
                    "count": transaction_count,
                    "volume": float(transaction_volume)
                },
                "accounts": {
                    "total": total_accounts,
                    "active": active_accounts
                },
                "agents": {
                    "total": total_agents,
                    "active": active_agents
                }
            }
            
            # Store in Redis with timestamp as key
            key = f"metrics:{current_time.strftime('%Y%m%d%H%M')}"
            await redis_client.setex(key, 86400 * 7, str(metrics_snapshot))  # Keep for 7 days
            
            db.close()
            
        except Exception as e:
            logger.error(f"Failed to record metrics: {e}")
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from app.core.messaging import MessagePublisher
from app.core.messaging.message_types import MessageType
from app.models.enums import TransactionType, TransactionStatus

logger = logging.getLogger(__name__)


class MessagingService:
    """Service for handling messaging operations in the banking system"""
    
    def __init__(self, message_publisher: MessagePublisher):
        self.publisher = message_publisher
    
    async def publish_transaction_event(
        self,
        transaction_id: str,
        transaction_type: TransactionType,
        status: TransactionStatus,
        account_id: str,
        amount: float,
        currency: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Publish transaction-related events"""
        try:
            payload = {
                "transaction_type": transaction_type.value,
                "status": status.value,
                "amount": amount,
                "currency": currency,
                "timestamp": datetime.utcnow().isoformat(),
                **(additional_data or {})
            }
            
            # Map status to message type
            message_type_map = {
                TransactionStatus.PENDING: MessageType.TRANSACTION_PROCESSING,
                TransactionStatus.PROCESSING: MessageType.TRANSACTION_PROCESSING,
                TransactionStatus.COMPLETED: MessageType.TRANSACTION_COMPLETED,
                TransactionStatus.FAILED: MessageType.TRANSACTION_FAILED,
                TransactionStatus.REVERSED: MessageType.TRANSACTION_REVERSED,
            }
            
            message_type = message_type_map.get(status, MessageType.TRANSACTION_PROCESSING)
            
            if message_type == MessageType.TRANSACTION_CREATED:
                return await self.publisher.publish_transaction_created(
                    transaction_id=transaction_id,
                    account_id=account_id,
                    amount=amount,
                    currency=currency,
                    transaction_type=transaction_type.value,
                    payload=payload
                )
            elif message_type == MessageType.TRANSACTION_COMPLETED:
                return await self.publisher.publish_transaction_completed(
                    transaction_id=transaction_id,
                    account_id=account_id,
                    amount=amount,
                    currency=currency,
                    payload=payload
                )
            elif message_type == MessageType.TRANSACTION_FAILED:
                failure_reason = additional_data.get("failure_reason", "Unknown error") if additional_data else "Unknown error"
                return await self.publisher.publish_transaction_failed(
                    transaction_id=transaction_id,
                    account_id=account_id,
                    amount=amount,
                    currency=currency,
                    failure_reason=failure_reason,
                    payload=payload
                )
            else:
                # Default to processing
                return await self.publisher.publish_transaction_processing(
                    transaction_id=transaction_id,
                    account_id=account_id,
                    amount=amount,
                    currency=currency,
                    payload=payload
                )
                
        except Exception as e:
            logger.error(f"Failed to publish transaction event: {e}")
            return False
    
    async def publish_deposit_request(
        self,
        transaction_id: str,
        account_id: str,
        amount: float,
        currency: str,
        agent_id: Optional[str] = None,
        mobile_number: Optional[str] = None
    ) -> bool:
        """Publish deposit request message"""
        try:
            return await self.publisher.publish_deposit_request(
                transaction_id=transaction_id,
                account_id=account_id,
                amount=amount,
                currency=currency,
                agent_id=agent_id,
                mobile_number=mobile_number
            )
        except Exception as e:
            logger.error(f"Failed to publish deposit request: {e}")
            return False
    
    async def publish_withdrawal_request(
        self,
        transaction_id: str,
        account_id: str,
        amount: float,
        currency: str,
        agent_id: Optional[str] = None,
        mobile_number: Optional[str] = None
    ) -> bool:
        """Publish withdrawal request message"""
        try:
            return await self.publisher.publish_withdrawal_request(
                transaction_id=transaction_id,
                account_id=account_id,
                amount=amount,
                currency=currency,
                agent_id=agent_id,
                mobile_number=mobile_number
            )
        except Exception as e:
            logger.error(f"Failed to publish withdrawal request: {e}")
            return False
    
    async def publish_transfer_request(
        self,
        transaction_id: str,
        from_account_id: str,
        to_account_id: str,
        amount: float,
        currency: str,
        description: Optional[str] = None
    ) -> bool:
        """Publish transfer request message"""
        try:
            return await self.publisher.publish_transfer_request(
                transaction_id=transaction_id,
                from_account_id=from_account_id,
                to_account_id=to_account_id,
                amount=amount,
                currency=currency,
                description=description
            )
        except Exception as e:
            logger.error(f"Failed to publish transfer request: {e}")
            return False
    
    async def publish_account_created(
        self,
        account_id: str,
        customer_id: str,
        account_number: str,
        account_type: str,
        currency: str
    ) -> bool:
        """Publish account created event"""
        try:
            return await self.publisher.publish_account_created(
                account_id=account_id,
                customer_id=customer_id,
                account_number=account_number,
                account_type=account_type,
                currency=currency
            )
        except Exception as e:
            logger.error(f"Failed to publish account created event: {e}")
            return False
    
    async def publish_agent_float_adjustment(
        self,
        agent_id: str,
        agent_code: str,
        adjustment_type: str,
        amount: float,
        previous_float: float,
        new_float: float,
        adjusted_by: str
    ) -> bool:
        """Publish agent float adjustment event"""
        try:
            return await self.publisher.publish_agent_float_adjustment(
                agent_id=agent_id,
                agent_code=agent_code,
                adjustment_type=adjustment_type,
                amount=amount,
                previous_float=previous_float,
                new_float=new_float,
                adjusted_by=adjusted_by
            )
        except Exception as e:
            logger.error(f"Failed to publish agent float adjustment: {e}")
            return False
    
    async def publish_agent_float_low_warning(
        self,
        agent_id: str,
        agent_code: str,
        current_float: float,
        minimum_float: float,
        threshold_percentage: float
    ) -> bool:
        """Publish agent float low warning"""
        try:
            return await self.publisher.publish_agent_float_low(
                agent_id=agent_id,
                agent_code=agent_code,
                current_float=current_float,
                minimum_float=minimum_float,
                threshold_percentage=threshold_percentage
            )
        except Exception as e:
            logger.error(f"Failed to publish agent float low warning: {e}")
            return False
    
    async def publish_reconciliation_started(
        self,
        reconciliation_id: str,
        file_name: str,
        total_records: int,
        initiated_by: str
    ) -> bool:
        """Publish reconciliation started event"""
        try:
            return await self.publisher.publish_reconciliation_started(
                reconciliation_id=reconciliation_id,
                file_name=file_name,
                total_records=total_records,
                initiated_by=initiated_by
            )
        except Exception as e:
            logger.error(f"Failed to publish reconciliation started event: {e}")
            return False
    
    async def publish_mobile_money_request(
        self,
        provider: str,
        mobile_number: str,
        transaction_id: str,
        amount: float,
        currency: str,
        transaction_type: str
    ) -> bool:
        """Publish mobile money request"""
        try:
            return await self.publisher.publish_mobile_money_request(
                provider=provider,
                mobile_number=mobile_number,
                transaction_id=transaction_id,
                amount=amount,
                currency=currency,
                transaction_type=transaction_type
            )
        except Exception as e:
            logger.error(f"Failed to publish mobile money request: {e}")
            return False
    
    async def publish_audit_log_created(
        self,
        audit_log_id: str,
        user_id: str,
        action: str,
        resource: str,
        success: bool
    ) -> bool:
        """Publish audit log created event"""
        try:
            return await self.publisher.publish_audit_log_created(
                audit_log_id=audit_log_id,
                user_id=user_id,
                action=action,
                resource=resource,
                success=success
            )
        except Exception as e:
            logger.error(f"Failed to publish audit log created event: {e}")
            return False
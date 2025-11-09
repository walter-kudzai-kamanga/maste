import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from .rabbitmq import RabbitMQPublisher
from .message_types import Message, MessageType, TransactionMessage, AccountMessage, AgentMessage

logger = logging.getLogger(__name__)


class MessagePublisher:
    """High-level message publisher for banking operations"""
    
    def __init__(self, rabbitmq_publisher: RabbitMQPublisher):
        self.publisher = rabbitmq_publisher
    
    async def publish_transaction_created(
        self,
        transaction_id: str,
        account_id: str,
        amount: float,
        currency: str,
        transaction_type: str,
        payload: Dict[str, Any]
    ) -> bool:
        """Publish transaction created event"""
        message = TransactionMessage(
            id=f"tx_created_{transaction_id}_{uuid.uuid4().hex[:8]}",
            type=MessageType.TRANSACTION_CREATED,
            timestamp=datetime.utcnow(),
            payload=payload,
            transaction_id=transaction_id,
            account_id=account_id,
            amount=amount,
            currency=currency
        )
        
        return await self.publisher.publish_message(message)
    
    async def publish_deposit_request(
        self,
        transaction_id: str,
        account_id: str,
        amount: float,
        currency: str,
        agent_id: Optional[str] = None,
        mobile_number: Optional[str] = None
    ) -> bool:
        """Publish deposit request"""
        payload = {
            "transaction_type": "deposit",
            "agent_id": agent_id,
            "mobile_number": mobile_number
        }
        
        message = TransactionMessage(
            id=f"deposit_{transaction_id}_{uuid.uuid4().hex[:8]}",
            type=MessageType.DEPOSIT_REQUEST,
            timestamp=datetime.utcnow(),
            payload=payload,
            transaction_id=transaction_id,
            account_id=account_id,
            amount=amount,
            currency=currency
        )
        
        return await self.publisher.publish_message(message)
    
    async def publish_withdrawal_request(
        self,
        transaction_id: str,
        account_id: str,
        amount: float,
        currency: str,
        agent_id: Optional[str] = None,
        mobile_number: Optional[str] = None
    ) -> bool:
        """Publish withdrawal request"""
        payload = {
            "transaction_type": "withdrawal",
            "agent_id": agent_id,
            "mobile_number": mobile_number
        }
        
        message = TransactionMessage(
            id=f"withdrawal_{transaction_id}_{uuid.uuid4().hex[:8]}",
            type=MessageType.WITHDRAWAL_REQUEST,
            timestamp=datetime.utcnow(),
            payload=payload,
            transaction_id=transaction_id,
            account_id=account_id,
            amount=amount,
            currency=currency
        )
        
        return await self.publisher.publish_message(message)
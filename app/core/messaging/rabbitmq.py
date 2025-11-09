import json
import logging
import asyncio
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime
import aio_pika
from aio_pika import connect_robust, Message, Channel, Exchange, Queue, Connection
from aio_pika.abc import AbstractIncomingMessage

from .message_types import Message, MessageType, QueueName

logger = logging.getLogger(__name__)


class RabbitMQConnection:
    """RabbitMQ connection manager"""
    
    def __init__(self, connection_url: str = "amqp://guest:guest@localhost/"):
        self.connection_url = connection_url
        self.connection: Optional[Connection] = None
        self.channel: Optional[Channel] = None
        self.exchanges: Dict[str, Exchange] = {}
        self.queues: Dict[str, Queue] = {}
        self._lock = asyncio.Lock()
        
    async def connect(self) -> None:
        """Establish connection to RabbitMQ"""
        try:
            self.connection = await connect_robust(self.connection_url)
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)
            logger.info("Connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close connection to RabbitMQ"""
        try:
            if self.channel and not self.channel.is_closed:
                await self.channel.close()
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")
    
    async def declare_exchange(self, name: str, exchange_type: str = "topic", durable: bool = True) -> Exchange:
        """Declare an exchange"""
        if name in self.exchanges:
            return self.exchanges[name]
        
        exchange = await self.channel.declare_exchange(
            name=name,
            type=exchange_type,
            durable=durable
        )
        self.exchanges[name] = exchange
        return exchange
    
    async def declare_queue(self, name: str, durable: bool = True, arguments: Optional[Dict] = None) -> Queue:
        """Declare a queue"""
        if name in self.queues:
            return self.queues[name]
        
        queue = await self.channel.declare_queue(
            name=name,
            durable=durable,
            arguments=arguments or {}
        )
        self.queues[name] = queue
        return queue
    
    async def bind_queue_to_exchange(self, queue_name: str, exchange_name: str, routing_key: str) -> None:
        """Bind a queue to an exchange with a routing key"""
        queue = await self.declare_queue(queue_name)
        exchange = await self.declare_exchange(exchange_name)
        await queue.bind(exchange, routing_key)
    
    async def setup_default_exchanges_and_queues(self) -> None:
        """Setup default exchanges and queues for the banking system"""
        # Declare main exchange
        main_exchange = await self.declare_exchange("banking.exchange", "topic")
        
        # Declare and bind queues
        for queue_name in QueueName:
            queue = await self.declare_queue(queue_name.value, durable=True)
            
            # Bind queue to exchange with appropriate routing key
            routing_key = f"banking.{queue_name.value}.#"
            await queue.bind(main_exchange, routing_key)
            
            logger.info(f"Declared queue {queue_name.value} and bound to exchange")
    
    @property
    def is_connected(self) -> bool:
        """Check if connection is established"""
        return self.connection is not None and not self.connection.is_closed


class RabbitMQPublisher:
    """RabbitMQ message publisher"""
    
    def __init__(self, connection: RabbitMQConnection):
        self.connection = connection
        self.exchange_name = "banking.exchange"
    
    async def publish_message(
        self,
        message: Message,
        routing_key: Optional[str] = None,
        exchange_name: Optional[str] = None,
        persistent: bool = True,
        priority: int = 0
    ) -> bool:
        """Publish a message to RabbitMQ"""
        if not self.connection.is_connected:
            logger.error("Cannot publish message: not connected to RabbitMQ")
            return False
        
        try:
            # Use provided routing key or generate from message type
            if not routing_key:
                routing_key = f"banking.{QueueName.get_queue_for_message_type(message.type)}.{message.type.value}"
            
            # Get exchange
            exchange_name = exchange_name or self.exchange_name
            exchange = await self.connection.declare_exchange(exchange_name)
            
            # Serialize message
            message_body = json.dumps(message.dict(), default=str).encode()
            
            # Create message properties
            message_properties = {
                "message_id": message.id,
                "timestamp": datetime.utcnow(),
                "content_type": "application/json",
                "delivery_mode": 2 if persistent else 1,  # 2 = persistent, 1 = transient
                "priority": priority,
                "headers": {
                    "message_type": message.type.value,
                    "retry_count": message.retry_count,
                    "correlation_id": message.correlation_id or "",
                    "reply_to": message.reply_to or ""
                }
            }
            
            # Publish message
            await exchange.publish(
                Message(message_body, **message_properties),
                routing_key=routing_key
            )
            
            logger.info(f"Published message {message.id} of type {message.type.value} to {routing_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish message {message.id}: {e}")
            return False
    
    async def publish_transaction_message(
        self,
        transaction_id: str,
        message_type: MessageType,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish a transaction-related message"""
        message = Message(
            id=f"{transaction_id}_{message_type.value}_{datetime.utcnow().timestamp()}",
            type=message_type,
            timestamp=datetime.utcnow(),
            payload=payload,
            correlation_id=correlation_id or transaction_id
        )
        
        return await self.publish_message(message)


class RabbitMQConsumer:
    """RabbitMQ message consumer"""
    
    def __init__(self, connection: RabbitMQConnection):
        self.connection = connection
        self.consumers: Dict[str, Callable] = {}
        self.running = False
    
    async def register_consumer(
        self,
        queue_name: str,
        message_handler: Callable[[AbstractIncomingMessage], Any]
    ) -> None:
        """Register a message handler for a queue"""
        self.consumers[queue_name] = message_handler
        logger.info(f"Registered consumer for queue: {queue_name}")
    
    async def start_consuming(self) -> None:
        """Start consuming messages from registered queues"""
        if not self.connection.is_connected:
            logger.error("Cannot start consuming: not connected to RabbitMQ")
            return
        
        self.running = True
        
        for queue_name, handler in self.consumers.items():
            queue = await self.connection.declare_queue(queue_name)
            await queue.consume(self._create_message_handler(handler))
            logger.info(f"Started consuming from queue: {queue_name}")
    
    async def stop_consuming(self) -> None:
        """Stop consuming messages"""
        self.running = False
        logger.info("Stopped consuming messages")
    
    def _create_message_handler(self, handler: Callable) -> Callable:
        """Create a message handler wrapper"""
        async def message_handler(message: AbstractIncomingMessage) -> None:
            async with message.process():
                try:
                    # Deserialize message
                    body = json.loads(message.body.decode())
                    
                    # Create Message object
                    msg = Message(
                        id=message.message_id or message.body.decode()[:50],
                        type=MessageType(message.headers.get("message_type", "unknown")),
                        timestamp=message.timestamp or datetime.utcnow(),
                        payload=body,
                        correlation_id=message.headers.get("correlation_id"),
                        reply_to=message.headers.get("reply_to"),
                        retry_count=int(message.headers.get("retry_count", 0)),
                        max_retries=int(message.headers.get("max_retries", 3))
                    )
                    
                    # Call the actual handler
                    await handler(msg)
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Message will be requeued due to message.process() context manager
        
        return message_handler
    
    async def consume_single_message(
        self,
        queue_name: str,
        timeout: float = 30.0
    ) -> Optional[Message]:
        """Consume a single message from a queue"""
        if not self.connection.is_connected:
            logger.error("Cannot consume message: not connected to RabbitMQ")
            return None
        
        try:
            queue = await self.connection.declare_queue(queue_name)
            
            # Try to get a message
            message = await queue.get(timeout=timeout, fail=False)
            
            if message:
                async with message.process():
                    body = json.loads(message.body.decode())
                    return Message(
                        id=message.message_id or message.body.decode()[:50],
                        type=MessageType(message.headers.get("message_type", "unknown")),
                        timestamp=message.timestamp or datetime.utcnow(),
                        payload=body,
                        correlation_id=message.headers.get("correlation_id"),
                        reply_to=message.headers.get("reply_to"),
                        retry_count=int(message.headers.get("retry_count", 0)),
                        max_retries=int(message.headers.get("max_retries", 3))
                    )
            
            return None
            
        except asyncio.TimeoutError:
            logger.debug(f"Timeout waiting for message from queue {queue_name}")
            return None
        except Exception as e:
            logger.error(f"Error consuming message from queue {queue_name}: {e}")
            return None
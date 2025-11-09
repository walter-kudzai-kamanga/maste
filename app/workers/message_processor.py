import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

from app.core.messaging import RabbitMQConnection, RabbitMQConsumer, MessagePublisher
from app.core.messaging.message_types import Message, MessageType, TransactionMessage
from app.core.config import settings
from app.core.database import get_db_session
from app.services.payment_service import PaymentService
from app.services.account_service import AccountService
from app.models.enums import TransactionType, TransactionStatus

logger = logging.getLogger(__name__)


class MessageProcessor:
    """Background worker for processing messages from RabbitMQ"""
    
    def __init__(self):
        self.rabbitmq_connection = RabbitMQConnection(settings.rabbitmq_url)
        self.rabbitmq_consumer = RabbitMQConsumer(self.rabbitmq_connection)
        self.running = False
        self.processors = {
            MessageType.DEPOSIT_REQUEST: self.process_deposit_request,
            MessageType.WITHDRAWAL_REQUEST: self.process_withdrawal_request,
            MessageType.TRANSFER_REQUEST: self.process_transfer_request,
            MessageType.TRANSACTION_PROCESSING: self.process_transaction_processing,
        }
    
    async def start(self) -> None:
        """Start the message processor"""
        try:
            # Connect to RabbitMQ
            await self.rabbitmq_connection.connect()
            await self.rabbitmq_connection.setup_default_exchanges_and_queues()
            
            # Register message handlers
            await self.register_handlers()
            
            # Start consuming messages
            await self.rabbitmq_consumer.start_consuming()
            
            self.running = True
            logger.info("Message processor started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start message processor: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the message processor"""
        self.running = False
        await self.rabbitmq_consumer.stop_consuming()
        await self.rabbitmq_connection.disconnect()
        logger.info("Message processor stopped")
    
    async def register_handlers(self) -> None:
        """Register message handlers for different queue types"""
        # Register handlers for different queues
        await self.rabbitmq_consumer.register_consumer("deposits", self.handle_deposit_message)
        await self.rabbitmq_consumer.register_consumer("withdrawals", self.handle_withdrawal_message)
        await self.rabbitmq_consumer.register_consumer("transfers", self.handle_transfer_message)
        await self.rabbitmq_consumer.register_consumer("transactions", self.handle_transaction_message)
    
    async def handle_deposit_message(self, message: Message) -> None:
        """Handle deposit-related messages"""
        try:
            logger.info(f"Processing deposit message: {message.id}")
            
            if message.type == MessageType.DEPOSIT_REQUEST:
                await self.process_deposit_request(message)
            else:
                logger.warning(f"Unhandled deposit message type: {message.type}")
                
        except Exception as e:
            logger.error(f"Error processing deposit message {message.id}: {e}")
    
    async def handle_withdrawal_message(self, message: Message) -> None:
        """Handle withdrawal-related messages"""
        try:
            logger.info(f"Processing withdrawal message: {message.id}")
            
            if message.type == MessageType.WITHDRAWAL_REQUEST:
                await self.process_withdrawal_request(message)
            else:
                logger.warning(f"Unhandled withdrawal message type: {message.type}")
                
        except Exception as e:
            logger.error(f"Error processing withdrawal message {message.id}: {e}")
    
    async def handle_transfer_message(self, message: Message) -> None:
        """Handle transfer-related messages"""
        try:
            logger.info(f"Processing transfer message: {message.id}")
            
            if message.type == MessageType.TRANSFER_REQUEST:
                await self.process_transfer_request(message)
            else:
                logger.warning(f"Unhandled transfer message type: {message.type}")
                
        except Exception as e:
            logger.error(f"Error processing transfer message {message.id}: {e}")
    
    async def handle_transaction_message(self, message: Message) -> None:
        """Handle general transaction messages"""
        try:
            logger.info(f"Processing transaction message: {message.id}")
            
            processor = self.processors.get(message.type)
            if processor:
                await processor(message)
            else:
                logger.warning(f"No processor for message type: {message.type}")
                
        except Exception as e:
            logger.error(f"Error processing transaction message {message.id}: {e}")
    
    async def process_deposit_request(self, message: Message) -> None:
        """Process a deposit request"""
        async with get_db_session() as db:
            try:
                transaction_id = message.payload.get("transaction_id")
                if not transaction_id:
                    logger.error("No transaction_id in deposit message payload")
                    return
                
                payment_service = PaymentService(db)
                
                # Get the transaction
                from sqlalchemy import select
                result = await db.execute(
                    select(Transaction).where(Transaction.transaction_id == transaction_id)
                )
                transaction = result.scalar_one_or_none()
                
                if not transaction:
                    logger.error(f"Transaction not found: {transaction_id}")
                    return
                
                # Process the deposit
                success = await payment_service.process_transaction(transaction.id)
                
                if success:
                    logger.info(f"Successfully processed deposit transaction: {transaction_id}")
                else:
                    logger.error(f"Failed to process deposit transaction: {transaction_id}")
                    
            except Exception as e:
                logger.error(f"Error processing deposit request: {e}")
                await db.rollback()
    
    async def process_withdrawal_request(self, message: Message) -> None:
        """Process a withdrawal request"""
        async with get_db_session() as db:
            try:
                transaction_id = message.payload.get("transaction_id")
                if not transaction_id:
                    logger.error("No transaction_id in withdrawal message payload")
                    return
                
                payment_service = PaymentService(db)
                
                # Get the transaction
                from sqlalchemy import select
                result = await db.execute(
                    select(Transaction).where(Transaction.transaction_id == transaction_id)
                )
                transaction = result.scalar_one_or_none()
                
                if not transaction:
                    logger.error(f"Transaction not found: {transaction_id}")
                    return
                
                # Process the withdrawal
                success = await payment_service.process_transaction(transaction.id)
                
                if success:
                    logger.info(f"Successfully processed withdrawal transaction: {transaction_id}")
                else:
                    logger.error(f"Failed to process withdrawal transaction: {transaction_id}")
                    
            except Exception as e:
                logger.error(f"Error processing withdrawal request: {e}")
                await db.rollback()
    
    async def process_transfer_request(self, message: Message) -> None:
        """Process a transfer request"""
        async with get_db_session() as db:
            try:
                transaction_id = message.payload.get("transaction_id")
                if not transaction_id:
                    logger.error("No transaction_id in transfer message payload")
                    return
                
                payment_service = PaymentService(db)
                
                # Get the transaction
                from sqlalchemy import select
                result = await db.execute(
                    select(Transaction).where(Transaction.transaction_id == transaction_id)
                )
                transaction = result.scalar_one_or_none()
                
                if not transaction:
                    logger.error(f"Transaction not found: {transaction_id}")
                    return
                
                # Process the transfer
                success = await payment_service.process_transaction(transaction.id)
                
                if success:
                    logger.info(f"Successfully processed transfer transaction: {transaction_id}")
                else:
                    logger.error(f"Failed to process transfer transaction: {transaction_id}")
                    
            except Exception as e:
                logger.error(f"Error processing transfer request: {e}")
                await db.rollback()
    
    async def process_transaction_processing(self, message: Message) -> None:
        """Process general transaction processing messages"""
        # This can be used for retry logic, status updates, etc.
        logger.info(f"Processing transaction message: {message.id}")
        # Add specific processing logic here as needed


async def run_message_processor() -> None:
    """Run the message processor"""
    processor = MessageProcessor()
    
    try:
        await processor.start()
        
        # Keep the processor running
        while processor.running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    finally:
        await processor.stop()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the message processor
    asyncio.run(run_message_processor())
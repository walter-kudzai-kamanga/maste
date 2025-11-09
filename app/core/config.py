from pydantic import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Application
    app_name: str = "Agent Banking Platform"
    app_version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"
    
    # Database
    database_url: str = "postgresql+asyncpg://banking_user:banking_password@localhost:5432/banking_db"
    test_database_url: str = "postgresql+asyncpg://banking_user:banking_password@localhost:5432/banking_test_db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = "banking.exchange"
    rabbitmq_prefetch_count: int = 10
    rabbitmq_retry_delay: int = 5  # seconds
    rabbitmq_max_retries: int = 3
    
    # Security
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # File Storage
    upload_dir: str = "/tmp/uploads"
    max_file_size: int = 10485760  # 10MB
    
    # External APIs
    ecocash_api_url: str = "https://api.ecocash.co.zw"
    airtel_money_api_url: str = "https://api.airtel.co.zw"
    
    # Monitoring
    prometheus_port: int = 8001
    enable_metrics: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create global settings instance
settings = Settings()

# Database table prefixes
TABLE_PREFIX = "banking_"
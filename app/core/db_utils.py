"""
Database utilities for handling UUID compatibility across different database backends.
"""

from sqlalchemy import String, Column
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from uuid import uuid4, UUID
from app.core.config import settings

def get_uuid_column(**kwargs):
    """
    Returns a UUID column appropriate for the current database backend.
    For SQLite: Uses String(36) to store UUID as text
    For PostgreSQL: Uses native UUID type
    """
    # Set default primary key behavior
    if 'primary_key' not in kwargs:
        kwargs['primary_key'] = True
    
    if 'default' not in kwargs:
        kwargs['default'] = uuid4
    
    # Check if we're using SQLite
    if 'sqlite' in settings.database_url:
        return Column(String(36), **kwargs)
    else:
        return Column(PostgreSQLUUID(as_uuid=True), **kwargs)

def get_foreign_key_uuid_column(*args, **kwargs):
    """
    Returns a UUID foreign key column appropriate for the current database backend.
    """
    # Set default nullable behavior if not provided
    if 'nullable' not in kwargs:
        kwargs['nullable'] = True
    
    # Check if we're using SQLite
    if 'sqlite' in settings.database_url:
        return Column(String(36), *args, **kwargs)
    else:
        return Column(PostgreSQLUUID(as_uuid=True), *args, **kwargs)
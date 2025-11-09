from functools import wraps
from typing import List
from fastapi import HTTPException, status

from app.models import User
from app.models.enums import UserRole


def require_roles(required_roles: List[UserRole]):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user: User = kwargs.get("current_user")
            if not user or user.role not in required_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to access this resource."
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
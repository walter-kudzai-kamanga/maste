from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
from datetime import datetime

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_token
from app.models.user import User
from app.models.enums import UserRole
from app.services.auth_service import AuthService


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check token expiration
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_username(username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_active_agent(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Get current active agent user."""
    if current_user.role != UserRole.AGENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions - agent role required"
        )
    return current_user


async def get_current_active_teller(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Get current active teller user."""
    if current_user.role != UserRole.TELLER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions - teller role required"
        )
    return current_user


async def get_current_active_staff(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Get current active bank staff user (teller, supervisor, admin)."""
    if current_user.role not in [UserRole.TELLER, UserRole.SUPERVISOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions - bank staff role required"
        )
    return current_user


async def get_current_active_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Get current active admin user."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions - admin role required"
        )
    return current_user


class RateLimiter:
    """Simple rate limiter using Redis."""
    
    def __init__(self, times: int = 10, seconds: int = 60):
        self.times = times
        self.seconds = seconds
    
    async def __call__(self, request, current_user: User = Depends(get_current_active_user)):
        # This is a placeholder - in production you'd implement Redis-based rate limiting
        # For now, we'll just return the user
        return current_user
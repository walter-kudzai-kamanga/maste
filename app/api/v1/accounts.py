from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.account import Account
from app.models.enums import UserRole
from app.core.permissions import require_roles

router = APIRouter()

@router.get("/")
async def get_accounts(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of accounts for the current user"""
    if current_user.role == UserRole.CUSTOMER:
        accounts = db.query(Account).filter(Account.user_id == current_user.id).offset(skip).limit(limit).all()
    else:
        # Bank staff can see all accounts
        accounts = db.query(Account).offset(skip).limit(limit).all()
    
    return {"accounts": accounts, "total": len(accounts)}

@router.get("/{account_id}")
async def get_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific account details"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Check if user has access to this account
    if current_user.role == UserRole.CUSTOMER and account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this account")
    
    return account

@router.post("/")
async def create_account(
    account_type: str,
    initial_balance: float = 0.0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new account"""
    # Only bank staff can create accounts for customers
    if current_user.role == UserRole.CUSTOMER:
        raise HTTPException(status_code=403, detail="Not authorized to create accounts")
    
    # In a real implementation, you would validate the account type
    # and create the account with proper account number generation
    
    new_account = Account(
        user_id=current_user.id,  # This should be the customer ID, not the current user
        account_type=account_type,
        balance=initial_balance,
        status="active"
    )
    
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    
    return new_account

@router.put("/{account_id}/status")
async def update_account_status(
    account_id: int,
    status: str,
    current_user: User = Depends(get_current_user),
    _: bool = Depends(require_roles([UserRole.ADMIN, UserRole.BANK_STAFF])),
    db: Session = Depends(get_db)
):
    """Update account status (admin/bank staff only)"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account.status = status
    db.commit()
    db.refresh(account)
    
    return account

@router.get("/{account_id}/balance")
async def get_account_balance(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get account balance"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Check if user has access to this account
    if current_user.role == UserRole.CUSTOMER and account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this account")
    
    return {"account_id": account_id, "balance": account.balance}
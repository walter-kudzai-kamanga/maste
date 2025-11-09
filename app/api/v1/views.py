from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.account_service import AccountService
from uuid import UUID
import random
import string

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@router.get("/accounts", response_class=HTMLResponse)
async def accounts(request: Request, db: AsyncSession = Depends(get_db)):
    account_service = AccountService(db)
    accounts = await account_service.get_accounts(limit=50)
    
    # Get account statistics
    total_accounts = await account_service.get_account_count()
    active_accounts = await account_service.get_account_count(status="ACTIVE")
    
    return templates.TemplateResponse("accounts.html", {
        "request": request,
        "accounts": accounts,
        "total_accounts": total_accounts,
        "active_accounts": active_accounts
    })

@router.get("/accounts/create", response_class=HTMLResponse)
async def create_account_form(request: Request):
    # Generate account number
    account_number = ''.join(random.choices(string.digits, k=9))
    return templates.TemplateResponse("create_account.html", {
        "request": request,
        "account_number": account_number
    })

@router.get("/accounts/{account_id}/edit", response_class=HTMLResponse)
async def edit_account_form(request: Request, account_id: str, db: AsyncSession = Depends(get_db)):
    account_service = AccountService(db)
    account = await account_service.get_account_by_id(UUID(account_id))
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return templates.TemplateResponse("edit_account.html", {
        "request": request,
        "account": account
    })

# Account API endpoints
@router.post("/api/accounts/create")
async def api_create_account(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        data = await request.json()
        account_service = AccountService(db)
        
        # For demo purposes, using a fixed user ID
        # In production, this should come from the authenticated user
        from uuid import uuid4
        created_by_user_id = uuid4()
        
        # Parse the JSON data into AccountCreate schema
        from uuid import UUID
        from decimal import Decimal
        from app.models.schemas import AccountCreate
        from app.models.enums import AccountType
        
        # Handle account_type - default to CUSTOMER if not provided or invalid
        account_type = AccountType.CUSTOMER
        if 'account_type' in data:
            try:
                account_type = AccountType(data['account_type'])
            except ValueError:
                account_type = AccountType.CUSTOMER
        
        account_create_data = AccountCreate(
            account_number=data.get('account_number'),
            account_type=account_type,
            currency=data.get('currency', 'USD'),
            customer_id=UUID(data.get('customer_id')),
            initial_balance=Decimal(str(data.get('initial_balance', '0'))),
            branch_code=data.get('branch_code'),
            description=data.get('description')
        )
        
        # Create account using service
        account = await account_service.create_account(account_create_data, created_by_user_id)
        
        return JSONResponse({
            "success": True,
            "account_id": str(account.id),
            "account_number": account.account_number,
            "message": "Account created successfully"
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=400)

@router.put("/api/accounts/{account_id}/update")
async def api_update_account(request: Request, account_id: str, db: AsyncSession = Depends(get_db)):
    try:
        data = await request.json()
        account_service = AccountService(db)
        
        # Update account using service
        account = await account_service.update_account(UUID(account_id), data)
        
        if not account:
            return JSONResponse({
                "success": False,
                "error": "Account not found"
            }, status_code=404)
        
        return JSONResponse({
            "success": True,
            "message": "Account updated successfully"
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=400)

@router.delete("/api/accounts/{account_id}/delete")
async def api_delete_account(request: Request, account_id: str, db: AsyncSession = Depends(get_db)):
    try:
        account_service = AccountService(db)
        
        # For safety, we'll deactivate instead of hard delete
        account = await account_service.deactivate_account(UUID(account_id))
        
        if not account:
            return JSONResponse({
                "success": False,
                "error": "Account not found"
            }, status_code=404)
        
        return JSONResponse({
            "success": True,
            "message": "Account deactivated successfully"
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=400)

from app.services.transaction_service import TransactionService

@router.get("/transactions", response_class=HTMLResponse)
async def transactions(request: Request, db: AsyncSession = Depends(get_db)):
    transaction_service = TransactionService(db)
    transactions = await transaction_service.get_transactions(limit=50)
    return templates.TemplateResponse("transactions.html", {"request": request, "transactions": transactions})

from app.services.reconciliation_service import ReconciliationService

@router.get("/reconciliation", response_class=HTMLResponse)
async def reconciliation(request: Request, db: AsyncSession = Depends(get_db)):
    reconciliation_service = ReconciliationService(db)
    mismatched_transactions = await reconciliation_service.get_mismatched_transactions()
    return templates.TemplateResponse("reconciliation.html", {"request": request, "mismatched_transactions": mismatched_transactions})

from app.services.mobile_money_service import MobileMoneyService
from fastapi import Form

@router.get("/mobile-money", response_class=HTMLResponse)
async def mobile_money(request: Request):
    return templates.TemplateResponse("mobile-money.html", {"request": request})

@router.post("/mobile-money", response_class=HTMLResponse)
async def process_mobile_money(request: Request, recipient: str = Form(...), amount: float = Form(...)):
    mobile_money_service = MobileMoneyService()
    success = await mobile_money_service.send_money(recipient, amount)
    return templates.TemplateResponse("mobile-money.html", {"request": request, "success": success})
from fastapi import APIRouter
from app.api.v1.endpoints import users, auth, accounts, transactions, ussd

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(ussd.router, prefix="/ussd", tags=["ussd"])  # Add this line
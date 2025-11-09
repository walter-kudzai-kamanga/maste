from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1.auth import router as auth_router
from app.api.v1.accounts import router as accounts_router
from app.api.v1.payments import router as payments_router
from app.api.v1.agents import router as agents_router
from app.api.v1.reconciliation import router as reconciliation_router
from app.api.v1.mobile_money import router as mobile_money_router
from app.api.v1.monitoring import router as monitoring_router
from app.api.v1.views import router as views_router

# Create database tables (commented out for async initialization)
# Use alembic migrations or init_db() function instead

app = FastAPI(
    title="Banking System API",
    description="A comprehensive banking system with payment processing, agent management, and reconciliation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include API routes
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(accounts_router, prefix="/api/v1/accounts", tags=["accounts"])
app.include_router(payments_router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(agents_router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(
    reconciliation_router, prefix="/api/v1/reconciliation", tags=["reconciliation"]
)
app.include_router(
    mobile_money_router, prefix="/api/v1/mobile_money", tags=["mobile_money"]
)
app.include_router(
    monitoring_router, prefix="/api/v1/monitoring", tags=["monitoring"]
)
app.include_router(views_router, tags=["views"])


@app.get("/ledger", response_class=HTMLResponse)
async def read_ledger(request: Request):
    # In a real application, you would fetch ledger entries from the database
    ledger_entries = [
        # Mock data for now
    ]
    return templates.TemplateResponse("ledger.html", {"request": request, "ledger_entries": ledger_entries})


# Dashboard endpoint is handled by views router

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "banking-api",
        "version": "1.0.0"
    }

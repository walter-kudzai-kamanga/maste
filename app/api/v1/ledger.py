from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.ledger_service import get_ledger_entries
from app.schemas.ledger import LedgerEntry

router = APIRouter()

@router.get("/", response_model=list[LedgerEntry])
def read_ledger_entries(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    ledger_entries = get_ledger_entries(db, skip=skip, limit=limit)
    return ledger_entries
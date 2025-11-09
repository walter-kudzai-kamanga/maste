from sqlalchemy.orm import Session
from app.models.ledger import LedgerEntry

def get_ledger_entries(db: Session, skip: int = 0, limit: int = 100):
    return db.query(LedgerEntry).offset(skip).limit(limit).all()
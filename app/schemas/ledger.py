from pydantic import BaseModel
from datetime import datetime

class LedgerEntry(BaseModel):
    entry_id: int
    account_id: int
    amount: float
    balance_after: float
    entry_type: str
    trace_id: str
    created_at: datetime

    class Config:
        orm_mode = True
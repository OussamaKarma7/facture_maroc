from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
from app.models.accounting import AccountType

class AccountBase(BaseModel):
    code: str
    name: str
    type: AccountType

class AccountResponse(AccountBase):
    id: int
    company_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class LedgerAccountResponse(AccountResponse):
    total_debit: float
    total_credit: float
    balance: float

class JournalEntryLineResponse(BaseModel):
    id: int
    account_id: int
    debit: float
    credit: float
    account: AccountResponse
    
    class Config:
        from_attributes = True

class JournalEntryResponse(BaseModel):
    id: int
    reference: Optional[str] = None
    date: date
    description: Optional[str] = None
    lines: List[JournalEntryLineResponse]
    
    class Config:
        from_attributes = True

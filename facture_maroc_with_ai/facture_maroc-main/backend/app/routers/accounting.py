from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.models.identity import User
from app.schemas.accounting import AccountResponse, JournalEntryResponse, LedgerAccountResponse
from app.services.accounting import get_accounts, get_journal_entries, get_general_ledger
from app.utils.security import get_current_user, get_current_company_id

router = APIRouter()

@router.get("/accounts", response_model=List[AccountResponse])
async def read_accounts(
    db: AsyncSession = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user)
):
    return await get_accounts(db, company_id)

@router.get("/journal", response_model=List[JournalEntryResponse])
async def read_journal_entries(
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user)
):
    return await get_journal_entries(db, company_id, skip, limit)

@router.get("/ledger", response_model=List[LedgerAccountResponse])
async def read_general_ledger(
    db: AsyncSession = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user)
):
    return await get_general_ledger(db, company_id)

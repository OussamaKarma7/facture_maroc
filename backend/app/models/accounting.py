import enum
from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, Enum, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base

class AccountType(str, enum.Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    code = Column(String, nullable=False) # e.g. "5141" for Banque
    name = Column(String, nullable=False)
    type = Column(Enum(AccountType), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    account_class = Column(String, nullable=True)

class JournalEntry(Base):
    __tablename__ = "journal_entries"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    reference = Column(String) # E.g., invoice number or payment receipt
    date = Column(Date, nullable=False)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lines = relationship("JournalEntryLine", back_populates="journal_entry", cascade="all, delete-orphan")

class JournalEntryLine(Base):
    __tablename__ = "journal_entry_lines"
    id = Column(Integer, primary_key=True, index=True)
    journal_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    debit = Column(Float, default=0.0)
    credit = Column(Float, default=0.0)

    journal_entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("Account")

class BankAccount(Base):
    __tablename__ = "bank_accounts"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=False)
    rib = Column(String) # Relevé d'Identité Bancaire (Moroccan standard)
    balance = Column(Float, default=0.0)

class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    id = Column(Integer, primary_key=True, index=True)
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=False)
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False) # Positive for incoming, negative for outgoing
    description = Column(String)

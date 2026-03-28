from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sql_func
from fastapi import HTTPException, status
from typing import List
from datetime import datetime

from app.models.billing import Invoice, InvoiceItem, InvoiceStatus, Payment, SupplierBill, SupplierBillItem, SupplierBillStatus, InvoiceType, Quote, QuoteItem, QuoteStatus
from app.schemas.billing import InvoiceCreate, PaymentCreate, SupplierBillCreate
from app.services.accounting import generate_accounting_entries_for_invoice, generate_accounting_entries_for_payment, generate_accounting_entries_for_supplier_bill

async def generate_invoice_number(db: AsyncSession, company_id: int) -> str:
    current_year = datetime.now().year
    
    # Get max invoice number for this year to increment
    # A simple approach: count invoices for company this year
    result = await db.execute(
        select(sql_func.count(Invoice.id))
        .where(Invoice.company_id == company_id)
        .where(sql_func.extract('year', Invoice.date) == current_year)
    )
    count = result.scalar() or 0
    next_number = count + 1
    
    return f"FAC-{current_year}-{next_number:04d}"

async def create_invoice(db: AsyncSession, obj_in: InvoiceCreate, company_id: int) -> Invoice:
    # Calculate totals
    total_excl_tax = 0.0
    vat_amount = 0.0
    
    for item in obj_in.items:
        line_total_excl = item.quantity * item.unit_price
        line_vat = line_total_excl * (item.vat_rate / 100.0)
        total_excl_tax += line_total_excl
        vat_amount += line_vat
        
    total_incl_tax = total_excl_tax + vat_amount
    
    # Generate number
    invoice_number = await generate_invoice_number(db, company_id)
    
    # Create Invoice
    db_invoice = Invoice(
        company_id=company_id,
        client_id=obj_in.client_id,
        number=invoice_number,
        date=obj_in.date,
        due_date=obj_in.due_date,
        total_excl_tax=total_excl_tax,
        vat_amount=vat_amount,
        total_incl_tax=total_incl_tax,
        status=InvoiceStatus.SENT
    )
    db.add(db_invoice)
    await db.flush()
    await db.refresh(db_invoice)
    
    # Create Items
    for item in obj_in.items:
        db_item = InvoiceItem(
            invoice_id=db_invoice.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            vat_rate=item.vat_rate
        )
        db.add(db_item)
        
    await db.commit()
    await db.refresh(db_invoice)
    
    # Trigger accounting automation
    await generate_accounting_entries_for_invoice(db, db_invoice)
    
    # Reload with relationships
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.items), selectinload(Invoice.client))
        .where(Invoice.id == db_invoice.id)
    )
    return result.scalars().first()

async def get_invoices(db: AsyncSession, company_id: int, skip: int = 0, limit: int = 100) -> List[Invoice]:
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.items), selectinload(Invoice.client))
        .where(Invoice.company_id == company_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def get_invoice(db: AsyncSession, invoice_id: int, company_id: int) -> Invoice:
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.items), selectinload(Invoice.client))
        .where(Invoice.id == invoice_id, Invoice.company_id == company_id)
    )
    invoice = result.scalars().first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice

async def register_payment(db: AsyncSession, obj_in: PaymentCreate, company_id: int) -> Payment:
    # 1. Verify Invoice exists
    invoice = await get_invoice(db, obj_in.invoice_id, company_id)
    
    # 2. Create Payment
    db_payment = Payment(
        company_id=company_id,
        invoice_id=invoice.id,
        date=obj_in.date,
        amount=obj_in.amount,
        method=obj_in.method
    )
    db.add(db_payment)
    
    # 3. Update Invoice Status
    # Basic logic: assume paid in full if payment exists for MVP
    # In real app, calculate sum(payments) >= invoice.total_incl_tax
    invoice.status = InvoiceStatus.PAID
    
    await db.commit()
    await db.refresh(db_payment)
    
    # Trigger accounting automation
    await generate_accounting_entries_for_payment(db, db_payment)
    
    return db_payment

async def get_payments(db: AsyncSession, company_id: int, skip: int = 0, limit: int = 100) -> List[Payment]:
    result = await db.execute(select(Payment).where(Payment.company_id == company_id).order_by(Payment.date.desc()).offset(skip).limit(limit))
    return result.scalars().all()

async def generate_supplier_bill_number(db: AsyncSession, company_id: int) -> str:
    current_year = datetime.now().year
    result = await db.execute(
        select(sql_func.count(SupplierBill.id))
        .where(SupplierBill.company_id == company_id)
        .where(sql_func.extract('year', SupplierBill.date) == current_year)
    )
    count = result.scalar() or 0
    next_number = count + 1
    return f"DEP-{current_year}-{next_number:04d}"

async def create_supplier_bill(db: AsyncSession, obj_in: SupplierBillCreate, company_id: int) -> SupplierBill:
    total_excl_tax = 0.0
    vat_amount = 0.0
    for item in obj_in.items:
        line_total_excl = item.quantity * item.unit_price
        line_vat = line_total_excl * (item.vat_rate / 100.0)
        total_excl_tax += line_total_excl
        vat_amount += line_vat
    total_incl_tax = total_excl_tax + vat_amount
    
    bill_number = await generate_supplier_bill_number(db, company_id)
    
    db_bill = SupplierBill(
        company_id=company_id,
        supplier_id=obj_in.supplier_id,
        number=bill_number,
        date=obj_in.date,
        total_excl_tax=total_excl_tax,
        vat_amount=vat_amount,
        total_incl_tax=total_incl_tax,
        status=SupplierBillStatus.DRAFT
    )
    db.add(db_bill)
    await db.flush()
    
    for item in obj_in.items:
        db_item = SupplierBillItem(
            bill_id=db_bill.id,
            product_name=item.product_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            vat_rate=item.vat_rate
        )
        db.add(db_item)
        
    await db.commit()
    await db.refresh(db_bill)
    
    # Trigger accounting automation
    await generate_accounting_entries_for_supplier_bill(db, db_bill)
    
    return db_bill

async def get_supplier_bills(db: AsyncSession, company_id: int, skip: int = 0, limit: int = 100) -> List[SupplierBill]:
    result = await db.execute(select(SupplierBill).where(SupplierBill.company_id == company_id).order_by(SupplierBill.date.desc()).offset(skip).limit(limit))
    return result.scalars().all()

async def get_supplier_bill(db: AsyncSession, bill_id: int, company_id: int) -> SupplierBill:
    result = await db.execute(select(SupplierBill).where(SupplierBill.id == bill_id, SupplierBill.company_id == company_id))
    bill = result.scalars().first()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier bill not found")
    return bill

from sqlalchemy.orm import selectinload

async def generate_credit_note(db: AsyncSession, invoice_id: int, company_id: int) -> Invoice:
    # Get original invoice and its items
    result = await db.execute(
        select(Invoice).options(selectinload(Invoice.items))
        .where(Invoice.id == invoice_id, Invoice.company_id == company_id)
    )
    original_invoice = result.scalars().first()
    
    if not original_invoice:
        raise HTTPException(status_code=404, detail="Facture introuvable")
        
    if original_invoice.status not in [InvoiceStatus.SENT, InvoiceStatus.PAID, InvoiceStatus.OVERDUE]:
        raise HTTPException(status_code=400, detail="Seules les factures finalisées peuvent faire l'objet d'un avoir")
        
    if original_invoice.type == InvoiceType.CREDIT_NOTE:
        raise HTTPException(status_code=400, detail="Impossible de faire un avoir sur un avoir")
        
    # Mark original as cancelled
    original_invoice.status = InvoiceStatus.CANCELLED
    
    current_year = datetime.now().year
    count_result = await db.execute(
        select(sql_func.count(Invoice.id))
        .where(Invoice.company_id == company_id)
        .where(Invoice.type == InvoiceType.CREDIT_NOTE)
        .where(sql_func.extract('year', Invoice.date) == current_year)
    )
    count = count_result.scalar() or 0
    next_number = count + 1
    avoir_number = f"AVO-{current_year}-{next_number:04d}"
    
    avoir = Invoice(
        company_id=company_id,
        client_id=original_invoice.client_id,
        number=avoir_number,
        date=datetime.now().date(),
        type=InvoiceType.CREDIT_NOTE,
        parent_id=original_invoice.id,
        status=InvoiceStatus.SENT,
        total_excl_tax=-original_invoice.total_excl_tax,
        vat_amount=-original_invoice.vat_amount,
        total_incl_tax=-original_invoice.total_incl_tax
    )
    db.add(avoir)
    await db.flush()
    
    for item in original_invoice.items:
        db_item = InvoiceItem(
            invoice_id=avoir.id,
            product_id=item.product_id,
            quantity=-item.quantity,
            unit_price=item.unit_price,
            vat_rate=item.vat_rate
        )
        db.add(db_item)
        
    await db.commit()
    await db.refresh(avoir)
    
    # Re-apply accounting rules (will generate negative entries which zero out correctly)
    await generate_accounting_entries_for_invoice(db, avoir)
    
    stmt = select(Invoice).options(selectinload(Invoice.items)).where(Invoice.id == avoir.id)
    res = await db.execute(stmt)
    return res.scalars().first()

# --- Quotes Services ---

async def create_quote(db: AsyncSession, quote_in, company_id: int) -> Quote:
    # Generate number
    current_year = datetime.now().year
    count_query = await db.execute(select(sql_func.count(Quote.id)).where(Quote.company_id == company_id, sql_func.extract('year', Quote.date) == current_year))
    quote_count = count_query.scalar() or 0
    quote_number = f"DEV-{current_year}-{quote_count + 1:04d}"

    db_quote = Quote(
        company_id=company_id,
        client_id=quote_in.client_id,
        number=quote_number,
        date=quote_in.date,
        valid_until=quote_in.valid_until,
        status=QuoteStatus.DRAFT,
        total_excl_tax=0.0,
        vat_amount=0.0,
        total_incl_tax=0.0
    )
    db.add(db_quote)
    await db.flush() # get id

    total_excl = 0.0
    total_vat = 0.0

    for item_in in quote_in.items:
        line_total_excl = item_in.quantity * item_in.unit_price
        line_vat = line_total_excl * (item_in.vat_rate / 100.0)
        
        db_item = QuoteItem(
            quote_id=db_quote.id,
            product_id=item_in.product_id,
            quantity=item_in.quantity,
            unit_price=item_in.unit_price,
            vat_rate=item_in.vat_rate
        )
        db.add(db_item)

        total_excl += line_total_excl
        total_vat += line_vat

    db_quote.total_excl_tax = total_excl
    db_quote.vat_amount = total_vat
    db_quote.total_incl_tax = total_excl + total_vat

    await db.commit()
    await db.refresh(db_quote)

    result = await db.execute(select(Quote).options(selectinload(Quote.items)).where(Quote.id == db_quote.id))
    return result.scalar_one()

async def get_quotes(db: AsyncSession, company_id: int, skip: int = 0, limit: int = 100) -> List[Quote]:
    result = await db.execute(
        select(Quote)
        .options(selectinload(Quote.items))
        .where(Quote.company_id == company_id)
        .order_by(Quote.date.desc(), Quote.id.desc())
        .offset(skip).limit(limit)
    )
    return result.scalars().all()

async def get_quote(db: AsyncSession, quote_id: int, company_id: int) -> Quote:
    result = await db.execute(
        select(Quote)
        .options(selectinload(Quote.items))
        .where(Quote.id == quote_id, Quote.company_id == company_id)
    )
    res = result.scalar_one_or_none()
    if not res:
         raise HTTPException(status_code=404, detail="Quote not found")
    return res

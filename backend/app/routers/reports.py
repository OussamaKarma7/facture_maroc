from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import APIRouter, Depends
from datetime import datetime, date, timedelta

from app.database import get_db
from app.models.identity import User
from app.models.billing import Invoice, InvoiceStatus, Payment, SupplierBill, SupplierBillStatus
from app.schemas.reports import DashboardResponse, DashboardKPis, ChartDataPoint, VatReportResponse
from app.utils.security import get_current_user, get_current_company_id

router = APIRouter()

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard_data(
    db: AsyncSession = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user)
):
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    # 1. Monthly Revenue (Payments received this month)
    revenue_query = await db.execute(
        select(func.sum(Payment.amount)).where(
            Payment.company_id == company_id,
            func.extract('month', Payment.date) == current_month,
            func.extract('year', Payment.date) == current_year
        )
    )
    monthly_revenue = revenue_query.scalar() or 0.0

    # 2. Unpaid Invoices
    unpaid_query = await db.execute(
        select(
            func.count(Invoice.id).label('count'),
            func.sum(Invoice.total_incl_tax).label('total')
        ).where(
            Invoice.company_id == company_id,
            Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.OVERDUE])
        )
    )
    unpaid_res = unpaid_query.first()
    unpaid_count = unpaid_res.count or 0
    unpaid_total = unpaid_res.total or 0.0

    # 3. Expenses (From Supplier Bills)
    expense_query = await db.execute(
        select(func.sum(SupplierBill.total_incl_tax)).where(
             SupplierBill.company_id == company_id,
             func.extract('month', SupplierBill.date) == current_month,
             func.extract('year', SupplierBill.date) == current_year,
             SupplierBill.status != SupplierBillStatus.CANCELLED
        )
    )
    total_expenses = expense_query.scalar() or 0.0

    # 4. VAT Due (Collected VAT from paid invoices this month)
    # Strictly in Morocco, VAT is often on encaissement (payments) or facturation
    # We will approximate this by VAT portion of payments for MVP
    vat_query = await db.execute(
        select(func.sum(Invoice.vat_amount)).where(
            Invoice.company_id == company_id,
            Invoice.status == InvoiceStatus.PAID,
            func.extract('month', Invoice.date) == current_month
        )
    )
    vat_due = vat_query.scalar() or 0.0

    # 5. Charts (Last 6 months dynamic)
    revenue_history_query = await db.execute(
        select(
            func.extract('year', Payment.date).label('year'),
            func.extract('month', Payment.date).label('month'),
            func.sum(Payment.amount).label('total')
        ).where(
            Payment.company_id == company_id,
            Payment.date >= (datetime.now().date() - timedelta(days=180))
        )
        .group_by('year', 'month')
    )
    revenue_history = {(int(row.year), int(row.month)): float(row.total or 0) for row in revenue_history_query.all()}

    expense_history_query = await db.execute(
        select(
            func.extract('year', SupplierBill.date).label('year'),
            func.extract('month', SupplierBill.date).label('month'),
            func.sum(SupplierBill.total_incl_tax).label('total')
        ).where(
            SupplierBill.company_id == company_id,
            SupplierBill.status != SupplierBillStatus.CANCELLED,
            SupplierBill.date >= (datetime.now().date() - timedelta(days=180))
        )
        .group_by('year', 'month')
    )
    expense_history = {(int(row.year), int(row.month)): float(row.total or 0) for row in expense_history_query.all()}

    fr_months = {
        1: "Jan", 2: "Fév", 3: "Mar", 4: "Avr", 5: "Mai", 6: "Juin",
        7: "Juil", 8: "Aoû", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Déc"
    }

    revenue_chart = []
    expense_chart = []
    
    for i in range(5, -1, -1):
        y = current_year
        m = current_month - i
        if m <= 0:
            m += 12
            y -= 1
        
        label = f"{fr_months[m]}"
        revenue_chart.append(ChartDataPoint(label=label, value=revenue_history.get((y, m), 0.0)))
        expense_chart.append(ChartDataPoint(label=label, value=expense_history.get((y, m), 0.0)))

    return DashboardResponse(
        kpis=DashboardKPis(
            monthly_revenue=monthly_revenue,
            unpaid_invoices_count=unpaid_count,
            unpaid_invoices_total=unpaid_total,
            total_expenses=total_expenses,
            vat_due=vat_due
        ),
        revenue_chart=revenue_chart,
        expense_chart=expense_chart
    )

@router.get("/taxes", response_model=VatReportResponse)
async def get_vat_report(
    db: AsyncSession = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user)
):
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    # Collected VAT (from paid invoices in the period)
    vat_collected_query = await db.execute(
        select(func.sum(Invoice.vat_amount)).where(
            Invoice.company_id == company_id,
            Invoice.status == InvoiceStatus.PAID,
            func.extract('month', Invoice.date) == current_month,
            func.extract('year', Invoice.date) == current_year
        )
    )
    collected_vat = vat_collected_query.scalar() or 0.0

    # Deductible VAT (from supplier bills in the period)
    vat_deductible_query = await db.execute(
        select(func.sum(SupplierBill.vat_amount)).where(
             SupplierBill.company_id == company_id,
             func.extract('month', SupplierBill.date) == current_month,
             func.extract('year', SupplierBill.date) == current_year,
             SupplierBill.status != SupplierBillStatus.CANCELLED
        )
    )
    deductible_vat = vat_deductible_query.scalar() or 0.0
    
    net_vat_due = collected_vat - deductible_vat

    return VatReportResponse(
        period=f"{current_month:02d}/{current_year}",
        collected_vat=collected_vat,
        deductible_vat=deductible_vat,
        net_vat_due=net_vat_due
    )

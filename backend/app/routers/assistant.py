from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List, Optional
import httpx
from app.database import get_db
from app.config import settings
from app.models.billing import Invoice, InvoiceItem, InvoiceStatus, Payment
from app.models.crm import Client
from app.utils.security import get_current_user, get_current_company_id
from app.models.identity import User

router = APIRouter()

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

async def get_company_context(db: AsyncSession, company_id: int) -> str:
    from app.models.billing import SupplierBill, SupplierBillStatus, Quote
    from app.models.accounting import Account, JournalEntryLine
    from app.models.catalog import Product
    from sqlalchemy.orm import selectinload

    # Factures par statut
    inv_status = await db.execute(
        select(Invoice.status, func.count(Invoice.id), func.sum(Invoice.total_incl_tax))
        .where(Invoice.company_id == company_id, Invoice.type == "STANDARD")
        .group_by(Invoice.status)
    )
    status_data = {}
    for row in inv_status.all():
        status_data[row[0].value] = {"count": row[1], "total": float(row[2] or 0)}

    sent = status_data.get("SENT", {"count": 0, "total": 0})
    paid = status_data.get("PAID", {"count": 0, "total": 0})
    cancelled = status_data.get("CANCELLED", {"count": 0, "total": 0})

    # Clients
    clients_result = await db.execute(
        select(Client).where(Client.company_id == company_id).limit(20)
    )
    clients = clients_result.scalars().all()
    clients_list = "\n".join([f"  - {c.name} | ICE: {c.ice or 'N/A'} | Ville: {c.city or 'N/A'}" for c in clients])

    # Devis
    quotes_result = await db.execute(
        select(Quote.status, func.count(Quote.id), func.sum(Quote.total_incl_tax))
        .where(Quote.company_id == company_id)
        .group_by(Quote.status)
    )
    quotes_data = {}
    for row in quotes_result.all():
        quotes_data[row[0].value] = {"count": row[1], "total": float(row[2] or 0)}

    # Achats fournisseurs
    bills_result = await db.execute(
        select(SupplierBill.status, func.count(SupplierBill.id), func.sum(SupplierBill.total_incl_tax))
        .where(SupplierBill.company_id == company_id)
        .group_by(SupplierBill.status)
    )
    bills_data = {}
    for row in bills_result.all():
        bills_data[row[0].value] = {"count": row[1], "total": float(row[2] or 0)}

    # TVA
    vat_collected = await db.execute(
        select(func.sum(Invoice.vat_amount))
        .where(Invoice.company_id == company_id, Invoice.status == InvoiceStatus.PAID)
    )
    collected = float(vat_collected.scalar() or 0)

    vat_deductible = await db.execute(
        select(func.sum(SupplierBill.vat_amount))
        .where(SupplierBill.company_id == company_id, SupplierBill.status != SupplierBillStatus.CANCELLED)
    )
    deductible = float(vat_deductible.scalar() or 0)
    net_vat = collected - deductible

    # Grand livre
    ledger_result = await db.execute(
        select(Account.code, Account.name,
               func.coalesce(func.sum(JournalEntryLine.debit), 0).label("debit"),
               func.coalesce(func.sum(JournalEntryLine.credit), 0).label("credit"))
        .outerjoin(JournalEntryLine, Account.id == JournalEntryLine.account_id)
        .where(Account.company_id == company_id)
        .group_by(Account.id)
        .order_by(Account.code)
    )
    ledger = ledger_result.all()
    ledger_list = "\n".join([
        f"  - Compte {row.code} ({row.name}): Debit {float(row.debit):.2f} | Credit {float(row.credit):.2f} | Solde {float(row.debit) - float(row.credit):.2f} MAD"
        for row in ledger
    ])

    # Produits catalogue
    products_result = await db.execute(
        select(Product).where(Product.company_id == company_id).limit(20)
    )
    products = products_result.scalars().all()
    products_list = "\n".join([f"  - ID:{p.id} | {p.name} | Prix: {p.price:.2f} MAD | TVA: {p.vat_rate}%" for p in products])

    # Detail articles par facture (20 dernieres avec items)
    invoices_with_items = await db.execute(
        select(Invoice, Client.name)
        .join(Client, Invoice.client_id == Client.id)
        .where(Invoice.company_id == company_id)
        .order_by(Invoice.id.desc())
        .limit(20)
    )
    invoices_list = invoices_with_items.all()

    # Charger les items separement
    invoice_ids = [inv.id for inv, _ in invoices_list]
    items_result = await db.execute(
        select(InvoiceItem, Product.name.label("product_name"))
        .outerjoin(Product, InvoiceItem.product_id == Product.id)
        .where(InvoiceItem.invoice_id.in_(invoice_ids))
    )
    items_by_invoice = {}
    for item, product_name in items_result.all():
        if item.invoice_id not in items_by_invoice:
            items_by_invoice[item.invoice_id] = []
        name = product_name if product_name else (item.description if item.description else f"Article sans nom")
        items_by_invoice[item.invoice_id].append(f"{item.quantity}x {name} a {item.unit_price:.2f} MAD HT (TVA {item.vat_rate}%)")

    status_map = {"SENT": "Envoyee", "PAID": "Payee", "CANCELLED": "Annulee", "OVERDUE": "En retard", "DRAFT": "Brouillon"}
    invoices_detail = []
    for inv, client_name in invoices_list:
        items_str = " | ".join(items_by_invoice.get(inv.id, ["Aucun article"]))
        invoices_detail.append(
            f"  - {inv.number} | {client_name} | {inv.total_incl_tax:.2f} MAD | {status_map.get(inv.status.value, inv.status.value)} | Articles: [{items_str}]"
        )
    invoices_detail_str = "\n".join(invoices_detail)

    return f"""
=== DONNEES COMPTABLES EN TEMPS REEL ===

FACTURES:
- Envoyees (impayees): {sent['count']} pour {sent['total']:.2f} MAD
- Payees: {paid['count']} pour {paid['total']:.2f} MAD
- Annulees: {cancelled['count']}

DETAIL 20 DERNIERES FACTURES AVEC ARTICLES:
{invoices_detail_str}

DEVIS:
- Brouillons: {quotes_data.get('DRAFT', {}).get('count', 0)}
- Envoyes: {quotes_data.get('SENT', {}).get('count', 0)}
- Acceptes: {quotes_data.get('ACCEPTED', {}).get('count', 0)}
- Rejetes: {quotes_data.get('REJECTED', {}).get('count', 0)}

ACHATS FOURNISSEURS:
- En cours: {bills_data.get('DRAFT', {}).get('count', 0)} pour {bills_data.get('DRAFT', {}).get('total', 0):.2f} MAD
- Payes: {bills_data.get('PAID', {}).get('count', 0)} pour {bills_data.get('PAID', {}).get('total', 0):.2f} MAD

CLIENTS ({len(clients)} au total):
{clients_list}

PRODUITS CATALOGUE ({len(products)} au total):
{products_list}

FISCALITE (TVA):
- TVA collectee sur factures payees: {collected:.2f} MAD
- TVA deductible sur achats: {deductible:.2f} MAD
- TVA nette a payer: {net_vat:.2f} MAD

GRAND LIVRE COMPTABLE:
{ledger_list}
"""

@router.post("/assistant/chat")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user)
):
    context = await get_company_context(db, company_id)

    system_prompt = f"""Tu es un assistant comptable intelligent pour une PME marocaine utilisant ComptaSaaS.
Tu aides le gestionnaire a comprendre ses donnees financieres, suivre ses factures et clients.
Tu reponds toujours en francais, de facon concise et professionnelle.
Tu utilises les donnees reelles de l'entreprise pour repondre aux questions.

{context}

Tu peux repondre aux questions sur:
- Le chiffre d'affaires et les revenus
- Les factures impayees et leur suivi
- Les clients et leur historique
- La TVA et les obligations fiscales
- Les conseils comptables generaux pour les PME marocaines
"""

    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "system", "content": system_prompt}] + messages,
                "max_tokens": 1024,
                "temperature": 0.7
            },
            timeout=30.0
        )
        data = response.json()
        reply = data["choices"][0]["message"]["content"]

    return {"reply": reply}

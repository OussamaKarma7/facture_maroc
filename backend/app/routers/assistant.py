from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List, Optional
import httpx
from app.database import get_db
from app.config import settings
from app.models.billing import Invoice, InvoiceStatus, Payment
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
    # Nombre de factures
    inv_count = await db.execute(select(func.count(Invoice.id)).where(Invoice.company_id == company_id))
    total_invoices = inv_count.scalar() or 0

    # Factures impayées
    unpaid = await db.execute(
        select(func.count(Invoice.id), func.sum(Invoice.total_incl_tax))
        .where(Invoice.company_id == company_id, Invoice.status == InvoiceStatus.SENT)
    )
    unpaid_row = unpaid.first()
    unpaid_count = unpaid_row[0] or 0
    unpaid_total = unpaid_row[1] or 0.0

    # Factures payées
    paid = await db.execute(
        select(func.count(Invoice.id), func.sum(Invoice.total_incl_tax))
        .where(Invoice.company_id == company_id, Invoice.status == InvoiceStatus.PAID)
    )
    paid_row = paid.first()
    paid_count = paid_row[0] or 0
    paid_total = paid_row[1] or 0.0

    # Nombre de clients
    clients_count = await db.execute(select(func.count(Client.id)).where(Client.company_id == company_id))
    total_clients = clients_count.scalar() or 0

    # Dernières factures
    recent_invoices = await db.execute(
        select(Invoice, Client.name)
        .join(Client, Invoice.client_id == Client.id)
        .where(Invoice.company_id == company_id)
        .order_by(Invoice.id.desc())
        .limit(5)
    )
    recent = recent_invoices.all()
    recent_list = "\n".join([f"  - {inv.number} | {name} | {inv.total_incl_tax} MAD | {inv.status}" for inv, name in recent])

    return f"""
Donnees comptables actuelles de l'entreprise:
- Total factures: {total_invoices}
- Factures impayees (SENT): {unpaid_count} pour un total de {unpaid_total:.2f} MAD
- Factures payees: {paid_count} pour un total de {paid_total:.2f} MAD
- Nombre de clients: {total_clients}

Dernieres factures:
{recent_list}
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

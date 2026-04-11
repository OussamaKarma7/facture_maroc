from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.config import settings
from app.models.billing import Invoice, InvoiceItem, InvoiceStatus, Payment, SupplierBill, SupplierBillStatus, Quote
from app.models.crm import Client
from app.models.catalog import Product

client_ai = AsyncOpenAI(
    api_key=settings.GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

async def get_company_context(db: AsyncSession, company_id: int) -> str:
    try:
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
            select(Client).where(Client.company_id == company_id).limit(30)
        )
        clients = clients_result.scalars().all()
        clients_list = "\n".join([
            f"  - {c.name} | ICE: {c.ice or 'N/A'} | Ville: {c.city or 'N/A'} | Email: {c.email or 'N/A'}"
            for c in clients
        ])

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

        # Produits catalogue
        products_result = await db.execute(
            select(Product).where(Product.company_id == company_id).limit(30)
        )
        products = products_result.scalars().all()
        products_list = "\n".join([
            f"  - {p.name} | Prix: {p.price:.2f} MAD | TVA: {p.vat_rate}%"
            for p in products
        ])

        # 20 dernieres factures avec articles
        invoices_result = await db.execute(
            select(Invoice, Client.name)
            .join(Client, Invoice.client_id == Client.id)
            .where(Invoice.company_id == company_id)
            .order_by(Invoice.id.desc())
            .limit(20)
        )
        invoices_list = invoices_result.all()
        invoice_ids = [inv.id for inv, _ in invoices_list]

        items_by_invoice = {}
        if invoice_ids:
            items_result = await db.execute(
                select(InvoiceItem, Product.name.label("product_name"))
                .outerjoin(Product, InvoiceItem.product_id == Product.id)
                .where(InvoiceItem.invoice_id.in_(invoice_ids))
            )
            for item, product_name in items_result.all():
                if item.invoice_id not in items_by_invoice:
                    items_by_invoice[item.invoice_id] = []
                name = product_name or getattr(item, 'description', None) or "Article"
                items_by_invoice[item.invoice_id].append(
                    f"{item.quantity}x {name} a {item.unit_price:.2f} MAD HT (TVA {item.vat_rate}%)"
                )

        status_map = {
            "SENT": "Envoyee", "PAID": "Payee", "CANCELLED": "Annulee",
            "OVERDUE": "En retard", "DRAFT": "Brouillon"
        }
        invoices_detail = []
        for inv, client_name in invoices_list:
            items_str = " | ".join(items_by_invoice.get(inv.id, ["Aucun article"]))
            invoices_detail.append(
                f"  - {inv.number} | {client_name} | {inv.total_incl_tax:.2f} MAD | "
                f"{status_map.get(inv.status.value, inv.status.value)} | Articles: [{items_str}]"
            )

        # Paiements recents
        payments_result = await db.execute(
            select(Payment).where(Payment.company_id == company_id)
            .order_by(Payment.id.desc()).limit(10)
        )
        payments = payments_result.scalars().all()
        payments_list = "\n".join([
            f"  - Paiement #{p.id} | Facture #{p.invoice_id} | {p.amount:.2f} MAD | {p.method.value} | {p.date}"
            for p in payments
        ])

        return f"""
=== DONNEES COMPTABLES EN TEMPS REEL DE L'ENTREPRISE ===

RESUME FACTURES:
- Envoyees (impayees): {sent['count']} factures pour {sent['total']:.2f} MAD
- Payees: {paid['count']} factures pour {paid['total']:.2f} MAD
- Annulees: {cancelled['count']} factures

DETAIL 20 DERNIERES FACTURES AVEC ARTICLES:
{chr(10).join(invoices_detail) if invoices_detail else "Aucune facture"}

DEVIS:
- Brouillons: {quotes_data.get('DRAFT', {}).get('count', 0)}
- Envoyes: {quotes_data.get('SENT', {}).get('count', 0)}
- Acceptes: {quotes_data.get('ACCEPTED', {}).get('count', 0)}
- Rejetes: {quotes_data.get('REJECTED', {}).get('count', 0)}

ACHATS FOURNISSEURS:
- En attente: {bills_data.get('DRAFT', {}).get('count', 0)} pour {bills_data.get('DRAFT', {}).get('total', 0):.2f} MAD
- Payes: {bills_data.get('PAID', {}).get('count', 0)} pour {bills_data.get('PAID', {}).get('total', 0):.2f} MAD

PAIEMENTS RECENTS:
{payments_list if payments_list else "Aucun paiement"}

CLIENTS ({len(clients)} au total):
{clients_list if clients_list else "Aucun client"}

PRODUITS CATALOGUE ({len(products)} au total):
{products_list if products_list else "Aucun produit"}

FISCALITE TVA (Loi marocaine - regime encaissement):
- TVA collectee (sur factures payees): {collected:.2f} MAD
- TVA deductible (sur achats fournisseurs): {deductible:.2f} MAD
- TVA nette a declarer et payer au Tresor: {net_vat:.2f} MAD
- Echeance: avant le 20 du mois suivant (article 111 CGI Maroc)
"""
    except Exception as e:
        print(f"Erreur get_company_context: {e}")
        return "Donnees temporairement non disponibles."


async def get_ai_response(company_id: int, user_id: int, message: str, db: AsyncSession = None) -> str:
    try:
        context = ""
        if db:
            context = await get_company_context(db, company_id)

        system_prompt = f"""Tu es un assistant comptable expert pour les PME marocaines utilisant ComptaSaaS.
Tu as acces en temps reel aux donnees financieres de l'entreprise.
Tu reponds TOUJOURS en francais, de facon claire, concise et professionnelle.
Tu bases tes reponses uniquement sur les donnees reelles ci-dessous.

{context}

REGLES COMPTABLES MAROCAINES QUE TU CONNAIS:
- PCM (Plan Comptable Marocain): classes 1 a 7
- TVA: taux 20% (standard), 14% (transport), 10% (hotellerie), 7% (eau/electricite)
- Regime encaissement: TVA due quand le paiement est recu
- IS (Impot sur Societes): 10% jusqu 300k MAD, 20% de 300k a 1M MAD, 31% au dela
- Cotisation minimale: 0.5% du CA HT (minimum 1500 MAD)
- Declaration TVA: avant le 20 du mois suivant (mensuelle) ou trimestrielle si CA < 1M MAD
- Exercice fiscal: generalement du 1er janvier au 31 decembre

Tu peux repondre sur:
- Factures, devis, paiements, clients, produits
- Comptabilite, TVA, IS, fiscalite marocaine
- Analyses financieres et conseils pour PME
- Procedures et obligations legales au Maroc
"""

        response = await client_ai.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=1024,
            temperature=0.7
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"Erreur get_ai_response: {e}")
        return f"Erreur de connexion a l'IA: {str(e)}"

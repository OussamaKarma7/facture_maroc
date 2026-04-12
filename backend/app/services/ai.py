"""
services/ai.py — Service IA enrichi avec accès Bilan, PCM, Grand Livre, GED
À copier dans backend/app/services/ai.py
"""
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.config import settings
from app.models.billing import Invoice, InvoiceItem, InvoiceStatus, Payment, SupplierBill, SupplierBillStatus, Quote
from app.models.crm import Client
from app.models.catalog import Product
from app.models.accounting import Account, JournalEntry, JournalEntryLine, AccountType
from app.models.system import Document, TaxReport

client_ai = AsyncOpenAI(
    api_key=settings.GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)


async def get_pcm_context(db: AsyncSession, company_id: int) -> str:
    """Plan Comptable Marocain — tous les comptes groupés par classe"""
    result = await db.execute(
        select(Account).where(Account.company_id == company_id).order_by(Account.code)
    )
    accounts = result.scalars().all()
    if not accounts:
        return "PLAN COMPTABLE: Aucun compte configuré."

    classes: dict[str, list] = {}
    for a in accounts:
        cls = a.code[0] if a.code else "?"
        classes.setdefault(cls, []).append(a)

    lines = ["=== PLAN COMPTABLE MAROCAIN (PCM) ==="]
    class_names = {
        "1": "Financement permanent", "2": "Actif immobilisé",
        "3": "Actif circulant", "4": "Passif circulant",
        "5": "Trésorerie", "6": "Charges", "7": "Produits",
    }
    for cls in sorted(classes.keys()):
        label = class_names.get(cls, "Autre")
        lines.append(f"\nClasse {cls} — {label} ({len(classes[cls])} comptes):")
        for a in classes[cls]:
            lines.append(f"  {a.code} | {a.name} | {a.type.value}")
    return "\n".join(lines)


async def get_journal_entries_context(db: AsyncSession, company_id: int) -> str:
    """Dernières écritures comptables avec lignes détaillées"""
    result = await db.execute(
        select(JournalEntry)
        .where(JournalEntry.company_id == company_id)
        .order_by(JournalEntry.date.desc())
        .limit(30)
    )
    entries = result.scalars().all()
    if not entries:
        return "ÉCRITURES COMPTABLES: Aucune écriture enregistrée."

    lines = ["=== ÉCRITURES COMPTABLES (30 dernières) ==="]
    for entry in entries:
        lines.append(f"\n  #{entry.id} | {entry.date} | {entry.description or 'N/A'} | Réf: {entry.reference or 'N/A'}")
        # Charger les lignes
        lines_result = await db.execute(
            select(JournalEntryLine, Account)
            .join(Account, JournalEntryLine.account_id == Account.id)
            .where(JournalEntryLine.journal_entry_id == entry.id)
        )
        for line, account in lines_result.all():
            lines.append(
                f"    {account.code} {account.name}: "
                f"Débit={line.debit:,.2f} Crédit={line.credit:,.2f}"
            )
    return "\n".join(lines)


async def get_ledger_context(db: AsyncSession, company_id: int) -> str:
    """Grand Livre — totaux débit/crédit/solde par compte"""
    result = await db.execute(
        select(
            Account.code,
            Account.name,
            Account.type,
            func.coalesce(func.sum(JournalEntryLine.debit), 0).label("total_debit"),
            func.coalesce(func.sum(JournalEntryLine.credit), 0).label("total_credit"),
        )
        .outerjoin(JournalEntryLine, JournalEntryLine.account_id == Account.id)
        .outerjoin(JournalEntry, JournalEntryLine.journal_entry_id == JournalEntry.id)
        .where(Account.company_id == company_id)
        .group_by(Account.code, Account.name, Account.type)
        .order_by(Account.code)
    )
    rows = result.all()
    lines = ["=== GRAND LIVRE ==="]
    for code, name, acc_type, td, tc in rows:
        solde = td - tc
        if td > 0 or tc > 0:
            lines.append(f"  {code} {name} ({acc_type.value}): D={td:,.2f} C={tc:,.2f} Solde={solde:,.2f} MAD")
    return "\n".join(lines) if len(lines) > 1 else "GRAND LIVRE: Aucun mouvement."


async def get_balance_bilan_context(db: AsyncSession, company_id: int) -> str:
    """Balance générale + Bilan + CPC calculés"""
    result = await db.execute(
        select(
            Account.code, Account.name, Account.type,
            func.coalesce(func.sum(JournalEntryLine.debit), 0).label("td"),
            func.coalesce(func.sum(JournalEntryLine.credit), 0).label("tc"),
        )
        .outerjoin(JournalEntryLine, JournalEntryLine.account_id == Account.id)
        .outerjoin(JournalEntry, JournalEntryLine.journal_entry_id == JournalEntry.id)
        .where(Account.company_id == company_id)
        .group_by(Account.code, Account.name, Account.type)
        .order_by(Account.code)
    )
    rows = result.all()

    total_mvt_d = total_mvt_c = 0
    total_sd = total_sc = 0
    actif = passif = capitaux = charges = produits = 0.0

    balance_lines = ["=== BALANCE GÉNÉRALE ==="]
    for code, name, acc_type, td, tc in rows:
        total_mvt_d += td
        total_mvt_c += tc
        sd = max(td - tc, 0)
        sc = max(tc - td, 0)
        total_sd += sd
        total_sc += sc
        balance_lines.append(f"  {code} {name}: MvtD={td:,.2f} MvtC={tc:,.2f} SD={sd:,.2f} SC={sc:,.2f}")

        solde = td - tc
        if acc_type == AccountType.ASSET:
            actif += solde
        elif acc_type == AccountType.LIABILITY:
            passif += abs(solde)
        elif acc_type == AccountType.EQUITY:
            capitaux += abs(solde)
        elif acc_type == AccountType.EXPENSE:
            charges += solde
        elif acc_type == AccountType.REVENUE:
            produits += abs(solde)

    balance_lines.append(f"TOTAUX: MvtD={total_mvt_d:,.2f} MvtC={total_mvt_c:,.2f} SD={total_sd:,.2f} SC={total_sc:,.2f}")

    resultat = produits - charges

    bilan = f"""
=== BILAN ===
ACTIF:
  Total Actifs: {actif:,.2f} MAD
PASSIF:
  Capitaux propres: {capitaux:,.2f} MAD
  Dettes: {passif:,.2f} MAD
RÉSULTAT NET: {resultat:,.2f} MAD

=== CPC (Compte de Produits et Charges) ===
  Total Produits: {produits:,.2f} MAD
  Total Charges: {charges:,.2f} MAD
  Résultat d'exploitation: {resultat:,.2f} MAD
"""
    return "\n".join(balance_lines) + bilan


async def get_ged_context(db: AsyncSession, company_id: int) -> str:
    """GED — liste des documents archivés"""
    result = await db.execute(
        select(Document)
        .where(Document.company_id == company_id)
        .order_by(Document.created_at.desc())
        .limit(50)
    )
    docs = result.scalars().all()
    if not docs:
        return "GED: Aucun document archivé."

    lines = ["=== GED - DOCUMENTS ARCHIVÉS ==="]
    for d in docs:
        lines.append(f"  {d.name} | Type: {d.file_type or 'N/A'} | Date: {d.created_at}")
    return "\n".join(lines)


async def get_company_context(db: AsyncSession, company_id: int) -> str:
    """Contexte complet : Facturation + Comptabilité + GED"""
    try:
        # ---- Facturation existante ----
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

        clients_result = await db.execute(
            select(func.count(Client.id)).where(Client.company_id == company_id)
        )
        nb_clients = clients_result.scalar() or 0

        products_result = await db.execute(
            select(func.count(Product.id)).where(Product.company_id == company_id)
        )
        nb_products = products_result.scalar() or 0

        # TVA
        vat_collected = float((await db.execute(
            select(func.sum(Invoice.vat_amount))
            .where(Invoice.company_id == company_id, Invoice.status == InvoiceStatus.PAID)
        )).scalar() or 0)

        vat_deductible = float((await db.execute(
            select(func.sum(SupplierBill.vat_amount))
            .where(SupplierBill.company_id == company_id, SupplierBill.status != SupplierBillStatus.CANCELLED)
        )).scalar() or 0)

        billing_ctx = f"""
=== FACTURATION ===
Factures impayées: {sent['count']} pour {sent['total']:,.2f} MAD
Factures payées: {paid['count']} pour {paid['total']:,.2f} MAD
Clients: {nb_clients} | Produits: {nb_products}

TVA:
  Collectée: {vat_collected:,.2f} MAD
  Déductible: {vat_deductible:,.2f} MAD
  Nette à payer: {vat_collected - vat_deductible:,.2f} MAD
"""

        # ---- Nouvelles sections ----
        pcm_ctx = await get_pcm_context(db, company_id)
        entries_ctx = await get_journal_entries_context(db, company_id)
        ledger_ctx = await get_ledger_context(db, company_id)
        balance_bilan_ctx = await get_balance_bilan_context(db, company_id)
        ged_ctx = await get_ged_context(db, company_id)

        return f"{billing_ctx}\n{pcm_ctx}\n\n{entries_ctx}\n\n{ledger_ctx}\n\n{balance_bilan_ctx}\n\n{ged_ctx}"

    except Exception as e:
        print(f"Erreur get_company_context: {e}")
        return "Données temporairement non disponibles."


async def get_ai_response(company_id: int, user_id: int, message: str, db: AsyncSession = None) -> str:
    try:
        context = ""
        if db:
            context = await get_company_context(db, company_id)

        system_prompt = f"""Tu es un assistant comptable expert pour les PME marocaines utilisant FactureMaroc.
Tu as accès en temps réel à TOUTES les données financières :
- Plan Comptable (PCM classes 1-7)
- Écritures comptables (tous les journaux)
- Grand Livre (soldes par compte)
- Balance Générale (mouvements et soldes)
- Bilan et CPC (états financiers)
- GED (documents archivés : factures, contrats, bulletins)
- Facturation (factures, devis, paiements, clients, produits)

Tu réponds TOUJOURS en français, de façon claire et professionnelle.

{context}

RÈGLES COMPTABLES MAROCAINES:
- PCM: classes 1 (financement permanent) à 7 (produits)
- TVA: 20% (standard), 14% (transport), 10% (hôtellerie), 7% (eau/électricité)
- Régime encaissement: TVA due quand le paiement est reçu
- IS: 10% ≤300k, 20% 300k-1M, 31% >1M MAD
- Cotisation minimale: 0,5% du CA HT (min 1500 MAD)
- Déclaration TVA: avant le 20 du mois suivant
"""

        response = await client_ai.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=1500,
            temperature=0.7
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"Erreur get_ai_response: {e}")
        return f"Erreur de connexion à l'IA: {str(e)}"
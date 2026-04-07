# backend/app/services/ai_tools.py
# backend/app/services/ai_tools.py
"""
Tools disponibles pour l'Assistant IA Grok
Version simplifiée pour démarrage rapide
"""

from typing import Any, Dict, List

async def list_invoices(db, company_id: int, status: str = None):
    """Récupérer la liste des factures"""
    from app.services.billing import get_invoices
    return await get_invoices(db, company_id=company_id, status=status)

async def list_clients(db, company_id: int):
    """Récupérer la liste des clients"""
    from app.services.crm import get_clients
    return await get_clients(db, company_id=company_id)

async def get_vat_report(db, company_id: int):
    """Récupérer le rapport de TVA"""
    from app.services.reports import get_vat_report   # si le service existe
    # Pour l'instant on retourne un message si le service n'existe pas encore
    return {"message": "Rapport TVA en cours de développement"}

def get_all_tools(company_id: int, user_id: int):
    """Retourne la liste des tools pour Grok"""
    return [
        {
            "name": "list_invoices",
            "description": "Liste toutes les factures de l'entreprise. Utile quand l'utilisateur demande ses factures ou son CA.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["DRAFT", "SENT", "PAID", "OVERDUE", "CANCELLED"]}
                },
                "required": []
            },
            "func": list_invoices
        },
        {
            "name": "list_clients",
            "description": "Liste tous les clients de l'entreprise.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            },
            "func": list_clients
        }
    ]
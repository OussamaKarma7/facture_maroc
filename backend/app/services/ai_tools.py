import json
# Importe ici tes fonctions de base de données (ex: get_invoices, get_clients...)

def get_all_tools(company_id: int, user_id: int):
    """
    Retourne la liste des outils. 
    Chaque dictionnaire DOIT avoir 'type' ET 'function'.
    """
    return [
        {
            "type": "function",  # <--- DOIT ÊTRE ICI
            "function": {
                "name": "get_invoice_stats",
                "description": "Récupère les statistiques des factures de l'entreprise.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["PAID", "SENT", "DRAFT"],
                            "description": "Filtrer par statut"
                        }
                    },
                    "required": []
                }
            }
        }
    ]

async def call_tool_function(function_name: str, company_id: int, **kwargs):
    # Ton code de dispatcher ici...
    return {"status": "success"}
async def call_tool_function(function_name: str, company_id: int, **kwargs):
    """L'aiguilleur qui exécute la vraie logique Python"""
    
    if function_name == "get_invoice_stats":
        # Ici, tu appelles ta vraie fonction de base de données
        # Exemple factice :
        return {
            "total_amount": "45.000 DH",
            "status": kwargs.get("status", "tous"),
            "count": 12
        }
    
    # Ajoute d'autres elif pour chaque nouvel outil
    
    return {"error": "Fonction non trouvée"}
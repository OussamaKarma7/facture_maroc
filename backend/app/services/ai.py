# backend/app/services/ai.py
from xai_sdk import Client
from xai_sdk.chat import user, system
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from app.config import settings
from app.services.ai_tools import get_all_tools  # On va créer ce fichier juste après

client = Client(api_key=settings.GROK_API_KEY)

async def get_ai_response(
    company_id: int,
    user_id: int,
    message: str,
    history: List[Dict[str, str]] = None
) -> str:
    """
    Fonction principale qui appelle Grok avec tous les tools de l'application
    """
    if history is None:
        history = []

    try:
        # Créer une nouvelle conversation avec les tools
        chat = client.chat.create(
            model=settings.GROK_MODEL,   # ex: "grok-4" ou "grok-4.20-reasoning"
            tools=get_all_tools(company_id, user_id)
        )

        # System prompt (très important)
        system_prompt = f"""Tu es un assistant comptable IA professionnel spécialisé dans la gestion d'entreprises au Maroc.
Tu as accès en temps réel à toutes les données de l'entreprise (factures, devis, clients, fournisseurs, produits, comptabilité, TVA, etc.).
Tu dois toujours répondre en français, de manière claire, professionnelle et conforme à la législation marocaine (ICE, IF, TVA 20%, 14%, 10%, 7%, etc.).
Utilise les tools disponibles lorsque c'est nécessaire pour donner des réponses précises.
Ne jamais inventer d'informations."""

        chat.append(system(system_prompt))

        # Ajouter l'historique de conversation
        for msg in history:
            if msg.get("role") == "user":
                chat.append(user(msg["content"]))
            else:
                chat.append(system(msg["content"]))

        # Ajouter le message actuel
        chat.append(user(message))

        # Exécuter la conversation (Grok gère le tool calling automatiquement)
        response_text = ""
        for chunk in chat.stream():
            if chunk.content:
                response_text += chunk.content

        return response_text.strip()

    except Exception as e:
        print(f"Erreur Grok AI: {e}")
        return "Désolé, j'ai rencontré une erreur technique. Pouvez-vous reformuler votre question ?"
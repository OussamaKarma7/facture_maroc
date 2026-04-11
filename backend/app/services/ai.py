from openai import AsyncOpenAI
from app.config import settings

# Configuration standard compatible x.ai
client = AsyncOpenAI(
    api_key=settings.GROK_API_KEY,
    base_url="https://api.x.ai/v1",
)

async def get_ai_response(company_id: int, user_id: int, message: str):
    try:
        # Utilise le modèle configuré dans app.config
        response = await client.chat.completions.create(
            model=settings.GROK_MODEL,
            messages=[
                {"role": "system", "content": "Tu es un assistant comptable expert au Maroc."},
                {"role": "user", "content": message}
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"❌ ERREUR CRITIQUE : {str(e)}")
        if "Model not found" in str(e):
            return (
                f"Erreur de connexion à l'IA : modèle configuré invalide '{settings.GROK_MODEL}'. "
                "Vérifie la valeur GROK_MODEL dans backend/app/config.py ou dans ton fichier .env."
            )
        return f"Erreur de connexion à l'IA : {str(e)}"
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.ai import get_ai_response
from app.utils.security import get_current_user
from app.models.identity import User

router = APIRouter(prefix="/ai", tags=["Assistant IA"])

@router.post("/chat")
async def chat_with_grok(message: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # On récupère la réponse de l'IA (en passant company_id et user_id pour les tools)
    response = await get_ai_response(
        company_id=current_user.company_id,
        user_id=current_user.id,
        message=message
    )
    return {"reply": response}

# Route pour déclencher manuellement la vérification Gmail
@router.post("/gmail/check")
async def trigger_gmail_check(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.services.gmail import check_new_emails_and_reply
    await check_new_emails_and_reply(db, current_user.company_id, current_user.id)
    return {"status": "Vérification Gmail lancée"}
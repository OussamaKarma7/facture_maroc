from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.gmail import check_new_emails_and_reply
from app.database import AsyncSessionLocal

# Import Routers - ASSURE-TOI QUE CES FICHIERS EXISTENT DANS app/routers/
from app.routers import auth, crm, catalog, billing, reports, accounting, ai, settings as site_settings, documents

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(crm.router, prefix="/api", tags=["crm"])
app.include_router(catalog.router, prefix="/api", tags=["catalog"])
app.include_router(billing.router, prefix="/api", tags=["billing"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(accounting.router, prefix="/api/accounting", tags=["accounting"])
app.include_router(site_settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])

# ON GARDE UN SEUL ROUTER POUR L'IA (Vérifie bien que app/routers/ai.py existe)
app.include_router(ai.router, prefix="/api", tags=["ai"])  

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scheduled_gmail_check, 'interval', minutes=10, id='gmail_check')
    scheduler.start()
    
    print("✅ Application démarrée")
    print("✅ Scheduler Gmail activé")

async def scheduled_gmail_check():
    async with AsyncSessionLocal() as db:
        try:
            await check_new_emails_and_reply(db, company_id=1, user_id=1)
        except Exception as e:
            print(f"Erreur scheduler Gmail: {e}")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Moroccan Accounting SaaS API"}

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.models.base import Base
from app.database import engine, Base

# Import Routers
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
app.include_router(ai.router, prefix="/api", tags=["assistant-ia"])






@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        # Create all tables on startup (replace with Alembic in production)
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Moroccan Accounting SaaS API"}


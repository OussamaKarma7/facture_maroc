from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Moroccan Accounting SaaS"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/accounting_saas"
    SECRET_KEY: str = "supersecretkey-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    GROK_API_KEY: str = "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"   # ← Mets ta clé Grok ici
    GROK_MODEL: str = "grok-4"   # ou "grok-4.20-reasoning" si disponible

    class Config:
        env_file = ".env"

settings = Settings()

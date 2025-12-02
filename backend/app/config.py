# backend/app/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENV: str = "development"
    DEBUG: bool = True

    OPENAI_API_KEY: str
    EMBED_MODEL: str = "text-embedding-3-large"
    LLM_MODEL: str = "gpt-4.1-mini"

    BACKEND_BASE_URL: str = "http://localhost:8000"


    # FIXED: lowercase name to match settings.database_url
    database_url: str = (
        "postgresql://mycertiq_user:mycertiq_dev@localhost:5432/mycertiq_demo"
    )

    PROJECT_NAME: str = "MyCertiQ Demo"

    class Config:
        env_file = ".env"

settings = Settings()

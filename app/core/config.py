import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"

class Settings(BaseSettings):
    PROJECT_NAME: str = "CraftAI Studio Backend"
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    
    SUPABASE_URL: str = "https://your-project.supabase.co"
    SUPABASE_SERVICE_ROLE_KEY: str = "your-service-role-key"
    SUPABASE_ANON_KEY: str = "your-anon-key"
    
    # LLM Multi-Provider Gateway & Configurable Models
    DEFAULT_LLM_PROVIDER: str = "gemini"
    LLM_PROVIDER: str = "gemini"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GROQ_MODEL: str = "qwen/qwen3.8-27b"
    LLM_MODEL_NAME: str = "qwen/qwen3.8-27b"
    OPENAI_MODEL: str = "gpt-4o-mini"
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"
    
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-chat"
    HF_TOKEN: str = ""

    AES_SECRET_KEY: str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = str(ENV_FILE) if ENV_FILE.exists() else ".env"
        extra = "ignore"

settings = Settings()

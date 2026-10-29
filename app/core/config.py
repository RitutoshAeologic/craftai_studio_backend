import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    LLM_MODEL_NAME: str = "llama-3.3-70b-versatile"
    OPENAI_MODEL: str = "gpt-4o-mini"
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"
    
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    HF_TOKEN: str = ""
    POLLINATIONS_API_KEY: str = ""

    # Diffusion Engine (Local MPS / Sidecar Worker / Cloud Gateway)
    LOCAL_DIFFUSION_ENABLED: bool = True
    DIFFUSION_BACKEND: str = "auto"  # "auto", "sidecar", "local", "huggingface", "pollinations"
    DIFFUSION_SIDECAR_URL: str = "http://127.0.0.1:8001"
    LOCAL_SDXL_BASE_MODEL: str = "SG161222/RealVisXL_V4.0"
    LOCAL_SDXL_LORA_REPO: str = "ByteDance/SDXL-Lightning"
    LOCAL_SDXL_LORA_WEIGHT: str = "sdxl_lightning_4step_lora.safetensors"
    LOCAL_SDXL_STEPS: int = 4
    LOCAL_SDXL_GUIDANCE: float = 0.0

    AES_SECRET_KEY: str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else ".env",
        extra="ignore"
    )

settings = Settings()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="CraftAI Studio — FastAPI & Supabase Compute Gateway"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "database": "Supabase PostgreSQL"
    }

@app.get("/api/v1/meta")
def api_metadata():
    return {
        "platform": "CraftAI Studio",
        "models_supported": ["flux_schnell", "sdxl", "instantid", "liveportrait"],
        "download_policy": "Flat 2 Credits Idempotent",
        "signed_url_ttl_seconds": 900
    }

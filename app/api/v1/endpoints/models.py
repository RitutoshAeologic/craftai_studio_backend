from fastapi import APIRouter, Query, Depends
from typing import Optional
from app.services.config_service import ConfigService
from app.core.auth import get_current_user

router = APIRouter(prefix="/models", tags=["AI Models"])


@router.get("")
async def list_available_models(task: Optional[str] = Query(None, description="Filter by task: text_to_image, image_edit, face_lock_remix")):
    """
    Returns active AI models from Supabase `ai_models` enriched with live key availability.
    Web & Mobile use this endpoint to dynamically unlock paid models as soon as keys are
    added in Supabase Dashboard (zero redeploy).
    """
    models = ConfigService.get_ai_models()
    if task:
        t = task.strip().lower()
        models = [m for m in models if t in [x.lower() for x in (m.get("tasks") or [])]]
    return {
        "models": models,
        "count": len(models),
    }


@router.post("/refresh")
async def refresh_model_cache(current_user: dict = Depends(get_current_user)):
    """
    Authenticated dev convenience: clears cache on the current worker process.
    In multi-worker production (`uvicorn --workers N`), all workers sync automatically within 60s via TTL.
    """
    ConfigService.refresh_cache()
    models = ConfigService.get_ai_models(force_refresh=True)
    return {
        "status": "refreshed",
        "count": len(models),
    }


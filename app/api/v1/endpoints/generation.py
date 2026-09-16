import asyncio
from fastapi import APIRouter, Depends, WebSocket, BackgroundTasks
from app.api.deps import get_generation_service
from app.services.generation_service import GenerationService
from app.schemas.generation import GenerationDispatchRequest, GenerationDispatchResponse, GenerationStatusResponse
from app.services.privacy_service import PrivacyService
from app.core.auth import get_current_user
from app.services.config_service import ConfigService
from app.core.logging import logger

router = APIRouter(tags=["Generation & Progress"])

@router.post("/generation/dispatch", response_model=GenerationDispatchResponse)
async def dispatch_generation(
    req: GenerationDispatchRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    service: GenerationService = Depends(get_generation_service)
):
    """Tier 0 vs Tier 1 dispatcher with Zero-Retention Ephemeral Privacy Auto-Purge & Dual Auth."""
    res = await service.dispatch(req, user_id=current_user.get("user_id"))

    # Privacy Auto-Purge: Ephemeral reference photos are purged after processing (giving safe window)
    if req.face_reference_urls and len(req.face_reference_urls) > 0:
        background_tasks.add_task(PrivacyService.purge_reference_images, req.face_reference_urls, 30)

    # Royalty Hook (Controlled via remote settings; disabled by default during dev)
    if req.remixed_from_prompt_id and ConfigService.is_royalty_enabled():
        logger.info(f"[Royalty] User {current_user.get('user_id')} remixed prompt {req.remixed_from_prompt_id}")

    return res

@router.get("/status/{task_id}", response_model=GenerationStatusResponse)
async def get_generation_status(
    task_id: str,
    service: GenerationService = Depends(get_generation_service)
):
    """HTTP polling fallback for generation status recovery on mobile disconnects."""
    return service.get_status(task_id)

@router.websocket("/ws/generation/{task_id}")
async def generation_progress_ws(
    websocket: WebSocket,
    task_id: str,
    service: GenerationService = Depends(get_generation_service)
):
    """Realtime WebSocket streaming generation step milestones."""
    await websocket.accept()
    phases = service.get_websocket_phases(task_id)
    is_tier1 = any("identity" in p.get("message", "").lower() or "gemini" in p.get("message", "").lower() for p in phases)

    try:
        for phase in phases:
            await websocket.send_json(phase)
            await asyncio.sleep(0.5 if not is_tier1 else 0.9)
    except Exception:
        pass
    finally:
        await websocket.close()

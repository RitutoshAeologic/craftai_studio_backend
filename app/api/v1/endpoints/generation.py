import asyncio
from fastapi import APIRouter, Depends, WebSocket, BackgroundTasks
from app.api.deps import get_generation_service
from app.services.generation_service import GenerationService
from app.schemas.generation import GenerationDispatchRequest, GenerationDispatchResponse, GenerationStatusResponse
from app.services.privacy_service import PrivacyService
from app.core.auth import get_current_user
from app.services.config_service import ConfigService
from app.core.supabase_client import get_supabase_admin
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

    # Royalty Hook: Automatically credit original creator when an artwork is remixed
    if req.remixed_from_prompt_id:
        buyer_id = current_user.get("user_id")
        try:
            admin = get_supabase_admin()
            orig = admin.table("explore_prompts").select("id, author_id, user_id, title, author_royalty_cut").eq("id", req.remixed_from_prompt_id).maybe_single().execute()
            if orig.data:
                creator_id = orig.data.get("author_id") or orig.data.get("user_id")
                royalty_cut = float(orig.data.get("author_royalty_cut") or 1.60)
                if creator_id and creator_id != buyer_id:
                    admin.rpc("increment_creator_royalty", {
                        "p_creator_id": creator_id,
                        "p_amount": royalty_cut,
                        "p_prompt_id": req.remixed_from_prompt_id,
                        "p_buyer_id": buyer_id
                    }).execute()
                    admin.rpc("increment_prompt_remix_count", {
                        "p_prompt_id": req.remixed_from_prompt_id
                    }).execute()
                    logger.info(f"[Royalty ✅] Credited {royalty_cut} Cr to creator {creator_id} for remixed prompt {req.remixed_from_prompt_id}")
        except Exception as e:
            logger.error(f"[Royalty ⚠️] Failed to process creator royalty: {e}")

    return res

@router.get("/status/{task_id}", response_model=GenerationStatusResponse)
@router.get("/generation/status/{task_id}", response_model=GenerationStatusResponse)
async def get_generation_status(
    task_id: str,
    service: GenerationService = Depends(get_generation_service)
):
    """HTTP polling fallback for generation status recovery on mobile disconnects."""
    return service.get_status(task_id)

@router.websocket("/ws/generation/{task_id}")
@router.websocket("/generation/ws/generation/{task_id}")
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

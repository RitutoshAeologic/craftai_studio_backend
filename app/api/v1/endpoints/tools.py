from typing import Optional, List, Dict, Any
from fastapi import Query
from fastapi import APIRouter, Depends
from app.api.deps import get_tool_service
from app.services.tool_service import ToolService
from app.schemas.tools import (
    ToolPresetRequest, ToolPresetResponse,
    RemoveBackgroundRequest, RemoveBackgroundResponse,
    AiBackgroundRequest, AiBackgroundResponse,
    AiExpandRequest, AiExpandResponse,
    UpscaleRequest, UpscaleResponse,
    ProductDetailRequest, ProductDetailResponse,
    MarketingPosterRequest, MarketingPosterResponse
)

router = APIRouter(tags=["MeiGen AI Skills"])

# ── Skill 1: Remove Background ────────────────────────────────────────────────
@router.post("/tools/remove-background", response_model=RemoveBackgroundResponse)
async def tool_remove_background(
    req: RemoveBackgroundRequest,
    service: ToolService = Depends(get_tool_service)
):
    """Skill 1: 1-tap transparent PNG cutout (Zero GPU, Free CPU rembg)."""
    return await service.remove_background(req)

# ── Skill 2: AI Backgrounds ───────────────────────────────────────────────────
@router.post("/tools/ai-background", response_model=AiBackgroundResponse)
async def tool_ai_background(
    req: AiBackgroundRequest,
    service: ToolService = Depends(get_tool_service)
):
    """Skill 2: Pure white studio canvas (0 tokens) or Smart / Custom contextual backdrop."""
    return await service.generate_ai_background(req)

# ── Skill 3: AI Expand ────────────────────────────────────────────────────────
@router.post("/tools/ai-expand", response_model=AiExpandResponse)
async def tool_ai_expand(
    req: AiExpandRequest,
    service: ToolService = Depends(get_tool_service)
):
    """Skill 3: Generative canvas outpaint extension to any aspect ratio."""
    return await service.execute_ai_expand(req)

# ── Skill 4: Upscale 4K ───────────────────────────────────────────────────────
@router.post("/tools/upscale", response_model=UpscaleResponse)
async def tool_upscale(
    req: UpscaleRequest,
    service: ToolService = Depends(get_tool_service)
):
    """Skill 4: 2X/4K super-resolution detail enhancement."""
    return await service.upscale_image(req)

# ── Skill 5: Product Detail Images ───────────────────────────────────────────
@router.post("/tools/product-detail", response_model=ProductDetailResponse)
async def tool_product_detail(
    req: ProductDetailRequest,
    service: ToolService = Depends(get_tool_service)
):
    """Skill 5: 1 photo to full e-commerce product feature listing set."""
    return await service.execute_product_detail(req)

# ── Skill 6: Marketing Poster ────────────────────────────────────────────────
@router.post("/tools/marketing-poster", response_model=MarketingPosterResponse)
async def tool_marketing_poster(
    req: MarketingPosterRequest,
    service: ToolService = Depends(get_tool_service)
):
    """Skill 6: Promos · Events · Commercial Posters — one line in."""
    return await service.generate_marketing_poster(req)

# ── Legacy Preset Transforms ─────────────────────────────────────────────────
@router.post("/tools/edit-preset", response_model=ToolPresetResponse)
async def tool_edit_preset(
    req: ToolPresetRequest,
    service: ToolService = Depends(get_tool_service)
):
    """Zero-token optical lighting, bokeh, or sharpening preset on CPU."""
    return await service.execute_preset_tool(req)


# ── Tool Generation History ──────────────────────────────────────────────────
@router.get("/tools/history")
async def get_tool_history(
    user_id: str = Query(..., description="User UUID to fetch history for"),
    tool_type: Optional[str] = Query(None, description="Optional tool_type filter"),
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
    service: ToolService = Depends(get_tool_service)
):
    """Fetches dedicated tool execution history from tool_generations table."""
    return await service.get_tool_history(user_id=user_id, tool_type=tool_type, limit=limit)

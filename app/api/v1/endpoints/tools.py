from fastapi import APIRouter, Depends, Query
from typing import Optional, List, Any
from app.api.deps import get_tool_service
from app.services.tool_service import ToolService
from app.schemas.tools import (
    ToolPresetRequest,
    ToolPresetResponse,
    RemoveBackgroundRequest,
    RemoveBackgroundResponse,
    UpscaleRequest,
    UpscaleResponse,
    AiBackgroundRequest,
    AiBackgroundResponse,
    AiExpandRequest,
    AiExpandResponse,
    ProductDetailRequest,
    ProductDetailResponse,
    MarketingPosterRequest,
    MarketingPosterResponse,
    RemoveObjectRequest,
    RemoveObjectResponse,
    ColorizeRequest,
    ColorizeResponse,
)
from app.core.supabase_client import get_supabase_admin
from app.core.logging import logger

router = APIRouter(tags=["Zero-Token Tools"])

@router.post("/tools/edit-preset", response_model=ToolPresetResponse)
async def tool_edit_preset(
    req: ToolPresetRequest,
    service: ToolService = Depends(get_tool_service)
):
    """1-Click zero-token preset tool execution with strict subject lock."""
    return await service.execute_preset_tool(req)

@router.post("/tools/remove-background", response_model=RemoveBackgroundResponse)
async def tool_remove_background(
    req: RemoveBackgroundRequest,
    service: ToolService = Depends(get_tool_service)
):
    """Zero-Token local CPU background removal (transparent PNG output, zero API cost)."""
    return await service.remove_background(req)

@router.post("/tools/upscale", response_model=UpscaleResponse)
async def tool_upscale(
    req: UpscaleRequest,
    service: ToolService = Depends(get_tool_service)
):
    """
    Sub-second Super-Resolution Detail Upscaler (2X HD / 4X Ultra 4K).
    Zero-Token, sub-second execution, preserving micro-textures & aspect ratio.
    """
    return await service.upscale_image(req)

@router.post("/tools/ai-background", response_model=AiBackgroundResponse)
async def tool_ai_background(
    req: AiBackgroundRequest,
    service: ToolService = Depends(get_tool_service)
):
    """Pure white e-commerce cutout or smart studio background synthesis."""
    return await service.execute_ai_background(req)


@router.get("/tools/ai-background/templates")
async def get_ai_background_templates():
    """Returns available AI background backdrop presets with metadata & credit costs."""
    return {
        "status": "success",
        "templates": [
            {
                "id": "pure_white",
                "title": "Pure white",
                "subtitle": "Commercial Cyclo",
                "icon": "⚪",
                "mode": "pure_white",
                "backdrop": "",
                "is_free": True,
                "credits": 0
            },
            {
                "id": "smart",
                "title": "Smart Studio",
                "subtitle": "Product Keylight",
                "icon": "🏢",
                "mode": "smart",
                "backdrop": "commercial photorealistic studio keylight",
                "is_free": False,
                "credits": 10
            },
            {
                "id": "marble",
                "title": "Luxury Marble",
                "subtitle": "Studio Pedestal",
                "icon": "🏛️",
                "mode": "marble",
                "backdrop": "luxury marble pedestal overhead soft spotlight",
                "is_free": False,
                "credits": 10
            },
            {
                "id": "wood",
                "title": "Warm Wood",
                "subtitle": "Cozy Cafe Table",
                "icon": "🪵",
                "mode": "wood",
                "backdrop": "warm wooden tabletop cafe ambient lighting",
                "is_free": False,
                "credits": 10
            },
            {
                "id": "neon",
                "title": "Cyber Neon",
                "subtitle": "Futuristic Glow",
                "icon": "🌆",
                "mode": "neon",
                "backdrop": "cyberpunk neon city illumination reflections",
                "is_free": False,
                "credits": 10
            },
            {
                "id": "custom",
                "title": "Custom Backdrop",
                "subtitle": "Write Any Prompt",
                "icon": "✍️",
                "mode": "custom",
                "backdrop": "",
                "is_free": False,
                "credits": 10
            }
        ]
    }


@router.post("/tools/ai-expand", response_model=AiExpandResponse)
async def tool_ai_expand(
    req: AiExpandRequest,
    service: ToolService = Depends(get_tool_service)
):
    """Generative canvas outpainting and aspect ratio extension."""
    return await service.execute_ai_expand(req)

@router.post("/tools/product-detail", response_model=ProductDetailResponse)
async def tool_product_detail(
    req: ProductDetailRequest,
    service: ToolService = Depends(get_tool_service)
):
    """E-commerce product isolation on luxury studio pedestal."""
    return await service.execute_product_detail(req)

@router.post("/tools/marketing-poster", response_model=MarketingPosterResponse)
async def tool_marketing_poster(
    req: MarketingPosterRequest,
    service: ToolService = Depends(get_tool_service)
):
    """Commercial marketing promotional poster layout engine."""
    return await service.generate_marketing_poster(req)


@router.post("/tools/remove-object", response_model=RemoveObjectResponse)
async def tool_remove_object(
    req: RemoveObjectRequest,
    service: ToolService = Depends(get_tool_service)
):
    """
    Magic Object Eraser (LaMa Neural Inpainting).
    Erase unwanted people, wires, text, or objects seamlessly in sub-second.
    """
    return await service.remove_object(req)

@router.post("/tools/colorize", response_model=ColorizeResponse)
async def tool_colorize(
    req: ColorizeRequest,
    service: ToolService = Depends(get_tool_service)
):
    """
    DDColor High-Fidelity Colorizer.
    Restores natural vibrant color to vintage or B&W photos, preserving 100% native resolution.
    """
    return await service.colorize_image(req)

@router.get("/tools/history")
async def tool_history(
    user_id: Optional[str] = Query(None),
    tool_type: Optional[str] = Query(None),
    limit: int = Query(20),
    offset: int = Query(0)
):
    """Retrieves tool generation history for the current user."""
    try:
        admin = get_supabase_admin()
        query = admin.from_("jobs").select("*").order("created_at", { "ascending": False }).limit(limit)
        if user_id and user_id not in ("undefined", "null", "default", "guest"):
            query = query.eq("user_id", user_id)
        res = query.execute()
        return res.data or []
    except Exception as e:
        logger.warning(f"[Tool: History] Could not load tool history: {e}")
        return []

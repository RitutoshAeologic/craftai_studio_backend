from fastapi import APIRouter, Depends
from app.api.deps import get_tool_service
from app.services.tool_service import ToolService
from app.schemas.tools import (
    ToolPresetRequest,
    ToolPresetResponse,
    RemoveBackgroundRequest,
    RemoveBackgroundResponse,
    UpscaleRequest,
    UpscaleResponse,
)

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


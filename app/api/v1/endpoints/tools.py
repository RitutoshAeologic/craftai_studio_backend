from fastapi import APIRouter, Depends
from app.api.deps import get_tool_service
from app.services.tool_service import ToolService
from app.schemas.tools import ToolPresetRequest, ToolPresetResponse, RemoveBackgroundRequest, RemoveBackgroundResponse

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

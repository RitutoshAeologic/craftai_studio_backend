import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import get_remix_service
from app.services.remix_service import RemixService
from app.core.auth import get_current_user
from app.schemas.remix import (
    CreateRemixSessionRequest,
    RemixSessionResponse,
    RemixChatRequest,
    RemixChatResponse,
    RemixSessionHistoryResponse,
)

logger = logging.getLogger("craftai.remix_endpoint")
router = APIRouter(prefix="/remix", tags=["Remix Chat Module"])

@router.post("/sessions", response_model=RemixSessionHistoryResponse)
async def create_remix_session(
    req: CreateRemixSessionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: RemixService = Depends(get_remix_service)
):
    """
    Initializes a new dedicated Remix Chat Session anchored to a reference image.
    Stores session metadata in Supabase and returns initial welcome guidance.
    """
    user_id = current_user.get("user_id")
    return await service.create_session(req, user_id=user_id)

@router.get("/sessions/{session_id}", response_model=RemixSessionHistoryResponse)
async def get_remix_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: RemixService = Depends(get_remix_service)
):
    """
    Retrieves the complete message history and anchor parameters for a remix session.
    """
    user_id = current_user.get("user_id")
    res = await service.get_session_history(session_id, user_id=user_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Remix session '{session_id}' not found."
        )
    return res

@router.post("/chat", response_model=RemixChatResponse)
async def execute_remix_chat(
    req: RemixChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: RemixService = Depends(get_remix_service)
):
    """
    Sub-second conversational prompt refinement using Groq LPU / Gemini.
    Compiles prompt delta, logs messages, and updates current prompt state.
    """
    user_id = current_user.get("user_id")
    try:
        return await service.execute_chat_turn(req, user_id=user_id)
    except Exception as e:
        logger.error(f"Error during remix chat turn: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compile remix prompt delta. Please check prompt instructions and retry."
        )

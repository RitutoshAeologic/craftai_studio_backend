from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import get_prompt_service
from app.services.prompt_service import PromptService
from app.schemas.prompt import (
    PromptExpandRequest,
    PromptExpandResponse,
    PromptDeltaRequest,
    PromptDeltaResponse,
    LLMConfigResponse
)

router = APIRouter(tags=["Prompt Engineering"])

@router.get("/config", response_model=LLMConfigResponse)
async def get_llm_config(
    service: PromptService = Depends(get_prompt_service)
):
    """Inspect active LLM configuration, available providers, model mappings, and fallback order."""
    return await service.get_active_config()

@router.post("/expand", response_model=PromptExpandResponse)
async def expand_prompt(
    req: PromptExpandRequest,
    service: PromptService = Depends(get_prompt_service)
):
    """1-Shot prompt expansion utilizing configured multi-LLM tokens and optics enrichment."""
    return await service.expand_prompt(
        raw_prompt=req.raw_prompt,
        starter_chip=req.starter_chip,
        aspect_ratio=req.aspect_ratio or "1:1",
        ai_model=req.ai_model
    )

@router.post("/chat-delta", response_model=PromptDeltaResponse)
async def compile_chat_delta(
    req: PromptDeltaRequest,
    service: PromptService = Depends(get_prompt_service)
):
    """Conversational prompt delta compilation with turn-limit enforcement."""
    if req.turn_count > 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Session free refinement limit reached. Please generate to continue."
        )
    return await service.compile_delta(
        base_prompt=req.base_prompt,
        user_instruction=req.user_instruction,
        ai_model=req.ai_model
    )

import uuid
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import get_prompt_service
from app.services.prompt_service import PromptService
from app.core.auth import get_current_user
from app.core.supabase_client import get_supabase_admin
from app.core.logging import logger
from app.schemas.remix import (
    RemixMessage,
    RemixSessionCreateRequest,
    RemixSessionResponse,
    RemixChatRequest,
    RemixChatTurnResponse
)

router = APIRouter(tags=["Remix Lab"])

# In-memory session store for high-performance sub-second turns & dev fallback
_REMIX_SESSIONS: Dict[str, Dict[str, Any]] = {}

DEFAULT_SUGGESTED_CHIPS = [
    "Increase Neon Bokeh",
    "Change to Platinum Hair",
    "Soft Studio Lighting",
    "Cinematic Rain Reflections",
    "Analog Film Grain"
]

@router.post("/remix/sessions", response_model=RemixSessionResponse)
@router.post("/sessions", response_model=RemixSessionResponse)
async def create_remix_session(
    req: RemixSessionCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Initializes a dedicated conversational Remix Lab session anchored to a reference image."""
    user_id = current_user.get("user_id")
    session_id = f"sess_remix_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    initial_prompt = req.initial_prompt or "Preserve subject with balanced aesthetics"
    welcome_msg = RemixMessage(
        id=f"msg_welcome_{uuid.uuid4().hex[:8]}",
        session_id=session_id,
        role="assistant",
        content=f"Anchored to reference artwork. How would you like to refine the prompt recipe?",
        diff_added=[],
        diff_removed=[],
        suggested_chips=DEFAULT_SUGGESTED_CHIPS,
        model_used="system",
        latency_ms=10,
        created_at=now_iso
    )

    session_data = {
        "id": session_id,
        "user_id": user_id,
        "anchor_image_url": req.anchor_image_url,
        "source_type": req.source_type,
        "remixed_from_prompt_id": req.remixed_from_prompt_id,
        "current_prompt": initial_prompt,
        "style_weight": req.style_weight,
        "turn_count": 0,
        "last_generated_job_id": None,
        "created_at": now_iso,
        "updated_at": now_iso,
        "messages": [welcome_msg]
    }

    _REMIX_SESSIONS[session_id] = session_data

    # Optional Supabase persistence if table remix_sessions exists
    try:
        admin = get_supabase_admin()
        admin.table("remix_sessions").insert({
            "id": session_id,
            "user_id": user_id,
            "anchor_image_url": req.anchor_image_url,
            "source_type": req.source_type,
            "remixed_from_prompt_id": req.remixed_from_prompt_id,
            "current_prompt": initial_prompt,
            "style_weight": req.style_weight,
            "turn_count": 0
        }).execute()
    except Exception as e:
        logger.debug(f"[Remix] Supabase session store notice: {e}")

    logger.info(f"[Remix] Created session {session_id} for user {user_id}")
    return RemixSessionResponse(**session_data)

@router.get("/remix/sessions/{session_id}", response_model=RemixSessionResponse)
@router.get("/sessions/{session_id}", response_model=RemixSessionResponse)
async def get_remix_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Fetches existing Remix Lab session with complete message turn history."""
    if session_id in _REMIX_SESSIONS:
        return RemixSessionResponse(**_REMIX_SESSIONS[session_id])

    # Try loading from Supabase
    try:
        admin = get_supabase_admin()
        res = admin.table("remix_sessions").select("*").eq("id", session_id).maybe_single().execute()
        if res.data:
            data = res.data
            now_iso = datetime.now(timezone.utc).isoformat()
            sess = {
                "id": data["id"],
                "user_id": data.get("user_id"),
                "anchor_image_url": data.get("anchor_image_url", ""),
                "source_type": data.get("source_type", "explore"),
                "remixed_from_prompt_id": data.get("remixed_from_prompt_id"),
                "current_prompt": data.get("current_prompt", ""),
                "style_weight": float(data.get("style_weight", 0.60)),
                "turn_count": int(data.get("turn_count", 0)),
                "last_generated_job_id": data.get("last_generated_job_id"),
                "created_at": data.get("created_at", now_iso),
                "updated_at": data.get("updated_at", now_iso),
                "messages": []
            }
            _REMIX_SESSIONS[session_id] = sess
            return RemixSessionResponse(**sess)
    except Exception as e:
        logger.debug(f"[Remix] Supabase session query notice: {e}")

    # Fallback default session if not found
    now_iso = datetime.now(timezone.utc).isoformat()
    fallback_session = {
        "id": session_id,
        "user_id": current_user.get("user_id"),
        "anchor_image_url": "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=600",
        "source_type": "explore",
        "remixed_from_prompt_id": None,
        "current_prompt": "Cinematic artwork, vibrant lighting, highly detailed",
        "style_weight": 0.60,
        "turn_count": 0,
        "last_generated_job_id": None,
        "created_at": now_iso,
        "updated_at": now_iso,
        "messages": []
    }
    _REMIX_SESSIONS[session_id] = fallback_session
    return RemixSessionResponse(**fallback_session)

@router.post("/remix/chat", response_model=RemixChatTurnResponse)
@router.post("/chat", response_model=RemixChatTurnResponse)
async def send_remix_chat_message(
    req: RemixChatRequest,
    current_user: dict = Depends(get_current_user),
    service: PromptService = Depends(get_prompt_service)
):
    """Conversational prompt refinement turn with multi-LLM compilation and diff tracking."""
    session_id = req.session_id
    session = _REMIX_SESSIONS.get(session_id)
    if not session:
        # Auto-create session if missing from in-memory cache
        now_iso = datetime.now(timezone.utc).isoformat()
        session = {
            "id": session_id,
            "user_id": current_user.get("user_id"),
            "anchor_image_url": "",
            "source_type": "explore",
            "remixed_from_prompt_id": None,
            "current_prompt": "Cinematic artwork, highly detailed",
            "style_weight": req.style_weight or 0.60,
            "turn_count": 0,
            "last_generated_job_id": None,
            "created_at": now_iso,
            "updated_at": now_iso,
            "messages": []
        }
        _REMIX_SESSIONS[session_id] = session

    if session["turn_count"] >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Session free refinement limit reached (5 turns max). Please generate to continue."
        )

    t0 = time.time()
    user_now = datetime.now(timezone.utc).isoformat()

    # User message
    user_msg = RemixMessage(
        id=f"msg_u_{uuid.uuid4().hex[:8]}",
        session_id=session_id,
        role="user",
        content=req.user_instruction,
        created_at=user_now
    )
    session["messages"].append(user_msg)

    # Prompt delta compilation via PromptService
    try:
        delta_res = await service.compile_delta(
            base_prompt=session["current_prompt"],
            user_instruction=req.user_instruction,
            ai_model=req.ai_model or "groq"
        )
        compiled_prompt = delta_res.compiled_prompt
        diff_added = delta_res.diff.added
        diff_removed = delta_res.diff.removed
        suggested_chips = delta_res.suggested_chips or DEFAULT_SUGGESTED_CHIPS
        model_used = delta_res.model_used
    except Exception as e:
        logger.warning(f"[Remix] LLM delta fallback: {e}")
        compiled_prompt = f"{session["current_prompt"]}, {req.user_instruction}, 8k resolution, cinematic lighting"
        diff_added = [req.user_instruction]
        diff_removed = []
        suggested_chips = DEFAULT_SUGGESTED_CHIPS
        model_used = "Local Fallback Engine"

    elapsed_ms = int((time.time() - t0) * 1000)
    assistant_now = datetime.now(timezone.utc).isoformat()

    assistant_msg = RemixMessage(
        id=f"msg_a_{uuid.uuid4().hex[:8]}",
        session_id=session_id,
        role="assistant",
        content=f"Applied: \"{req.user_instruction}\". Refined prompt recipe for diffusion synthesis.",
        diff_added=diff_added,
        diff_removed=diff_removed,
        suggested_chips=suggested_chips,
        model_used=model_used,
        latency_ms=elapsed_ms,
        created_at=assistant_now
    )
    session["messages"].append(assistant_msg)
    session["current_prompt"] = compiled_prompt
    session["turn_count"] += 1
    session["updated_at"] = assistant_now
    if req.style_weight is not None:
        session["style_weight"] = req.style_weight

    logger.info(f"[Remix] Refined session {session_id} turn {session["turn_count"]} in {elapsed_ms}ms")
    return RemixChatTurnResponse(
        session_id=session_id,
        compiled_prompt=compiled_prompt,
        user_message=user_msg,
        assistant_message=assistant_msg,
        turn_count=session["turn_count"],
        suggested_chips=suggested_chips,
        model_used=model_used,
        latency_ms=elapsed_ms
    )

import time
import uuid
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.schemas.remix import (
    CreateRemixSessionRequest,
    RemixSessionResponse,
    RemixChatMessage,
    RemixChatRequest,
    RemixChatResponse,
    RemixSessionHistoryResponse,
)
from app.services.prompt_service import PromptService
from app.core.supabase_client import get_supabase_admin

logger = logging.getLogger("craftai.remix_service")

# In-memory session store for local dev resilience when Supabase DB is offline
_IN_MEMORY_SESSIONS: Dict[str, Dict[str, Any]] = {}
_IN_MEMORY_MESSAGES: Dict[str, List[Dict[str, Any]]] = {}

INITIAL_SUGGESTED_CHIPS = [
    "+ Cyberpunk Neon",
    "+ Studio Ghibli Anime",
    "+ 3D Octane Render",
    "+ Dark Moody Cinematic",
    "+ Watercolor Dreamscape",
]

class RemixService:
    def __init__(self, prompt_service: PromptService):
        self.prompt_service = prompt_service
        try:
            self.supabase = get_supabase_admin()
        except Exception as e:
            logger.warning(f"Failed to initialize Supabase admin client: {e}. Operating in resilient memory mode.")
            self.supabase = None

    async def create_session(
        self,
        req: CreateRemixSessionRequest,
        user_id: Optional[str] = None
    ) -> RemixSessionHistoryResponse:
        session_id = str(uuid.uuid4())
        effective_user_id = user_id or "00000000-0000-0000-0000-000000000000"
        now_iso = datetime.utcnow().isoformat()

        session_data = {
            "id": session_id,
            "user_id": effective_user_id,
            "anchor_image_url": req.anchor_image_url,
            "source_type": req.source_type,
            "remixed_from_prompt_id": req.remixed_from_prompt_id,
            "current_prompt": req.initial_prompt or "Preserve subject with balanced aesthetics",
            "style_weight": req.style_weight,
            "turn_count": 0,
            "last_generated_job_id": None,
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        initial_msg_id = str(uuid.uuid4())
        welcome_message = {
            "id": initial_msg_id,
            "session_id": session_id,
            "role": "assistant",
            "content": "Reference artwork locked as visual anchor. What style, lighting, or atmosphere modifications would you like to apply?",
            "diff_added": ["composition_anchor"],
            "diff_removed": [],
            "suggested_chips": INITIAL_SUGGESTED_CHIPS,
            "generated_image_url": None,
            "model_used": "system/anchor-director",
            "latency_ms": 15,
            "created_at": now_iso,
        }

        # Try persisting to Supabase
        if self.supabase:
            try:
                self.supabase.table("remix_sessions").insert(session_data).execute()
                self.supabase.table("remix_messages").insert(welcome_message).execute()
            except Exception as e:
                logger.warning(f"Supabase write failed for remix session {session_id}: {e}. Storing in memory fallback.")
                _IN_MEMORY_SESSIONS[session_id] = session_data
                _IN_MEMORY_MESSAGES[session_id] = [welcome_message]
        else:
            _IN_MEMORY_SESSIONS[session_id] = session_data
            _IN_MEMORY_MESSAGES[session_id] = [welcome_message]

        session_resp = RemixSessionResponse(**session_data)
        msg_resp = RemixChatMessage(**welcome_message)

        return RemixSessionHistoryResponse(
            session=session_resp,
            messages=[msg_resp]
        )

    async def get_session_history(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> Optional[RemixSessionHistoryResponse]:
        session_data = None
        messages_data = []

        if self.supabase:
            try:
                res = self.supabase.table("remix_sessions").select("*").eq("id", session_id).execute()
                if res.data and len(res.data) > 0:
                    session_data = res.data[0]
                    msg_res = self.supabase.table("remix_messages").select("*").eq("session_id", session_id).order("created_at").execute()
                    messages_data = msg_res.data or []
            except Exception as e:
                logger.warning(f"Supabase fetch failed for session {session_id}: {e}")

        if not session_data and session_id in _IN_MEMORY_SESSIONS:
            session_data = _IN_MEMORY_SESSIONS[session_id]
            messages_data = _IN_MEMORY_MESSAGES.get(session_id, [])

        if not session_data:
            return None

        return RemixSessionHistoryResponse(
            session=RemixSessionResponse(**session_data),
            messages=[RemixChatMessage(**m) for m in messages_data]
        )

    async def execute_chat_turn(
        self,
        req: RemixChatRequest,
        user_id: Optional[str] = None
    ) -> RemixChatResponse:
        start_time = time.time()
        session_id = req.session_id

        # 1. Fetch current session state
        history = await self.get_session_history(session_id, user_id)
        if not history:
            # Auto-create session if missing to prevent dead-end errors
            default_create = CreateRemixSessionRequest(
                anchor_image_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb",
                source_type="custom",
                initial_prompt="Visual masterpiece"
            )
            history = await self.create_session(default_create, user_id)
            session_id = history.session.id

        session = history.session
        base_prompt = session.current_prompt
        new_turn_count = session.turn_count + 1

        # 2. Compile Delta via PromptService (defaults to high-speed Groq LPU)
        ai_engine = req.ai_model or "groq"
        delta_res = await self.prompt_service.compile_delta(
            base_prompt=base_prompt,
            user_instruction=req.user_instruction,
            ai_model=ai_engine
        )

        now_iso = datetime.utcnow().isoformat()
        latency_ms = int((time.time() - start_time) * 1000)

        # 3. Create User Message
        user_msg = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "role": "user",
            "content": req.user_instruction,
            "diff_added": [],
            "diff_removed": [],
            "suggested_chips": [],
            "generated_image_url": None,
            "model_used": None,
            "latency_ms": None,
            "created_at": now_iso,
        }

        # 4. Create Assistant Message
        added_desc = f"Applied: {', '.join(delta_res.diff.added)}" if delta_res.diff.added else "Applied style adjustments."
        assistant_content = f"{added_desc} Refined formula ready for diffusion synthesis."

        assistant_msg = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "role": "assistant",
            "content": assistant_content,
            "diff_added": delta_res.diff.added,
            "diff_removed": delta_res.diff.removed,
            "suggested_chips": delta_res.suggested_chips or INITIAL_SUGGESTED_CHIPS,
            "generated_image_url": None,
            "model_used": delta_res.model_used,
            "latency_ms": latency_ms,
            "created_at": now_iso,
        }

        # 5. Update Session State
        updated_weight = req.style_weight if req.style_weight is not None else session.style_weight
        update_data = {
            "current_prompt": delta_res.compiled_prompt,
            "turn_count": new_turn_count,
            "style_weight": updated_weight,
            "updated_at": now_iso,
        }

        if self.supabase:
            try:
                self.supabase.table("remix_messages").insert([user_msg, assistant_msg]).execute()
                self.supabase.table("remix_sessions").update(update_data).eq("id", session_id).execute()
            except Exception as e:
                logger.warning(f"Supabase update failed for chat turn: {e}")
                if session_id in _IN_MEMORY_SESSIONS:
                    _IN_MEMORY_SESSIONS[session_id].update(update_data)
                    _IN_MEMORY_MESSAGES.setdefault(session_id, []).extend([user_msg, assistant_msg])
        else:
            if session_id in _IN_MEMORY_SESSIONS:
                _IN_MEMORY_SESSIONS[session_id].update(update_data)
                _IN_MEMORY_MESSAGES.setdefault(session_id, []).extend([user_msg, assistant_msg])

        return RemixChatResponse(
            session_id=session_id,
            compiled_prompt=delta_res.compiled_prompt,
            user_message=RemixChatMessage(**user_msg),
            assistant_message=RemixChatMessage(**assistant_msg),
            turn_count=new_turn_count,
            suggested_chips=delta_res.suggested_chips or INITIAL_SUGGESTED_CHIPS,
            model_used=delta_res.model_used,
            latency_ms=latency_ms
        )

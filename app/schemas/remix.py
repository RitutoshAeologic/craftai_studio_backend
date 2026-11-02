from typing import Optional, List, Any
from pydantic import BaseModel, Field, model_validator
from datetime import datetime, timezone
import uuid

class RemixMessage(BaseModel):
    id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    session_id: str
    role: str = "assistant"  # user | assistant
    content: str
    diff_added: List[str] = Field(default_factory=list)
    diff_removed: List[str] = Field(default_factory=list)
    suggested_chips: List[str] = Field(default_factory=list)
    generated_image_url: Optional[str] = None
    model_used: Optional[str] = None
    latency_ms: Optional[int] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class RemixSessionCreateRequest(BaseModel):
    anchor_image_url: str = Field(..., description="Reference seed image URL or data URI")
    anchorImageUrl: Optional[str] = None
    source_type: str = Field("explore", description="Origin: explore, library, or upload")
    sourceType: Optional[str] = None
    remixed_from_prompt_id: Optional[str] = None
    remixedFromPromptId: Optional[str] = None
    initial_prompt: Optional[str] = "Preserve subject with balanced aesthetics"
    initialPrompt: Optional[str] = None
    style_weight: float = Field(0.60, ge=0.0, le=1.0)
    styleWeight: Optional[float] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            url = data.get("anchor_image_url") or data.get("anchorImageUrl") or data.get("image_url") or data.get("imageUrl")
            if url:
                data["anchor_image_url"] = str(url)
            src = data.get("source_type") or data.get("sourceType")
            if src:
                data["source_type"] = str(src)
            remix_id = data.get("remixed_from_prompt_id") or data.get("remixedFromPromptId") or data.get("prompt_id")
            if remix_id:
                data["remixed_from_prompt_id"] = str(remix_id)
            init_p = data.get("initial_prompt") or data.get("initialPrompt")
            if init_p:
                data["initial_prompt"] = str(init_p)
            sw = data.get("style_weight") if data.get("style_weight") is not None else data.get("styleWeight")
            if sw is not None:
                try:
                    data["style_weight"] = float(sw)
                except Exception:
                    pass
        return data

class RemixSessionResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    anchor_image_url: str
    source_type: str = "explore"
    remixed_from_prompt_id: Optional[str] = None
    current_prompt: str
    style_weight: float = 0.60
    turn_count: int = 0
    last_generated_job_id: Optional[str] = None
    created_at: str
    updated_at: str
    messages: List[RemixMessage] = Field(default_factory=list)

class RemixChatRequest(BaseModel):
    session_id: str
    sessionId: Optional[str] = None
    user_instruction: str = Field(..., min_length=1, max_length=1000)
    userInstruction: Optional[str] = None
    ai_model: Optional[str] = "groq"
    aiModel: Optional[str] = None
    style_weight: Optional[float] = 0.60
    styleWeight: Optional[float] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            sid = data.get("session_id") or data.get("sessionId")
            if sid:
                data["session_id"] = str(sid)
            inst = data.get("user_instruction") or data.get("userInstruction")
            if inst:
                data["user_instruction"] = str(inst)
            model = data.get("ai_model") or data.get("aiModel")
            if model:
                data["ai_model"] = str(model)
            sw = data.get("style_weight") if data.get("style_weight") is not None else data.get("styleWeight")
            if sw is not None:
                try:
                    data["style_weight"] = float(sw)
                except Exception:
                    pass
        return data

class RemixChatTurnResponse(BaseModel):
    session_id: str
    compiled_prompt: str
    user_message: RemixMessage
    assistant_message: RemixMessage
    turn_count: int
    suggested_chips: List[str] = Field(default_factory=list)
    model_used: str = "groq"
    latency_ms: int = 0

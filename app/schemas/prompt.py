import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator

class PromptExpandRequest(BaseModel):
    raw_prompt: str = Field(..., min_length=1, max_length=4000, description="Base user prompt text")
    rawPrompt: Optional[str] = None
    starter_chip: Optional[str] = Field(None, description="Optional style or scenario preset tag")
    starterChip: Optional[str] = None
    aspect_ratio: Optional[str] = Field("1:1", description="Target aspect ratio")
    aspectRatio: Optional[str] = None
    ai_model: Optional[str] = Field(None, description="Optional prompt engine: gemini, groq, openai, claude, local")
    aiModel: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            p = data.get("raw_prompt") or data.get("rawPrompt") or data.get("prompt")
            if p:
                data["raw_prompt"] = str(p)
            chip = data.get("starter_chip") or data.get("starterChip")
            if chip:
                data["starter_chip"] = str(chip)
            ratio = data.get("aspect_ratio") or data.get("aspectRatio")
            if ratio:
                data["aspect_ratio"] = str(ratio)
            model = data.get("ai_model") or data.get("aiModel") or data.get("model")
            if model:
                data["ai_model"] = str(model)
        return data

class PromptExpandResponse(BaseModel):
    master_prompt: str
    negative_prompt: str
    complexity_score: int
    model_used: str

class PromptDeltaRequest(BaseModel):
    session_id: Optional[str] = Field(
        default_factory=lambda: f"sess_{uuid.uuid4().hex[:12]}",
        description="Unique conversational copilot session ID (auto-generated if omitted)"
    )
    sessionId: Optional[str] = None
    turn_count: int = Field(default=1, ge=1, le=10, description="Number of conversational refinement turns")
    turnCount: Optional[int] = None
    base_prompt: str = Field(..., min_length=1, description="Current master prompt to refine")
    basePrompt: Optional[str] = None
    user_instruction: str = Field(..., min_length=1, description="Natural language delta change instruction")
    userInstruction: Optional[str] = None
    ai_model: Optional[str] = Field(None, description="Optional prompt engine: gemini, groq, openai, claude, local")
    aiModel: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            sid = data.get("session_id") or data.get("sessionId")
            if sid:
                data["session_id"] = str(sid)
            tc = data.get("turn_count") if data.get("turn_count") is not None else data.get("turnCount")
            if tc is not None:
                try:
                    data["turn_count"] = int(tc)
                except Exception:
                    pass
            bp = data.get("base_prompt") or data.get("basePrompt")
            if bp:
                data["base_prompt"] = str(bp)
            inst = data.get("user_instruction") or data.get("userInstruction")
            if inst:
                data["user_instruction"] = str(inst)
            model = data.get("ai_model") or data.get("aiModel") or data.get("model")
            if model:
                data["ai_model"] = str(model)
        return data

class PromptDeltaDiff(BaseModel):
    added: List[str] = Field(default_factory=list)
    removed: List[str] = Field(default_factory=list)

class PromptDeltaResponse(BaseModel):
    compiled_prompt: str
    diff: PromptDeltaDiff
    suggested_chips: List[str] = Field(default_factory=list)
    model_used: str

class LLMConfigResponse(BaseModel):
    active_provider: str
    fallback_order: List[str]
    available_providers: List[str]
    model_mappings: Dict[str, str]

import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class PromptExpandRequest(BaseModel):
    raw_prompt: str = Field(..., min_length=1, max_length=4000, description="Base user prompt text")
    starter_chip: Optional[str] = Field(None, description="Optional style or scenario preset tag")
    aspect_ratio: Optional[str] = Field("1:1", description="Target aspect ratio")
    ai_model: Optional[str] = Field(None, description="Optional prompt engine: gemini, groq, openai, claude, local")

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
    turn_count: int = Field(default=1, ge=1, le=10, description="Number of conversational refinement turns")
    base_prompt: str = Field(..., min_length=1, description="Current master prompt to refine")
    user_instruction: str = Field(..., min_length=1, description="Natural language delta change instruction")
    ai_model: Optional[str] = Field(None, description="Optional prompt engine: gemini, groq, openai, claude, local")

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

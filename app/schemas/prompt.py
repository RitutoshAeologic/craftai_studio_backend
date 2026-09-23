import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, AliasChoices, ConfigDict

class PromptExpandRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    raw_prompt: str = Field(..., min_length=1, max_length=4000, validation_alias=AliasChoices("raw_prompt", "rawPrompt", "prompt", "text"), description="Base user prompt text")
    starter_chip: Optional[str] = Field(None, validation_alias=AliasChoices("starter_chip", "starterChip", "chip", "preset"), description="Optional style or scenario preset tag")
    aspect_ratio: Optional[str] = Field("1:1", validation_alias=AliasChoices("aspect_ratio", "aspectRatio", "ratio"), description="Target aspect ratio")
    ai_model: Optional[str] = Field(None, validation_alias=AliasChoices("ai_model", "aiModel", "model", "engine"), description="Optional prompt engine: gemini, groq, openai, claude, local")

class StructuredPromptMetadata(BaseModel):
    subject: Optional[str] = Field(None, description="Primary subject entity, action, and key details")
    environment: Optional[str] = Field(None, description="Scene backdrop, location, atmosphere, and weather")
    lighting: Optional[str] = Field(None, description="Key light, rim light, ambient color, and shadow tones")
    camera_optics: Optional[str] = Field(None, description="Focal length, shot angle, aperture, and depth of field")
    art_style: Optional[str] = Field(None, description="Aesthetic style, genre, or photographic medium")
    avoid: List[str] = Field(default_factory=list, description="Negative filtering tokens to eliminate")
    preserved_elements: List[str] = Field(default_factory=list, description="Locked attributes across multi-turn chat edits")

class PromptExpandResponse(BaseModel):
    master_prompt: str
    negative_prompt: str
    complexity_score: int
    model_used: str
    structured_metadata: Optional[StructuredPromptMetadata] = None

class PromptDeltaRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    session_id: Optional[str] = Field(
        default_factory=lambda: f"sess_{uuid.uuid4().hex[:12]}",
        validation_alias=AliasChoices("session_id", "sessionId"),
        description="Unique conversational copilot session ID (auto-generated if omitted)"
    )
    turn_count: int = Field(default=1, ge=1, le=10, validation_alias=AliasChoices("turn_count", "turnCount", "turn"), description="Number of conversational refinement turns")
    base_prompt: str = Field(..., min_length=1, validation_alias=AliasChoices("base_prompt", "basePrompt", "prompt", "current_prompt"), description="Current master prompt to refine")
    user_instruction: str = Field(..., min_length=1, validation_alias=AliasChoices("user_instruction", "userInstruction", "instruction", "message"), description="Natural language delta change instruction")
    ai_model: Optional[str] = Field(None, validation_alias=AliasChoices("ai_model", "aiModel", "model", "engine"), description="Optional prompt engine: gemini, groq, openai, claude, local")

class PromptDeltaDiff(BaseModel):
    added: List[str] = Field(default_factory=list)
    removed: List[str] = Field(default_factory=list)

class PromptDeltaResponse(BaseModel):
    compiled_prompt: str
    diff: PromptDeltaDiff
    suggested_chips: List[str] = Field(default_factory=list)
    model_used: str
    structured_metadata: Optional[StructuredPromptMetadata] = None

class LLMConfigResponse(BaseModel):
    active_provider: str
    fallback_order: List[str]
    available_providers: List[str]
    model_mappings: Dict[str, str]

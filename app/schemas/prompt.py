from typing import Optional, List, Dict
from pydantic import BaseModel, Field

class PromptExpandRequest(BaseModel):
    raw_prompt: str = Field(..., min_length=1, max_length=4000, description="Base user prompt text")
    starter_chip: Optional[str] = Field(None, description="Optional style or scenario preset tag")
    aspect_ratio: Optional[str] = Field("1:1", description="Target aspect ratio")
    ai_model: Optional[str] = Field("groq", description="Prompt engine provider: groq, gemini, claude, gpt4")

class PromptExpandResponse(BaseModel):
    master_prompt: str
    negative_prompt: str
    complexity_score: int
    model_used: str

class PromptDeltaRequest(BaseModel):
    session_id: str = Field(..., description="Unique conversational copilot session ID")
    turn_count: int = Field(default=1, ge=1, le=10, description="Number of conversational refinement turns")
    base_prompt: str = Field(..., min_length=1, description="Current master prompt to refine")
    user_instruction: str = Field(..., min_length=1, description="Natural language delta change instruction")
    ai_model: Optional[str] = Field("groq", description="Prompt engine provider: groq, gemini, claude, gpt4")

class PromptDeltaDiff(BaseModel):
    added: List[str] = Field(default_factory=list)
    removed: List[str] = Field(default_factory=list)

class PromptDeltaResponse(BaseModel):
    compiled_prompt: str
    diff: PromptDeltaDiff
    suggested_chips: List[str] = Field(default_factory=list)
    model_used: str

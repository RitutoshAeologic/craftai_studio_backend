import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class CreateRemixSessionRequest(BaseModel):
    anchor_image_url: str = Field(..., min_length=5, description="Reference image URL to anchor composition")
    source_type: str = Field(default="explore", description="Source of artwork: explore, library, or custom")
    remixed_from_prompt_id: Optional[str] = Field(None, description="UUID of Explore prompt for creator royalties")
    initial_prompt: Optional[str] = Field(
        default="Preserve core subject and composition of anchor image with balanced styling",
        description="Initial seed prompt recipe"
    )
    style_weight: float = Field(default=0.60, ge=0.10, le=1.00, description="Transformation intensity: 0.1 to 1.0")

class RemixChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: str = Field(..., description="user or assistant")
    content: str
    diff_added: List[str] = Field(default_factory=list)
    diff_removed: List[str] = Field(default_factory=list)
    suggested_chips: List[str] = Field(default_factory=list)
    generated_image_url: Optional[str] = None
    model_used: Optional[str] = "groq/qwen3.8-27b"
    latency_ms: Optional[int] = None
    created_at: Optional[str] = None

class RemixSessionResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    anchor_image_url: str
    source_type: str
    remixed_from_prompt_id: Optional[str] = None
    current_prompt: str
    style_weight: float
    turn_count: int
    last_generated_job_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class RemixChatRequest(BaseModel):
    session_id: str = Field(..., description="Remix session UUID")
    user_instruction: str = Field(..., min_length=1, max_length=500, description="User modification instruction")
    ai_model: Optional[str] = Field(default="groq", description="Target LLM (groq for low-latency LPU, gemini, etc.)")
    style_weight: Optional[float] = Field(None, ge=0.10, le=1.00, description="Updated transformation intensity")

class RemixChatResponse(BaseModel):
    session_id: str
    compiled_prompt: str
    user_message: RemixChatMessage
    assistant_message: RemixChatMessage
    turn_count: int
    suggested_chips: List[str] = Field(default_factory=list)
    model_used: str
    latency_ms: int

class RemixSessionHistoryResponse(BaseModel):
    session: RemixSessionResponse
    messages: List[RemixChatMessage] = Field(default_factory=list)

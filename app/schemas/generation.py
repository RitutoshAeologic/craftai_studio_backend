from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class GenerationDispatchRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000, description="Compiled generation prompt")
    character_id: Optional[str] = Field(None, description="Consistent character entity ID")
    face_reference_urls: Optional[List[str]] = Field(None, description="Face lock reference photo URLs")
    negative_prompt: Optional[str] = Field(None, description="Explicit negative tokens to eliminate unwanted artifacts")
    structured_metadata: Optional[Dict[str, Any]] = Field(None, description="Visual Director structured metadata")
    width: Optional[int] = Field(1024, ge=512, le=2048)
    height: Optional[int] = Field(1024, ge=512, le=2048)
    seed: Optional[int] = Field(42, description="RNG Seed for reproducibility")
    model: Optional[str] = Field("flux", description="Diffusion model: flux, gemini, chatgpt")
    remixed_from_prompt_id: Optional[str] = Field(None, description="Original explore prompt ID if remixed")

class GenerationDispatchResponse(BaseModel):
    task_id: str
    tier: str
    status: str
    estimated_seconds: int
    direct_image_url: Optional[str] = None

class GenerationStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    output_url: Optional[str] = None

class WebSocketProgressMessage(BaseModel):
    progress: int = Field(..., ge=0, le=100)
    status: str
    message: str

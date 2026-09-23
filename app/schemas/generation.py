from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, AliasChoices, ConfigDict

class GenerationDispatchRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    prompt: str = Field(..., min_length=1, max_length=4000, validation_alias=AliasChoices("prompt", "raw_prompt", "rawPrompt"), description="Compiled generation prompt")
    negative_prompt: Optional[str] = Field(None, validation_alias=AliasChoices("negative_prompt", "negativePrompt", "avoid"), description="Explicit negative tokens to eliminate unwanted artifacts")
    structured_metadata: Optional[Dict[str, Any]] = Field(None, validation_alias=AliasChoices("structured_metadata", "structuredMetadata", "metadata"), description="Visual Director structured metadata")
    character_id: Optional[str] = Field(None, validation_alias=AliasChoices("character_id", "characterId"), description="Consistent character entity ID")
    face_reference_urls: Optional[List[str]] = Field(None, validation_alias=AliasChoices("face_reference_urls", "faceReferenceUrls", "reference_images", "referenceImages", "references"), description="Face lock reference photo URLs")
    width: Optional[int] = Field(1024, ge=512, le=2048)
    height: Optional[int] = Field(1024, ge=512, le=2048)
    seed: Optional[int] = Field(42, description="RNG Seed for reproducibility")
    model: Optional[str] = Field("flux", description="Diffusion model: flux, gemini, chatgpt")
    remixed_from_prompt_id: Optional[str] = Field(None, validation_alias=AliasChoices("remixed_from_prompt_id", "remixedFromPromptId"), description="Original explore prompt ID if remixed")

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

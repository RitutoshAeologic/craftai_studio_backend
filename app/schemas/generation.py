from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator

class GenerationDispatchRequest(BaseModel):
    task_id: Optional[str] = Field(None, description="Client-generated task ID to synchronize WebSocket progress")
    taskId: Optional[str] = None
    prompt: str = Field(..., min_length=1, max_length=4000, description="Compiled generation prompt")
    character_id: Optional[str] = Field(None, description="Consistent character entity ID")
    characterId: Optional[str] = None
    face_reference_urls: Optional[List[str]] = Field(None, description="Face lock reference photo URLs")
    faceReferenceUrls: Optional[List[str]] = None
    negative_prompt: Optional[str] = Field(None, description="Explicit negative tokens to eliminate unwanted artifacts")
    negativePrompt: Optional[str] = None
    structured_metadata: Optional[Dict[str, Any]] = Field(None, description="Visual Director structured metadata")
    structuredMetadata: Optional[Dict[str, Any]] = None
    width: Optional[int] = Field(1024, ge=512, le=2048)
    height: Optional[int] = Field(1024, ge=512, le=2048)
    seed: Optional[int] = Field(42, description="RNG Seed for reproducibility")
    model: Optional[str] = Field("flux", description="Diffusion model: flux, gemini, chatgpt")
    remixed_from_prompt_id: Optional[str] = Field(None, description="Original explore prompt ID if remixed")
    remixedFromPromptId: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            tid = data.get("task_id") or data.get("taskId")
            if tid:
                data["task_id"] = str(tid)
            cid = data.get("character_id") or data.get("characterId")
            if cid:
                data["character_id"] = str(cid)
            refs = data.get("face_reference_urls") or data.get("faceReferenceUrls")
            if refs is not None:
                data["face_reference_urls"] = refs
            neg = data.get("negative_prompt") or data.get("negativePrompt")
            if neg:
                data["negative_prompt"] = str(neg)
            meta = data.get("structured_metadata") or data.get("structuredMetadata")
            if meta is not None:
                data["structured_metadata"] = meta
            remix = data.get("remixed_from_prompt_id") or data.get("remixedFromPromptId")
            if remix:
                data["remixed_from_prompt_id"] = str(remix)
            # Aspect ratio to width/height fallback
            ratio = data.get("aspect_ratio") or data.get("aspectRatio")
            if ratio and (not data.get("width") or not data.get("height")):
                ratio_map = {
                    "1:1": (1024, 1024),
                    "16:9": (1344, 768),
                    "9:16": (768, 1344),
                    "4:5": (896, 1152),
                    "3:4": (864, 1152),
                    "4:3": (1152, 864),
                }
                if ratio in ratio_map:
                    w, h = ratio_map[ratio]
                    data.setdefault("width", w)
                    data.setdefault("height", h)
        return data

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

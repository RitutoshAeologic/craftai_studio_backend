from typing import Optional
from pydantic import BaseModel, Field

class VisionScanRequest(BaseModel):
    photo_url: Optional[str] = Field(None, description="Public image URL or reference key to scan")
    image_url: Optional[str] = Field(None, description="Alternative key for reference photo URL")

class VisionScanResponse(BaseModel):
    extracted_prompt: str = Field(..., description="Aesthetic diffusion prompt reverse-engineered from reference")
    detected_style: str = Field(..., description="Aesthetic style identified by multimodal model")
    lighting_optics: str = Field(..., description="Lighting geometry and camera optics inferred")
    model_used: str = Field(..., description="Multimodal vision model utilized")

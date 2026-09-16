from pydantic import BaseModel, Field

class VisionScanResponse(BaseModel):
    extracted_prompt: str = Field(..., description="Aesthetic diffusion prompt reverse-engineered from reference")
    detected_style: str = Field(..., description="Aesthetic style identified by multimodal model")
    lighting_optics: str = Field(..., description="Lighting geometry and camera optics inferred")
    model_used: str = Field(..., description="Multimodal vision model utilized")

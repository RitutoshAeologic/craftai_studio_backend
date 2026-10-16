from typing import Optional
from pydantic import BaseModel, Field

class ToolPresetRequest(BaseModel):
    image_id: str = Field(..., description="Target image identifier in library or session")
    image_url: Optional[str] = Field(default=None, description="Public URL or base64 data URL of the image to transform")
    action: str = Field(..., description="Action type: 'relight', 'bokeh', or 'upscale'")
    target_preset: str = Field(..., description="Preset identifier: 'golden_hour', 'studio_neon', 'rim_light', 'soft_bokeh'")
    lock_subject: bool = Field(default=True, description="Enforce strict subject face & silhouette preservation")

class ToolPresetResponse(BaseModel):
    task_id: str
    status: str
    applied_tool: str
    subject_masked: bool
    tokens_consumed: int
    output_url: str = ""
    image_url: str = Field(default="", description="Alias to output_url for web clients")

class RemoveBackgroundRequest(BaseModel):
    image_url: str = Field(..., description="Public or storage URL of the image to remove background from")

class RemoveBackgroundResponse(BaseModel):
    task_id: str
    status: str
    output_url: str
    cutout_url: str = Field(default="", description="Alias to output_url for web clients")
    tokens_consumed: int = 0

class UpscaleRequest(BaseModel):
    image_url: Optional[str] = Field(default=None, description="Public URL, storage URL, or base64 data URL of the image to upscale")
    image_id: Optional[str] = Field(default=None, description="Target image identifier in library or session if URL omitted")
    scale: Optional[int] = Field(default=2, ge=2, le=4, description="Upscale multiplier: 2 (2X HD) or 4 (4X Ultra 4K)")
    scale_factor: Optional[int] = Field(default=None, description="Mobile client alias for scale multiplier (2 or 4)")
    user_id: Optional[str] = Field(default=None, description="Optional user identifier from client")
    mode: str = Field(default="photo", description="Enhancement mode: 'photo' (Realistic Photo), 'anime' (Digital Art/Anime), 'portrait' (Face Clarity), or 'fast' (Instant Crisp)")

class UpscaleResponse(BaseModel):
    task_id: str
    status: str
    scale: int
    mode: str
    original_resolution: str
    upscaled_resolution: str
    output_url: str
    image_url: str = Field(default="", description="Alias to output_url for client compatibility")
    tokens_consumed: int = 0
    is_free: bool = True
    engine: str = Field(default="Optical Super-Resolution (CPU)", description="AI or optical engine used (e.g., 'Real-ESRGAN (ONNX)', 'CodeFormer (Face Restoration)', etc.)")

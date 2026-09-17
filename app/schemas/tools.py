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

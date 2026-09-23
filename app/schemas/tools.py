from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, AliasChoices, ConfigDict, model_validator, field_validator

# ── Base Model for Multi-Client Responses (Web & Mobile Parity) ──────────────
class BaseToolResponse(BaseModel):
    task_id: str
    status: str
    output_url: str = ""
    image_url: str = Field(default="", description="Alias to output_url for Next.js web clients")
    url: str = Field(default="", description="Generic alias to output_url for web clients")
    credits_deducted: float = Field(default=0.0, description="Wallet credits charged")
    tokens_consumed: int = Field(default=0, description="Token consumption metrics")
    error_message: Optional[str] = Field(default=None, description="Error detail if failed")

    @model_validator(mode="after")
    def sync_url_aliases(self):
        if self.output_url:
            if not self.image_url:
                self.image_url = self.output_url
            if not self.url:
                self.url = self.output_url
        return self


# ── Preset Tools ─────────────────────────────────────────────────────────────
class ToolPresetRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    image_id: str = Field(..., validation_alias=AliasChoices("image_id", "imageId", "id"), description="Target image identifier in library or session")
    image_url: Optional[str] = Field(default=None, validation_alias=AliasChoices("image_url", "imageUrl", "photo_url", "url"), description="Public URL or base64 data URL")
    action: str = Field(..., description="Action type: 'relight', 'bokeh', or 'upscale'")
    target_preset: str = Field(..., validation_alias=AliasChoices("target_preset", "targetPreset", "preset"), description="Preset identifier")
    lock_subject: bool = Field(default=True, validation_alias=AliasChoices("lock_subject", "lockSubject"), description="Enforce strict subject face & silhouette preservation")
    user_id: Optional[str] = Field(default=None, validation_alias=AliasChoices("user_id", "userId"))

class ToolPresetResponse(BaseToolResponse):
    applied_tool: str = ""
    subject_masked: bool = False


# ── Skill 1: Remove Background ────────────────────────────────────────────────
class RemoveBackgroundRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    image_url: str = Field(..., validation_alias=AliasChoices("image_url", "imageUrl", "photo_url", "url"), description="Public or storage URL of the image")
    user_id: Optional[str] = Field(default=None, validation_alias=AliasChoices("user_id", "userId"))

class RemoveBackgroundResponse(BaseToolResponse):
    cutout_url: str = Field(default="", description="Alias to output_url for Next.js web client")

    @model_validator(mode="after")
    def sync_cutout_url(self):
        if self.output_url and not self.cutout_url:
            self.cutout_url = self.output_url
        return self


# ── Skill 2: AI Backgrounds ───────────────────────────────────────────────────
class AiBackgroundRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    image_url: str = Field(..., validation_alias=AliasChoices("image_url", "imageUrl", "photo_url", "url"), description="Source image (cutout or product photo)")
    mode: str = Field(default="pure_white", description="'pure_white', 'smart', or 'custom'")
    custom_backdrop: Optional[str] = Field(default=None, validation_alias=AliasChoices("custom_backdrop", "customBackdrop", "backdrop", "prompt"), description="Custom background description")
    aspect_ratio: str = Field(default="Auto", validation_alias=AliasChoices("aspect_ratio", "aspectRatio", "ratio"), description="Output ratio")
    quality: str = Field(default="1k", description="'1k' or '2k'")
    user_id: Optional[str] = Field(default=None, validation_alias=AliasChoices("user_id", "userId"))

class AiBackgroundResponse(BaseToolResponse):
    mode: str = "pure_white"


# ── Skill 3: AI Expand ────────────────────────────────────────────────────────
class AiExpandRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    image_url: str = Field(..., validation_alias=AliasChoices("image_url", "imageUrl", "photo_url", "url"), description="Source image to expand")
    target_ratio: str = Field(default="16:9", validation_alias=AliasChoices("target_ratio", "targetRatio", "aspect_ratio", "aspectRatio"), description="Target ratio")
    quality: str = Field(default="1k", description="'1k' or '2k'")
    user_id: Optional[str] = Field(default=None, validation_alias=AliasChoices("user_id", "userId"))

class AiExpandResponse(BaseToolResponse):
    target_ratio: str = "16:9"


# ── Skill 4: Upscale 4K ───────────────────────────────────────────────────────
class UpscaleRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    image_url: str = Field(..., validation_alias=AliasChoices("image_url", "imageUrl", "photo_url", "url"), description="Source image to upscale")
    scale_factor: Union[int, str] = Field(default=2, validation_alias=AliasChoices("scale_factor", "scaleFactor", "scale", "factor"), description="Scale multiplier")
    user_id: Optional[str] = Field(default=None, validation_alias=AliasChoices("user_id", "userId"))

    @field_validator("scale_factor", mode="before")
    @classmethod
    def parse_scale_factor(cls, v: Any) -> int:
        if isinstance(v, (int, float)):
            return max(2, min(int(v), 8))
        if isinstance(v, str):
            clean = v.lower().replace("x", "").strip()
            if clean.isdigit():
                return max(2, min(int(clean), 8))
        return 2

class UpscaleResponse(BaseToolResponse):
    resolution: str = "4096x4096"


# ── Skill 5: Product Detail Images ───────────────────────────────────────────
class ProductDetailRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    image_url: Optional[str] = Field(default=None, validation_alias=AliasChoices("image_url", "imageUrl", "photo_url", "url"), description="Hero product image")
    product_name: Optional[str] = Field(default="Commercial Product", validation_alias=AliasChoices("product_name", "productName", "name", "title"), description="Product title")
    aspect_ratio: str = Field(default="4:5", validation_alias=AliasChoices("aspect_ratio", "aspectRatio", "ratio"), description="Detail ratio")
    language: str = Field(default="Auto", description="Detail copy language")
    quality: str = Field(default="1k", description="'1k' or '2k'")
    user_id: Optional[str] = Field(default=None, validation_alias=AliasChoices("user_id", "userId"))

class ProductDetailResponse(BaseToolResponse):
    product_name: str = ""


# ── Skill 6: Marketing Poster ────────────────────────────────────────────────
class MarketingPosterRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    image_url: Optional[str] = Field(default=None, validation_alias=AliasChoices("image_url", "imageUrl", "photo_url"), description="Optional product/subject image to feature on poster")
    topic: Optional[str] = Field(default="Commercial Promotion", description="Poster topic")
    category: str = Field(default="Promotion", description="'Beverage', 'Fashion', 'Hiring', 'Flash Sale', 'Promotion'")
    aspect_ratio: str = Field(default="4:5", validation_alias=AliasChoices("aspect_ratio", "aspectRatio", "ratio"), description="Poster ratio")
    language: str = Field(default="Auto", description="Headline language")
    headline: Optional[str] = Field(default=None, description="Optional custom headline")
    quality: str = Field(default="1k", description="'1k' or '2k'")
    user_id: Optional[str] = Field(default=None, validation_alias=AliasChoices("user_id", "userId"))

class MarketingPosterResponse(BaseToolResponse):
    topic: str = ""
    headline: str = ""

from typing import Optional, Any
from pydantic import BaseModel, Field, model_validator

class ToolPresetRequest(BaseModel):
    image_id: Optional[str] = Field(default=None, description="Target image identifier in library or session")
    image_url: Optional[str] = Field(default=None, description="Public URL or base64 data URL of the image to transform")
    action: str = Field(default="relight", description="Action type: 'relight', 'bokeh', or 'upscale'")
    target_preset: str = Field(default="golden_hour", description="Preset identifier: 'golden_hour', 'studio_neon', 'rim_light', 'soft_bokeh'")
    lock_subject: bool = Field(default=True, description="Enforce strict subject face & silhouette preservation")

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "imageUrl" in data and not data.get("image_url"):
                data["image_url"] = data["imageUrl"]
            if "imageId" in data and not data.get("image_id"):
                data["image_id"] = data["imageId"]
            if not data.get("image_id"):
                data["image_id"] = "job_default"
        return data

class ToolPresetResponse(BaseModel):
    task_id: str
    status: str = "completed"
    applied_tool: str
    subject_masked: bool = True
    tokens_consumed: int = 0
    output_url: str = ""
    image_url: str = Field(default="", description="Alias to output_url for web clients")

class RemoveBackgroundRequest(BaseModel):
    image_url: Optional[str] = None
    imageUrl: Optional[str] = None
    userId: Optional[str] = None
    user_id: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            url = data.get("image_url") or data.get("imageUrl") or data.get("url") or data.get("image")
            if url:
                data["image_url"] = url
        return data

class RemoveBackgroundResponse(BaseModel):
    task_id: str
    status: str = "completed"
    output_url: str
    cutout_url: str = Field(default="", description="Alias to output_url for web clients")
    image_url: str = Field(default="", description="Alias to output_url for mobile clients")
    url: str = Field(default="", description="Alias to output_url")
    tokens_consumed: int = 0
    credits_deducted: int = 0

class UpscaleRequest(BaseModel):
    image_url: Optional[str] = Field(default=None, description="Public HTTPS image URL or Base64 data URL")
    imageUrl: Optional[str] = None
    image_id: Optional[str] = Field(default=None, description="Job ID in database if image_url is omitted")
    imageId: Optional[str] = None
    scale: Optional[int] = Field(default=2, description="Multiplier: 2 (2X HD) or 4 (4X Ultra 4K)")
    scale_factor: Optional[int] = Field(default=None, description="Mobile/Web alias for scale (accepts 2 or 4)")
    scaleFactor: Optional[int] = None
    mode: Optional[str] = Field(default="photo", description="Enhancement mode: 'photo', 'portrait', 'anime', or 'fast'")
    user_id: Optional[str] = Field(default=None, description="Optional tracking user ID")
    userId: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            url = data.get("image_url") or data.get("imageUrl") or data.get("url")
            if url:
                data["image_url"] = url
            scale = data.get("scale") or data.get("scale_factor") or data.get("scaleFactor")
            if scale:
                try:
                    data["scale"] = int(scale)
                    data["scale_factor"] = int(scale)
                except Exception:
                    pass
            uid = data.get("user_id") or data.get("userId")
            if uid:
                data["user_id"] = uid
        return data

class UpscaleResponse(BaseModel):
    task_id: str
    status: str = "completed"
    scale: int = 2
    mode: str = "photo"
    original_resolution: str = "1024x1024"
    upscaled_resolution: str = "2048x2048"
    output_url: str
    image_url: str
    url: str = ""
    tokens_consumed: int = 0
    credits_deducted: int = 0
    is_free: bool = True
    engine: str = "Optical Photo Super-Resolution (CPU)"

class AiBackgroundRequest(BaseModel):
    image_url: Optional[str] = None
    imageUrl: Optional[str] = None
    mode: Optional[str] = "pure_white"
    custom_backdrop: Optional[str] = None
    customBackdrop: Optional[str] = None
    aspect_ratio: Optional[str] = "1:1"
    aspectRatio: Optional[str] = None
    quality: Optional[str] = "1k"
    user_id: Optional[str] = None
    userId: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            url = data.get("image_url") or data.get("imageUrl") or data.get("url")
            if url:
                data["image_url"] = url
            backdrop = data.get("custom_backdrop") or data.get("customBackdrop")
            if backdrop:
                data["custom_backdrop"] = backdrop
            ratio = data.get("aspect_ratio") or data.get("aspectRatio")
            if ratio:
                data["aspect_ratio"] = ratio
        return data

class AiBackgroundResponse(BaseModel):
    task_id: str
    status: str = "completed"
    output_url: str
    image_url: str
    url: str = ""
    mode: str = "pure_white"
    tokens_consumed: int = 0
    credits_deducted: int = 0
    is_free: bool = True

class AiExpandRequest(BaseModel):
    image_url: Optional[str] = None
    imageUrl: Optional[str] = None
    target_ratio: Optional[str] = "16:9"
    targetRatio: Optional[str] = None
    quality: Optional[str] = "1k"
    user_id: Optional[str] = None
    userId: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            url = data.get("image_url") or data.get("imageUrl") or data.get("url")
            if url:
                data["image_url"] = url
            ratio = data.get("target_ratio") or data.get("targetRatio")
            if ratio:
                data["target_ratio"] = ratio
        return data

class AiExpandResponse(BaseModel):
    task_id: str
    status: str = "completed"
    output_url: str
    image_url: str
    url: str = ""
    target_ratio: str = "16:9"
    tokens_consumed: int = 0
    credits_deducted: int = 0
    is_free: bool = True

class ProductDetailRequest(BaseModel):
    image_url: Optional[str] = None
    imageUrl: Optional[str] = None
    product_name: Optional[str] = "Commercial Product"
    productName: Optional[str] = None
    aspect_ratio: Optional[str] = "4:5"
    aspectRatio: Optional[str] = None
    language: Optional[str] = "Auto"
    quality: Optional[str] = "1k"
    user_id: Optional[str] = None
    userId: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            url = data.get("image_url") or data.get("imageUrl") or data.get("url")
            if url:
                data["image_url"] = url
            name = data.get("product_name") or data.get("productName")
            if name:
                data["product_name"] = name
            ratio = data.get("aspect_ratio") or data.get("aspectRatio")
            if ratio:
                data["aspect_ratio"] = ratio
        return data

class ProductDetailResponse(BaseModel):
    task_id: str
    status: str = "completed"
    output_url: str
    image_url: str
    url: str = ""
    product_name: str = "Commercial Product"
    tokens_consumed: int = 0
    credits_deducted: int = 0
    is_free: bool = True

class MarketingPosterRequest(BaseModel):
    topic: Optional[str] = "Promotion"
    image_url: Optional[str] = None
    imageUrl: Optional[str] = None
    category: Optional[str] = "Promotion"
    aspect_ratio: Optional[str] = "4:5"
    aspectRatio: Optional[str] = None
    headline: Optional[str] = None
    language: Optional[str] = "Auto"
    quality: Optional[str] = "1k"
    user_id: Optional[str] = None
    userId: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            url = data.get("image_url") or data.get("imageUrl") or data.get("url")
            if url:
                data["image_url"] = url
            ratio = data.get("aspect_ratio") or data.get("aspectRatio")
            if ratio:
                data["aspect_ratio"] = ratio
        return data

class MarketingPosterResponse(BaseModel):
    task_id: str
    status: str = "completed"
    output_url: str
    image_url: str
    url: str = ""
    topic: str = "Promotion"
    tokens_consumed: int = 0
    credits_deducted: int = 0
    is_free: bool = True


class RemoveObjectRequest(BaseModel):
    image_url: Optional[str] = Field(default=None, description="Image URL or Base64 data URL")
    imageUrl: Optional[str] = None
    mask_url: Optional[str] = Field(default=None, description="Mask URL or Base64 data URL (white=erase, black=keep)")
    maskUrl: Optional[str] = None
    image_base64: Optional[str] = None
    mask_base64: Optional[str] = None
    user_id: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            url = data.get("image_url") or data.get("imageUrl") or data.get("url")
            if url:
                data["image_url"] = url
            mask = data.get("mask_url") or data.get("maskUrl") or data.get("mask")
            if mask:
                data["mask_url"] = mask
        return data

class RemoveObjectResponse(BaseModel):
    task_id: str
    status: str = "completed"
    output_url: str
    image_url: str = Field(default="", description="Alias to output_url")
    url: str = Field(default="", description="Alias to output_url")
    tokens_consumed: int = 0
    credits_deducted: int = 0
    latency_ms: Optional[float] = None
    is_free: bool = True

class ColorizeRequest(BaseModel):
    image_url: Optional[str] = Field(default=None, description="Image URL or Base64 data URL to colorize")
    imageUrl: Optional[str] = None
    image_base64: Optional[str] = None
    saturation: float = Field(default=1.0, description="Color saturation multiplier: 0.5 to 2.0")
    user_id: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            url = data.get("image_url") or data.get("imageUrl") or data.get("url")
            if url:
                data["image_url"] = url
        return data

class ColorizeResponse(BaseModel):
    task_id: str
    status: str = "completed"
    output_url: str
    image_url: str = Field(default="", description="Alias to output_url")
    url: str = Field(default="", description="Alias to output_url")
    tokens_consumed: int = 0
    credits_deducted: int = 0
    latency_ms: Optional[float] = None
    is_free: bool = True

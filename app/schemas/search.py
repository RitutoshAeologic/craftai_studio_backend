from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class UniversalSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Search keyword across prompts, tags, styles")
    search_type: str = Field("text", description="'text' | 'image' | 'video' multimodal search flag")
    models: Optional[List[str]] = Field(None, description="Filter by AI models (sdxl_lightning, flux, etc.)")
    tools: Optional[List[str]] = Field(None, description="Filter by tools (text_to_image, upscale, cutouts)")
    categories: Optional[List[str]] = Field(None, description="Filter by style categories")
    aspect_ratios: Optional[List[str]] = Field(None, description="Filter by ratios (1:1, 16:9, 9:16, 4:5)")
    collection_id: Optional[str] = Field(None, description="Scope search to a specific collection")
    sort_by: str = Field("newest", description="'newest' | 'popular' | 'remixed'")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    image_reference_url: Optional[str] = Field(None, description="Future visual embedding search input")
    video_reference_url: Optional[str] = Field(None, description="Future video embedding search input")

class SearchResultItem(BaseModel):
    id: str
    title: str
    preview_url: str
    author_name: str
    author_handle: str
    author_avatar: Optional[str] = None
    category: str
    model_used: str = "sdxl_lightning"
    tool_applied: str = "text_to_image"
    aspect_ratio: str = "1:1"
    dimensions: str = "1024x1024"
    seed: int = 42
    likes_count: int = 0
    remix_count: int = 0
    created_at: str

class UniversalSearchResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: List[SearchResultItem]

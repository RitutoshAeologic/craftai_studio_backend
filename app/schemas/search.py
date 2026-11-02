from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator

class UniversalSearchRequest(BaseModel):
    query: str = Field("", max_length=500, description="Search keyword across prompts, tags, styles")
    search_type: str = Field("text", description="text, image, or video multimodal search flag")
    searchType: Optional[str] = None
    models: Optional[List[str]] = Field(None, description="Filter by AI models (sdxl_lightning, flux, etc.)")
    tools: Optional[List[str]] = Field(None, description="Filter by tools (text_to_image, upscale, cutouts)")
    categories: Optional[List[str]] = Field(None, description="Filter by style categories")
    aspect_ratios: Optional[List[str]] = Field(None, description="Filter by ratios (1:1, 16:9, 9:16, 4:5)")
    aspectRatios: Optional[List[str]] = None
    collection_id: Optional[str] = Field(None, description="Scope search to a specific collection")
    collectionId: Optional[str] = None
    sort_by: str = Field("newest", description="newest, popular, or remixed")
    sortBy: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    pageSize: Optional[int] = None
    image_reference_url: Optional[str] = Field(None, description="Future visual embedding search input")
    imageReferenceUrl: Optional[str] = None
    video_reference_url: Optional[str] = Field(None, description="Future video embedding search input")
    videoReferenceUrl: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            st = data.get("search_type") or data.get("searchType")
            if st:
                data["search_type"] = str(st)
            ratios = data.get("aspect_ratios") or data.get("aspectRatios")
            if ratios is not None:
                data["aspect_ratios"] = ratios
            cid = data.get("collection_id") or data.get("collectionId")
            if cid:
                data["collection_id"] = str(cid)
            sb = data.get("sort_by") or data.get("sortBy")
            if sb:
                data["sort_by"] = str(sb)
            ps = data.get("page_size") if data.get("page_size") is not None else data.get("pageSize")
            if ps is not None:
                try:
                    data["page_size"] = int(ps)
                except Exception:
                    pass
            img = data.get("image_reference_url") or data.get("imageReferenceUrl")
            if img:
                data["image_reference_url"] = str(img)
            vid = data.get("video_reference_url") or data.get("videoReferenceUrl")
            if vid:
                data["video_reference_url"] = str(vid)
        return data

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

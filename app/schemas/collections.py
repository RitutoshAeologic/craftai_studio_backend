from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, model_validator

class CollectionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Collection name")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")
    is_private: bool = Field(True, description="Private to user or public")

class CollectionItemAddRequest(BaseModel):
    job_id: Optional[str] = Field(None, description="Supabase jobs.id reference")
    jobId: Optional[str] = None
    explore_prompt_id: Optional[str] = Field(None, description="Supabase explore_prompts.id reference")
    explorePromptId: Optional[str] = None
    item_id: Optional[str] = Field(None, description="Generic item identifier")
    itemId: Optional[str] = None
    artwork_id: Optional[str] = None
    image_url: str = Field(..., min_length=1, description="Direct URL of bookmarked artwork")
    imageUrl: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            url = data.get("image_url") or data.get("imageUrl") or data.get("url")
            if url:
                data["image_url"] = str(url)
            job = data.get("job_id") or data.get("jobId")
            if job:
                data["job_id"] = str(job)
            exp = data.get("explore_prompt_id") or data.get("explorePromptId") or data.get("prompt_id") or data.get("promptId")
            if exp:
                data["explore_prompt_id"] = str(exp)
            item = data.get("item_id") or data.get("itemId")
            if item:
                data["item_id"] = str(item)
            art = data.get("artwork_id") or data.get("artworkId")
            if art:
                data["artwork_id"] = str(art)
        return data

class CollectionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    item_count: int = 0
    is_default: bool = False
    is_private: bool = True
    created_at: str
    updated_at: str

class CollectionListResponse(BaseModel):
    total: int
    collections: List[CollectionResponse]

class CollectionItemListResponse(BaseModel):
    collection_id: str
    total: int
    items: List[Dict[str, Any]]

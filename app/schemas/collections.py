from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field

class CollectionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Collection name")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")
    is_private: bool = Field(True, description="Private to user or public")

class CollectionItemAddRequest(BaseModel):
    job_id: Optional[str] = Field(None, description="Supabase jobs.id reference")
    explore_prompt_id: Optional[str] = Field(None, description="Supabase explore_prompts.id reference")
    image_url: str = Field(..., min_length=1, description="Direct URL of bookmarked artwork")

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

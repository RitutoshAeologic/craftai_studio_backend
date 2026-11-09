from typing import List, Optional
from pydantic import BaseModel, Field

class CategoryItem(BaseModel):
    id: str
    slug: str
    name: str
    description: Optional[str] = None
    icon_name: str = "auto_awesome"
    keywords: List[str] = Field(default_factory=list)
    sort_order: int = 0
    is_active: bool = True

class CategoryListResponse(BaseModel):
    categories: List[CategoryItem]
    total: int

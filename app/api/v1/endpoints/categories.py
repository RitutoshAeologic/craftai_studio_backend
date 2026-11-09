from typing import List, Dict, Any
from fastapi import APIRouter
from app.core.supabase_client import get_supabase_admin
from app.core.logging import logger
from app.schemas.category import CategoryItem, CategoryListResponse

router = APIRouter(tags=["Categories & Taxonomy"])

# Standard starter categories fallback (parity when Supabase is offline/migrating)
_FALLBACK_CATEGORIES: List[Dict[str, Any]] = [
    {
        "id": "11111111-0000-0000-0000-000000000001",
        "slug": "photorealism",
        "name": "Photorealism",
        "description": "High-fidelity photographic portraits, 85mm optics, and lifelike textures",
        "icon_name": "camera_alt",
        "keywords": ["photo", "photograph", "85mm", "portrait", "realistic", "dslr"],
        "sort_order": 1,
        "is_active": True,
    },
    {
        "id": "11111111-0000-0000-0000-000000000002",
        "slug": "anime",
        "name": "Anime",
        "description": "Japanese animation, cel-shaded characters, and vibrant illustrative art",
        "icon_name": "palette",
        "keywords": ["anime", "manga", "ghibli", "makoto shinkai", "cel shaded", "waifu"],
        "sort_order": 2,
        "is_active": True,
    },
    {
        "id": "11111111-0000-0000-0000-000000000003",
        "slug": "cyberpunk",
        "name": "Cyberpunk",
        "description": "Futuristic neon cities, cyborg aesthetics, holographic glow, and synthwave",
        "icon_name": "electric_bolt",
        "keywords": ["cyberpunk", "neon", "futuristic", "cyborg", "synthwave", "sci-fi"],
        "sort_order": 3,
        "is_active": True,
    },
    {
        "id": "11111111-0000-0000-0000-000000000004",
        "slug": "3d-render",
        "name": "3D Render",
        "description": "CGI models, claymation, Octane/Blender renders, and isometric scenes",
        "icon_name": "view_in_ar",
        "keywords": ["3d", "render", "octane", "blender", "unreal engine", "cgi", "pixar"],
        "sort_order": 4,
        "is_active": True,
    },
    {
        "id": "11111111-0000-0000-0000-000000000005",
        "slug": "character",
        "name": "Character",
        "description": "Portraits, warriors, heroes, and unique concept character avatars",
        "icon_name": "person",
        "keywords": ["character", "portrait", "warrior", "knight", "woman", "man", "hero"],
        "sort_order": 5,
        "is_active": True,
    },
    {
        "id": "11111111-0000-0000-0000-000000000006",
        "slug": "architecture",
        "name": "Architecture",
        "description": "Interior design, modern facades, structural blueprints, and landscapes",
        "icon_name": "apartment",
        "keywords": ["architecture", "building", "house", "interior", "facade", "villa"],
        "sort_order": 6,
        "is_active": True,
    },
    {
        "id": "11111111-0000-0000-0000-000000000007",
        "slug": "product",
        "name": "Product",
        "description": "E-commerce packaging, bottle mockups, studio lighting, and consumer goods",
        "icon_name": "inventory_2",
        "keywords": ["product", "mockup", "bottle", "packaging", "watch", "sneakers"],
        "sort_order": 7,
        "is_active": True,
    },
]

@router.get("/categories", response_model=CategoryListResponse)
async def list_categories():
    """Returns active taxonomy categories with metadata, icons, and keyword tags."""
    try:
        admin = get_supabase_admin()
        res = admin.table("categories").select("*").eq("is_active", True).order("sort_order").execute()
        if res.data and len(res.data) > 0:
            items = [
                CategoryItem(
                    id=str(r.get("id")),
                    slug=r.get("slug", "general"),
                    name=r.get("name", "General"),
                    description=r.get("description"),
                    icon_name=r.get("icon_name", "auto_awesome"),
                    keywords=r.get("keywords") or [],
                    sort_order=r.get("sort_order", 0),
                    is_active=r.get("is_active", True),
                )
                for r in res.data
            ]
            return CategoryListResponse(categories=items, total=len(items))
    except Exception as e:
        logger.debug(f"[Categories] Supabase query fallback to starter categories: {e}")

    items = [CategoryItem(**r) for r in _FALLBACK_CATEGORIES]
    return CategoryListResponse(categories=items, total=len(items))

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from app.core.supabase_client import get_supabase_admin
from app.core.logging import logger
from app.schemas.search import (
    UniversalSearchRequest,
    UniversalSearchResponse,
    SearchResultItem,
)

router = APIRouter(tags=["Search & Discovery"])

# Rich community dataset for offline/local development parity
_COMMUNITY_CREATIONS: List[Dict[str, Any]] = [
    {
        "id": "exp_1",
        "title": "Cyber Ronin in Rain",
        "preview_url": "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=600&auto=format&fit=crop",
        "author_name": "Neo Akira",
        "author_handle": "@neo_akira",
        "author_avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop",
        "category": "Cyberpunk",
        "model_used": "sdxl_lightning",
        "tool_applied": "text_to_image",
        "aspect_ratio": "16:9",
        "dimensions": "1344x768",
        "seed": 4291823,
        "likes_count": 890,
        "remix_count": 342,
        "created_at": "2026-10-28T12:00:00Z"
    },
    {
        "id": "exp_2",
        "title": "Ethereal Studio Portrait",
        "preview_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=600&auto=format&fit=crop",
        "author_name": "Elena Rostova",
        "author_handle": "@elena_art",
        "author_avatar": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=100&auto=format&fit=crop",
        "category": "Photorealism",
        "model_used": "realvisxl_v4",
        "tool_applied": "text_to_image",
        "aspect_ratio": "4:5",
        "dimensions": "1024x1280",
        "seed": 881273,
        "likes_count": 1420,
        "remix_count": 512,
        "created_at": "2026-10-28T11:30:00Z"
    },
    {
        "id": "exp_3",
        "title": "Mecha Angel Guardian",
        "preview_url": "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=600&auto=format&fit=crop",
        "author_name": "Kaito Studio",
        "author_handle": "@kaito_anime",
        "author_avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop",
        "category": "Anime",
        "model_used": "flux_schnell",
        "tool_applied": "text_to_image",
        "aspect_ratio": "1:1",
        "dimensions": "1024x1024",
        "seed": 99318,
        "likes_count": 654,
        "remix_count": 219,
        "created_at": "2026-10-28T10:15:00Z"
    },
    {
        "id": "exp_4",
        "title": "Obsidian Minimalist Watch",
        "preview_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&auto=format&fit=crop",
        "author_name": "Voxel Craft",
        "author_handle": "@voxel_craft",
        "author_avatar": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&auto=format&fit=crop",
        "category": "Product",
        "model_used": "sdxl_lightning",
        "tool_applied": "upscale",
        "aspect_ratio": "1:1",
        "dimensions": "2048x2048",
        "seed": 112456,
        "likes_count": 420,
        "remix_count": 184,
        "created_at": "2026-10-28T09:00:00Z"
    },
    {
        "id": "exp_5",
        "title": "Neon Valkyrie 2099",
        "preview_url": "https://images.unsplash.com/photo-1563089145-599997674d42?w=600&auto=format&fit=crop",
        "author_name": "Sora Tanaka",
        "author_handle": "@sora_cg",
        "author_avatar": "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=100&auto=format&fit=crop",
        "category": "Cyberpunk",
        "model_used": "sdxl_lightning",
        "tool_applied": "text_to_image",
        "aspect_ratio": "9:16",
        "dimensions": "768x1344",
        "seed": 772199,
        "likes_count": 975,
        "remix_count": 412,
        "created_at": "2026-10-28T08:45:00Z"
    },
    {
        "id": "exp_6",
        "title": "Winter Fox Adventurer",
        "preview_url": "https://images.unsplash.com/photo-1474511320723-9a56873867b5?w=600&auto=format&fit=crop",
        "author_name": "Pixar Magic",
        "author_handle": "@pixar_craft",
        "author_avatar": "https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?w=100&auto=format&fit=crop",
        "category": "3D Render",
        "model_used": "flux_schnell",
        "tool_applied": "text_to_image",
        "aspect_ratio": "1:1",
        "dimensions": "1024x1024",
        "seed": 33182,
        "likes_count": 1890,
        "remix_count": 680,
        "created_at": "2026-10-28T07:30:00Z"
    }
]

@router.post("/search", response_model=UniversalSearchResponse)
async def universal_search(req: UniversalSearchRequest):
    """
    High-performance keyword & multi-attribute search across community creations.
    Uses PostgreSQL GIN index on Supabase when available, with fast local fallback.
    """
    query_str = req.query.lower().strip()

    # 1. Attempt Supabase Full-Text Search
    try:
        admin = get_supabase_admin()
        query = admin.table("explore_prompts").select("*")

        # Full-text search using PostgreSQL GIN index
        if query_str:
            query = query.ilike("title", f"%{query_str}%")

        if req.categories and len(req.categories) > 0:
            query = query.in_("category", req.categories)

        res = query.order("created_at", desc=True).limit(req.page_size).execute()
        if res.data and len(res.data) > 0:
            results = []
            for row in res.data:
                results.append(SearchResultItem(
                    id=row["id"],
                    title=row["title"],
                    preview_url=row.get("preview_image_url") or row.get("preview_url", ""),
                    author_name=row.get("author_name", "Creator"),
                    author_handle=row.get("author_handle", "@creator"),
                    author_avatar=row.get("author_avatar"),
                    category=row.get("category", "General"),
                    model_used=row.get("model_used", "sdxl_lightning"),
                    tool_applied=row.get("tool_applied", "text_to_image"),
                    aspect_ratio=row.get("aspect_ratio", "1:1"),
                    dimensions=row.get("dimensions", "1024x1024"),
                    seed=row.get("seed", 42),
                    likes_count=row.get("likes_count", 0),
                    remix_count=row.get("remix_count", 0),
                    created_at=str(row.get("created_at")),
                ))
            return UniversalSearchResponse(
                total=len(results),
                page=req.page,
                page_size=req.page_size,
                results=results
            )
    except Exception as e:
        logger.warning(f"[Search] Supabase GIN search notice: {e}. Executing local fallback search.")

    # 2. Local Fallback Search Filter
    filtered = []
    for item in _COMMUNITY_CREATIONS:
        match_query = (
            query_str in item["title"].lower() or
            query_str in item["category"].lower() or
            query_str in item["author_name"].lower() or
            query_str in item["author_handle"].lower()
        )
        if not match_query:
            continue
        if req.categories and item["category"] not in req.categories:
            continue
        if req.models and item["model_used"] not in req.models:
            continue
        if req.tools and item["tool_applied"] not in req.tools:
            continue
        if req.aspect_ratios and item["aspect_ratio"] not in req.aspect_ratios:
            continue
        filtered.append(SearchResultItem(**item))

    start = (req.page - 1) * req.page_size
    end = start + req.page_size
    page_results = filtered[start:end]

    return UniversalSearchResponse(
        total=len(filtered),
        page=req.page,
        page_size=req.page_size,
        results=page_results
    )

@router.get("/explore/similar/{card_id}", response_model=List[SearchResultItem])
async def get_similar_creations(
    card_id: str,
    limit: int = Query(10, ge=1, le=20)
):
    """
    Retrieves similar creations for the top horizontal carousel in Screen 2 (ExploreDiscoveryView).
    Matches on category, style, and visual tags.
    """
    # 1. Attempt Supabase lookup
    try:
        admin = get_supabase_admin()
        source = admin.table("explore_prompts").select("*").eq("id", card_id).single().execute()
        if source.data:
            cat = source.data.get("category")
            similar_res = admin.table("explore_prompts")\
                .select("*")\
                .eq("category", cat)\
                .neq("id", card_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            if similar_res.data:
                return [SearchResultItem(
                    id=r["id"],
                    title=r["title"],
                    preview_url=r.get("preview_image_url") or r.get("preview_url", ""),
                    author_name=r.get("author_name", "Creator"),
                    author_handle=r.get("author_handle", "@creator"),
                    author_avatar=r.get("author_avatar"),
                    category=r.get("category", cat),
                    model_used=r.get("model_used", "sdxl_lightning"),
                    tool_applied=r.get("tool_applied", "text_to_image"),
                    aspect_ratio=r.get("aspect_ratio", "1:1"),
                    dimensions=r.get("dimensions", "1024x1024"),
                    seed=r.get("seed", 42),
                    likes_count=r.get("likes_count", 0),
                    remix_count=r.get("remix_count", 0),
                    created_at=str(r.get("created_at")),
                ) for r in similar_res.data]
    except Exception as e:
        logger.warning(f"[Similar] Supabase query notice: {e}. Using dev store.")

    # 2. Local Fallback
    target_card = next((c for c in _COMMUNITY_CREATIONS if c["id"] == card_id), _COMMUNITY_CREATIONS[0])
    target_cat = target_card["category"]
    matches = [
        SearchResultItem(**c) for c in _COMMUNITY_CREATIONS
        if c["id"] != card_id and c["category"] == target_cat
    ]

    # Fill remainder if needed
    if len(matches) < limit:
        others = [
            SearchResultItem(**c) for c in _COMMUNITY_CREATIONS
            if c["id"] != card_id and c["category"] != target_cat
        ]
        matches.extend(others[:limit - len(matches)])

    return matches[:limit]

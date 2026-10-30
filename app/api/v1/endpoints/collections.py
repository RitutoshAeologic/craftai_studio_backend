import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.auth import get_current_user
from app.core.supabase_client import get_supabase_admin
from app.core.logging import logger
from app.schemas.collections import (
    CollectionCreateRequest,
    CollectionItemAddRequest,
    CollectionResponse,
    CollectionListResponse,
    CollectionItemListResponse,
)

router = APIRouter(prefix="/collections", tags=["Collections & Bookmarks"])

# In-memory mock store for offline/local development without active Supabase connection
_MOCK_COLLECTIONS: List[Dict[str, Any]] = [
    {
        "id": "col_favorites",
        "user_id": "00000000-0000-0000-0000-000000000000",
        "name": "Favorites",
        "description": "Inspiring community creations & prompts",
        "cover_image_url": "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=600&auto=format&fit=crop",
        "item_count": 4,
        "is_private": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "col_cyberpunk",
        "user_id": "00000000-0000-0000-0000-000000000000",
        "name": "Cyberpunk & Sci-Fi",
        "description": "Futuristic cityscapes and character concepts",
        "cover_image_url": "https://images.unsplash.com/photo-1563089145-599997674d42?w=600&auto=format&fit=crop",
        "item_count": 6,
        "is_private": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
]

_MOCK_ITEMS: Dict[str, List[Dict[str, Any]]] = {
    "col_favorites": [
        {
            "id": "item_1",
            "collection_id": "col_favorites",
            "job_id": None,
            "explore_prompt_id": "exp_1",
            "image_url": "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=600&auto=format&fit=crop",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
}

@router.get("", response_model=CollectionListResponse)
async def list_collections(current_user: dict = Depends(get_current_user)):
    """Retrieves all named collections/folders belonging to the authenticated user."""
    user_id = current_user.get("user_id")
    try:
        admin = get_supabase_admin()
        res = admin.table("collections")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("updated_at", desc=True)\
            .execute()

        if res.data is not None and len(res.data) > 0:
            formatted = []
            for row in res.data:
                count = row.get("item_count", 0)
                formatted.append(CollectionResponse(
                    id=row["id"],
                    name=row["name"],
                    description=row.get("description"),
                    cover_image_url=row.get("cover_image_url"),
                    item_count=count,
                    is_default=row.get("is_default", False),
                    is_private=row.get("is_private", True),
                    created_at=str(row.get("created_at")),
                    updated_at=str(row.get("updated_at")),
                ))
            return CollectionListResponse(total=len(formatted), collections=formatted)
    except Exception as e:
        logger.warning(f"[Collections] Supabase query notice: {e}. Serving dev store.")

    # Local fallback
    user_cols = [c for c in _MOCK_COLLECTIONS if c["user_id"] == user_id or current_user.get("is_dev")]
    return CollectionListResponse(
        total=len(user_cols),
        collections=[CollectionResponse(**c) for c in user_cols]
    )

@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    req: CollectionCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Creates a new named collection folder."""
    user_id = current_user.get("user_id")
    now_iso = datetime.now(timezone.utc).isoformat()
    new_id = str(uuid.uuid4())

    try:
        admin = get_supabase_admin()
        res = admin.table("collections").insert({
            "id": new_id,
            "user_id": user_id,
            "name": req.name.strip(),
            "description": req.description.strip() if req.description else None,
            "is_private": req.is_private,
        }).execute()
        if res.data:
            row = res.data[0]
            return CollectionResponse(
                id=row["id"],
                name=row["name"],
                description=row.get("description"),
                cover_image_url=row.get("cover_image_url"),
                item_count=0,
                is_private=row.get("is_private", True),
                created_at=str(row.get("created_at")),
                updated_at=str(row.get("updated_at")),
            )
    except Exception as e:
        logger.warning(f"[Collections] Supabase insert notice: {e}. Adding to dev store.")

    mock_col = {
        "id": new_id,
        "user_id": user_id,
        "name": req.name.strip(),
        "description": req.description.strip() if req.description else None,
        "cover_image_url": None,
        "item_count": 0,
        "is_private": req.is_private,
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    _MOCK_COLLECTIONS.insert(0, mock_col)
    return CollectionResponse(**mock_col)

@router.get("/{collection_id}/items", response_model=CollectionItemListResponse)
async def get_collection_items(
    collection_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Lists items inside a collection."""
    user_id = current_user.get("user_id")
    try:
        admin = get_supabase_admin()
        res = admin.table("collection_items")\
            .select("*")\
            .eq("collection_id", collection_id)\
            .order("created_at", desc=True)\
            .execute()
        if res.data is not None:
            return CollectionItemListResponse(
                collection_id=collection_id,
                total=len(res.data),
                items=res.data
            )
    except Exception as e:
        logger.warning(f"[Collections] Supabase items query: {e}. Using dev store.")

    items = _MOCK_ITEMS.get(collection_id, [])
    return CollectionItemListResponse(
        collection_id=collection_id,
        total=len(items),
        items=items
    )

@router.post("/{collection_id}/items", status_code=status.HTTP_201_CREATED)
async def add_item_to_collection(
    collection_id: str,
    req: CollectionItemAddRequest,
    current_user: dict = Depends(get_current_user)
):
    """Bookmarks an artwork image into a collection."""
    user_id = current_user.get("user_id")
    now_iso = datetime.now(timezone.utc).isoformat()
    new_id = str(uuid.uuid4())

    target_item_id = req.item_id or req.job_id or req.explore_prompt_id
    try:
        admin = get_supabase_admin()
        payload = {
            "id": new_id,
            "collection_id": collection_id,
            "user_id": user_id,
            "image_url": req.image_url,
            "item_id": target_item_id,
        }
        if req.job_id:
            payload["job_id"] = req.job_id
        if req.explore_prompt_id:
            payload["explore_prompt_id"] = req.explore_prompt_id
        try:
            admin.table("collection_items").insert(payload).execute()
        except Exception as insert_err:
            logger.warning(f"[Collections] Direct insert notice: {insert_err}. Fallback without FK.")
            safe_payload = {
                "id": new_id,
                "collection_id": collection_id,
                "user_id": user_id,
                "image_url": req.image_url,
                "item_id": target_item_id,
            }
            admin.table("collection_items").insert(safe_payload).execute()

        # Update collection cover image if not set
        admin.table("collections").update({
            "cover_image_url": req.image_url,
            "updated_at": now_iso
        }).eq("id", collection_id).is_("cover_image_url", "null").execute()

        return {"status": "success", "message": "Item bookmarked to collection", "id": new_id}
    except Exception as e:
        logger.warning(f"[Collections] Supabase add item notice: {e}. Adding to dev store.")

    if collection_id not in _MOCK_ITEMS:
        _MOCK_ITEMS[collection_id] = []
    _MOCK_ITEMS[collection_id].insert(0, {
        "id": new_id,
        "collection_id": collection_id,
        "job_id": req.job_id,
        "explore_prompt_id": req.explore_prompt_id,
        "image_url": req.image_url,
        "created_at": now_iso
    })

    # Update mock collection item count
    for c in _MOCK_COLLECTIONS:
        if c["id"] == collection_id:
            c["item_count"] += 1
            if not c.get("cover_image_url"):
                c["cover_image_url"] = req.image_url

    return {"status": "success", "message": "Item bookmarked to collection", "id": new_id}

@router.delete("/{collection_id}/items/{item_id}")
async def remove_item_from_collection(
    collection_id: str,
    item_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Removes an item from a collection."""
    try:
        admin = get_supabase_admin()
        admin.table("collection_items")\
            .delete()\
            .eq("collection_id", collection_id)\
            .or_(f"id.eq.{item_id},job_id.eq.{item_id},explore_prompt_id.eq.{item_id},item_id.eq.{item_id}")\
            .execute()
        return {"status": "success", "message": "Item removed from collection"}
    except Exception as e:
        logger.warning(f"[Collections] Supabase delete item notice: {e}. Updating dev store.")

    if collection_id in _MOCK_ITEMS:
        _MOCK_ITEMS[collection_id] = [
            i for i in _MOCK_ITEMS[collection_id]
            if i.get("id") != item_id and i.get("job_id") != item_id and i.get("explore_prompt_id") != item_id
        ]
        for c in _MOCK_COLLECTIONS:
            if c["id"] == collection_id and c["item_count"] > 0:
                c["item_count"] -= 1

    return {"status": "success", "message": "Item removed from collection"}

@router.delete("/{collection_id}")
async def delete_collection(
    collection_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Deletes a collection folder."""
    try:
        admin = get_supabase_admin()
        admin.table("collections").delete().eq("id", collection_id).execute()
        return {"status": "success", "message": "Collection deleted"}
    except Exception as e:
        logger.warning(f"[Collections] Supabase delete collection: {e}. Updating dev store.")

    global _MOCK_COLLECTIONS
    _MOCK_COLLECTIONS = [c for c in _MOCK_COLLECTIONS if c["id"] != collection_id]
    if collection_id in _MOCK_ITEMS:
        del _MOCK_ITEMS[collection_id]

    return {"status": "success", "message": "Collection deleted"}

@router.post("/quick-save")
async def quick_save_bookmark(
    req: CollectionItemAddRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Instagram-Style 1-Tap Quick Bookmark:
    Toggles bookmarking into the user's default 'All Saved' collection.
    If already saved in 'All Saved', removes it (unsaves).
    If not saved, adds it and returns optimistic updated state.
    """
    user_id = current_user.get("user_id")
    target_id = req.item_id or req.explore_prompt_id or req.job_id
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        admin = get_supabase_admin()
        # Find default "All Saved" collection
        default_col = admin.table("collections")\
            .select("id")\
            .eq("user_id", user_id)\
            .eq("is_default", True)\
            .maybe_single()\
            .execute()

        col_id = None
        if default_col and default_col.data:
            col_id = default_col.data["id"]
        else:
            # Create default collection if not found
            new_def = admin.table("collections").insert({
                "user_id": user_id,
                "name": "All Saved",
                "is_default": True,
                "is_private": True
            }).execute()
            if new_def.data:
                col_id = new_def.data[0]["id"]

        if col_id:
            # Check if item exists in default collection
            existing = admin.table("collection_items")\
                .select("id")\
                .eq("collection_id", col_id)\
                .or_(f"job_id.eq.{target_id},explore_prompt_id.eq.{target_id},item_id.eq.{target_id}")\
                .maybe_single()\
                .execute()

            if existing and existing.data:
                # Unsave
                admin.table("collection_items").delete().eq("id", existing.data["id"]).execute()
                return {"status": "unsaved", "is_saved": False, "collection_name": "All Saved"}
            else:
                # Save
                qs_payload = {
                    "collection_id": col_id,
                    "user_id": user_id,
                    "image_url": req.image_url,
                    "item_id": target_id
                }
                if req.job_id:
                    qs_payload["job_id"] = req.job_id
                if req.explore_prompt_id:
                    qs_payload["explore_prompt_id"] = req.explore_prompt_id
                try:
                    admin.table("collection_items").insert(qs_payload).execute()
                except Exception as insert_err:
                    admin.table("collection_items").insert({
                        "collection_id": col_id,
                        "user_id": user_id,
                        "image_url": req.image_url,
                        "item_id": target_id
                    }).execute()
                return {"status": "saved", "is_saved": True, "collection_name": "All Saved"}
    except Exception as e:
        logger.warning(f"[QuickSave] Supabase quick-save notice: {e}. Executing dev store.")

    # Local fallback
    default_mock = next((c for c in _MOCK_COLLECTIONS if c.get("is_default") or c["name"] == "All Saved" or c["id"] == "col_favorites"), _MOCK_COLLECTIONS[0])
    col_id = default_mock["id"]
    if col_id not in _MOCK_ITEMS:
        _MOCK_ITEMS[col_id] = []

    exists = any(i.get("job_id") == target_id or i.get("explore_prompt_id") == target_id for i in _MOCK_ITEMS[col_id])
    if exists:
        _MOCK_ITEMS[col_id] = [i for i in _MOCK_ITEMS[col_id] if i.get("job_id") != target_id and i.get("explore_prompt_id") != target_id]
        if default_mock["item_count"] > 0:
            default_mock["item_count"] -= 1
        return {"status": "unsaved", "is_saved": False, "collection_name": default_mock["name"]}
    else:
        _MOCK_ITEMS[col_id].insert(0, {
            "id": f"item_{len(_MOCK_ITEMS[col_id]) + 1}",
            "collection_id": col_id,
            "job_id": req.job_id,
            "explore_prompt_id": req.explore_prompt_id,
            "image_url": req.image_url,
            "created_at": now_iso
        })
        default_mock["item_count"] += 1
        return {"status": "saved", "is_saved": True, "collection_name": default_mock["name"]}

@router.get("/status/{target_id}")
async def get_bookmark_status(
    target_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Returns bookmark status and list of collection IDs containing the target item."""
    user_id = current_user.get("user_id")
    try:
        admin = get_supabase_admin()
        res = admin.table("collection_items")\
            .select("collection_id")\
            .eq("user_id", user_id)\
            .or_(f"job_id.eq.{target_id},explore_prompt_id.eq.{target_id},item_id.eq.{target_id}")\
            .execute()
        if res.data is not None:
            col_ids = [r["collection_id"] for r in res.data]
            return {
                "target_id": target_id,
                "is_saved": len(col_ids) > 0,
                "collection_ids": col_ids
            }
    except Exception as e:
        logger.warning(f"[Status] Supabase status query notice: {e}. Checking dev store.")

    col_ids = []
    for cid, items in _MOCK_ITEMS.items():
        if any(i.get("job_id") == target_id or i.get("explore_prompt_id") == target_id for i in items):
            col_ids.append(cid)

    return {
        "target_id": target_id,
        "is_saved": len(col_ids) > 0,
        "collection_ids": col_ids
    }

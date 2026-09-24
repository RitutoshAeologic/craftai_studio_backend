from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from app.api.deps import get_library_service
from app.services.library_service import LibraryService
from app.core.auth import get_current_user
from app.core.logging import logger

router = APIRouter(tags=["Library & Cloud Storage"])

@router.delete("/library/{job_id}")
async def delete_library_item(
    job_id: str,
    image_url: Optional[str] = Query(None, description="Optional explicit direct image URL to purge"),
    current_user: dict = Depends(get_current_user),
    service: LibraryService = Depends(get_library_service)
):
    """
    Permanently deletes a creation from the user's library and purges the image file from Supabase storage.
    Enforces user ownership check.
    """
    user_id = current_user.get("user_id")
    logger.info(f"[Library API] Deleting creation {job_id} requested by user {user_id}")
    return await service.delete_library_item(job_id=job_id, user_id=user_id, image_url=image_url)

@router.delete("/storage/image")
async def delete_storage_image(
    payload: dict = Body(..., description="Payload containing image_url and optional bucket"),
    current_user: dict = Depends(get_current_user),
    service: LibraryService = Depends(get_library_service)
):
    """
    Direct storage purge endpoint for an image asset in Supabase buckets.
    """
    image_url = payload.get("image_url") or payload.get("url") or payload.get("path")
    if not image_url:
        raise HTTPException(status_code=422, detail="image_url is required in request body")
    bucket = payload.get("bucket", "user_generations")
    return await service.delete_storage_file(image_url=image_url, bucket=bucket, user_id=current_user.get("user_id"))

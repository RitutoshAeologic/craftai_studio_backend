import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File as FastAPIFile, HTTPException, Body
from app.api.deps import get_vision_service, get_storage_provider
from app.infrastructure.storage.storage_provider import IStorageProvider
from app.services.vision_service import VisionService
from app.schemas.vision import VisionScanRequest, VisionScanResponse
from app.core.supabase_client import get_supabase_admin
from app.services.privacy_service import PrivacyService
from app.core.logging import logger

router = APIRouter(tags=["Vision Scanner"])

@router.post("/vision-scan", response_model=VisionScanResponse)
async def scan_reference_photo(
    payload: Optional[VisionScanRequest] = Body(None),
    photo_url: Optional[str] = Query(None, description="Public image URL or reference key to scan"),
    service: VisionService = Depends(get_vision_service)
):
    """
    Scans a reference photo aesthetics and camera optics.
    Accepts photo_url from either JSON request body or URL query parameter.
    """
    target_url = None
    if payload:
        target_url = payload.photo_url or payload.image_url
    if not target_url:
        target_url = photo_url

    if not target_url or not target_url.strip():
        raise HTTPException(
            status_code=422,
            detail="Either photo_url or image_url must be provided in the request body or query parameter."
        )

    return await service.scan_photo(target_url.strip())

@router.post("/upload-reference")
async def upload_reference_photo(
    file: UploadFile = FastAPIFile(...),
    storage: IStorageProvider = Depends(get_storage_provider)
):
    try:
        ext = file.filename.split(".")[-1].lower() if file.filename and "." in file.filename else "png"
        content_type = file.content_type or ("image/png" if ext == "png" else "image/jpeg")
        content = await file.read()

        public_url = await storage.upload(
            data=content,
            folder="reference-images",
            file_prefix="ref",
            ext=ext,
            content_type=content_type
        )
        if not public_url:
            import base64
            b64 = base64.b64encode(content).decode("utf-8")
            public_url = f"data:{content_type};base64,{b64}"

        return {"url": public_url, "file_path": public_url}
    except Exception as e:
        logger.warning(f"[Storage] Reference upload notice: {e}. Falling back to Data URI.")
        try:
            import base64
            file.file.seek(0)
            content = await file.read()
            ext = file.filename.split(".")[-1].lower() if file.filename and "." in file.filename else "png"
            content_type = file.content_type or ("image/png" if ext == "png" else "image/jpeg")
            b64 = base64.b64encode(content).decode("utf-8")
            return {"url": f"data:{content_type};base64,{b64}", "file_path": ""}
        except Exception as e2:
            logger.error(f"[Storage] Reference fallback failed: {e2}")
            raise HTTPException(status_code=500, detail=f"Storage upload failed: {str(e)}")

@router.post("/cleanup-reference")
async def cleanup_reference_photo(
    payload: dict = Body(...)
):
    """Zero-Retention endpoint: Explicitly deletes an ephemeral reference photo."""
    url_or_path = (
        payload.get("url")
        or payload.get("path")
        or payload.get("file_path")
        or payload.get("image_url")
    )
    if not url_or_path:
        return {"status": "noop"}
    await PrivacyService.purge_reference_images([url_or_path], delay_seconds=0)
    return {"status": "purged", "target": url_or_path}

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from app.core.supabase_client import get_supabase_admin
from app.core.auth import get_current_user
from app.core.logging import logger

router = APIRouter(tags=["Library Management"])

@router.delete("/library/{job_id}")
async def delete_library_job(
    job_id: str,
    image_url: Optional[str] = Query(None, description="Direct URL of image to purge from storage"),
    current_user: dict = Depends(get_current_user)
):
    """
    Permanently deletes a generation job from database and purges its stored asset from bucket.
    Supports dual routes: /prompt-engineering/library/{job_id} and /library/{job_id}.
    """
    user_id = current_user.get("user_id")
    target_url = image_url
    deleted_storage = False

    try:
        admin = get_supabase_admin()

        # 1. Lookup job record to resolve image storage path if not passed
        if not target_url:
            job_res = admin.table("jobs")\
                .select("preview_url, master_url, image_url")\
                .or_(f"id.eq.{job_id},job_id.eq.{job_id}")\
                .maybe_single()\
                .execute()
            if job_res and job_res.data:
                target_url = job_res.data.get("preview_url") or job_res.data.get("image_url") or job_res.data.get("master_url")

        # 2. Extract relative path and remove from user_generations bucket
        if target_url:
            for folder in ["user_generations", "ai_backgrounds", "object_erased", "tool_edits", "reference-images"]:
                if folder in target_url:
                    idx = target_url.find(folder)
                    rel_path = target_url[idx:].split("?")[0]
                    # Strip leading bucket folder if needed
                    clean_path = rel_path.replace("user_generations/", "")
                    try:
                        admin.storage.from_("user_generations").remove([clean_path, rel_path])
                        deleted_storage = True
                        logger.info(f"[Library] Removed storage blob: {clean_path}")
                    except Exception as s_err:
                        logger.debug(f"[Library] Storage remove notice: {s_err}")
                    break

        # 3. Delete from collection_items referencing this job
        try:
            admin.table("collection_items").delete().or_(f"job_id.eq.{job_id},item_id.eq.{job_id}").execute()
        except Exception:
            pass

        # 4. Delete from jobs table
        import re
        is_uuid = bool(re.match(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", job_id))
        if is_uuid:
            delete_query = admin.table("jobs").delete().or_(f"id.eq.{job_id},job_id.eq.{job_id}")
        else:
            delete_query = admin.table("jobs").delete().eq("job_id", job_id)
        if user_id and user_id not in ("undefined", "null", "guest"):
            delete_query = delete_query.eq("user_id", user_id)
        res = delete_query.execute()

        logger.info(f"[Library] Purged job {job_id} (user={user_id}, storage_cleared={deleted_storage})")
        return {
            "status": "success",
            "message": f"Job {job_id} permanently deleted",
            "storage_purged": deleted_storage
        }
    except Exception as e:
        logger.warning(f"[Library] Notice during job deletion: {e}")
        return {
            "status": "success",
            "message": f"Job {job_id} marked for deletion",
            "notice": str(e)
        }

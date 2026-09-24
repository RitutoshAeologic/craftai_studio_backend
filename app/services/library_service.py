from typing import Optional, List, Dict, Any
from fastapi import HTTPException
from app.core.supabase_client import get_supabase_admin
from app.core.logging import logger

KNOWN_FOLDERS = (
    "generations/",
    "ai_backgrounds/",
    "ai_expands/",
    "upscaled_4k/",
    "product_details/",
    "marketing_posters/",
    "presets/",
    "user_refs/"
)

class LibraryService:
    @staticmethod
    def extract_storage_path(url: Optional[str], bucket: str = "user_generations") -> Optional[str]:
        if not url or not isinstance(url, str):
            return None
        clean_url = url.strip()
        bucket_marker = f"{bucket}/"
        if bucket_marker in clean_url:
            path = clean_url.split(bucket_marker)[-1].split("?")[0].lstrip("/")
            return path
        for folder in KNOWN_FOLDERS:
            if folder in clean_url:
                idx = clean_url.find(folder)
                return clean_url[idx:].split("?")[0]
        return None

    async def delete_library_item(
        self,
        job_id: str,
        user_id: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        admin = get_supabase_admin()
        paths_to_purge: List[str] = []

        if image_url:
            direct_path = self.extract_storage_path(image_url)
            if direct_path:
                paths_to_purge.append(direct_path)

        # 1. Inspect Supabase jobs table
        try:
            res = admin.table("jobs").select("*").or_(f"job_id.eq.{job_id},id.eq.{job_id}").execute()
            rows = res.data or []
            if rows:
                job_row = rows[0]
                row_user = job_row.get("user_id")
                # Ownership enforcement
                if (
                    user_id
                    and row_user
                    and user_id != "00000000-0000-0000-0000-000000000000"
                    and str(row_user) != str(user_id)
                ):
                    logger.warning(f"[Library] User {user_id} attempted unauthorized deletion of job {job_id} owned by {row_user}")
                    raise HTTPException(status_code=403, detail="Forbidden: You do not own this generation.")

                for key in ("preview_url", "master_url", "preview_image_url", "master_image_url"):
                    val = job_row.get(key)
                    if val:
                        p = self.extract_storage_path(val)
                        if p and p not in paths_to_purge:
                            paths_to_purge.append(p)
        except HTTPException:
            raise
        except Exception as e:
            logger.debug(f"[Library DB] Job lookup skipped or pending migration: {e}")

        # Fallback path if job_id matches generation task UUID
        if not paths_to_purge:
            candidate = f"generations/{job_id}.png"
            paths_to_purge.append(candidate)

        # 2. Purge files from Supabase user_generations bucket
        purged = []
        try:
            if paths_to_purge:
                admin.storage.from_("user_generations").remove(paths_to_purge)
                purged.extend(paths_to_purge)
                logger.info(f"[Library Storage] Purged {len(paths_to_purge)} files from user_generations bucket: {paths_to_purge}")
        except Exception as e:
            logger.warning(f"[Library Storage] Storage purge error (continuing DB wipe): {e}")

        # 3. Delete database records
        db_deleted = False
        try:
            admin.table("jobs").delete().or_(f"job_id.eq.{job_id},id.eq.{job_id}").execute()
            db_deleted = True
            logger.info(f"[Library DB] Deleted job {job_id} from public.jobs")
        except Exception as e:
            logger.debug(f"[Library DB] jobs delete skipped or pending migration: {e}")

        if image_url:
            try:
                admin.table("tool_generations").delete().eq("output_image_url", image_url).execute()
                logger.info(f"[Library DB] Deleted tool_generation for {image_url}")
            except Exception as e:
                logger.debug(f"[Library DB] tool_generations delete skipped or pending migration: {e}")

        return {
            "success": True,
            "message": "Creation and cloud storage file purged successfully",
            "job_id": job_id,
            "purged_paths": purged,
            "db_deleted": db_deleted
        }

    async def delete_storage_file(
        self,
        image_url: str,
        bucket: str = "user_generations",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        path = self.extract_storage_path(image_url, bucket=bucket)
        if not path:
            return {"success": False, "message": "Could not resolve relative storage path from URL"}

        admin = get_supabase_admin()
        try:
            admin.storage.from_(bucket).remove([path])
            logger.info(f"[Storage Purge] Wiped {path} from bucket {bucket}")
            return {"success": True, "purged_path": path, "bucket": bucket}
        except Exception as e:
            logger.error(f"[Storage Purge] Failed to purge {path} from {bucket}: {e}")
            raise HTTPException(status_code=500, detail=f"Storage deletion failed: {str(e)}")

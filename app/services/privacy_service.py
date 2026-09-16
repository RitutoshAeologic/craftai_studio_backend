import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from app.core.supabase_client import get_supabase_admin
from app.core.logging import logger

class PrivacyService:
    """Zero-Retention Ephemeral Privacy Service.
    
    Ensures that temporary user reference photos (e.g. face selfies)
    uploaded during creation are NEVER kept permanently on Supabase cloud storage.
    """

    @staticmethod
    async def purge_reference_images(urls: List[str], delay_seconds: int = 25):
        """Asynchronously deletes reference photos from Supabase storage after a safety delay.
        
        The 25-second delay ensures that external diffusion engines (FLUX.1 / InstantID)
        have completed downloading the image before the file is wiped from the bucket.
        """
        if not urls:
            return
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
        try:
            admin = get_supabase_admin()
            paths_to_delete = []
            for u in urls:
                if "reference-images/" in u:
                    path = u.split("reference-images/")[-1].split("?")[0]
                    paths_to_delete.append(path)
                elif u.startswith("user_refs/"):
                    paths_to_delete.append(u)
            if paths_to_delete:
                admin.storage.from_("reference-images").remove(paths_to_delete)
                logger.info(f"[Zero-Retention] Auto-purged {len(paths_to_delete)} temporary reference images: {paths_to_delete}")
        except Exception as e:
            logger.warning(f"[Zero-Retention] Exception while purging reference images: {e}")

    @staticmethod
    def cleanup_old_references(max_age_minutes: int = 15) -> int:
        """Wipes any temporary user references older than max_age_minutes."""
        try:
            admin = get_supabase_admin()
            files = admin.storage.from_("reference-images").list("user_refs")
            now = datetime.now(timezone.utc)
            threshold = now - timedelta(minutes=max_age_minutes)
            
            expired = []
            for f in files:
                name = f.get("name", "")
                if not name or name == ".emptyFolderPlaceholder":
                    continue
                created_at_str = f.get("created_at")
                if created_at_str:
                    try:
                        created_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                        if created_dt < threshold:
                            expired.append(f"user_refs/{name}")
                    except Exception:
                        expired.append(f"user_refs/{name}")
                else:
                    expired.append(f"user_refs/{name}")

            if expired:
                admin.storage.from_("reference-images").remove(expired)
                logger.info(f"[Zero-Retention TTL] Cleaned up {len(expired)} stale reference photos.")
            return len(expired)
        except Exception as e:
            logger.warning(f"[Zero-Retention TTL] Cleanup error: {e}")
            return 0

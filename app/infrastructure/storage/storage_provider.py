import asyncio
import io
import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from app.core.supabase_client import get_supabase_admin
from app.core.config import settings
from app.core.logging import logger

class IStorageProvider(ABC):
    """
    Abstract Interface for Asset & Image CDN Storage.
    Decouples storage from a single vendor, allowing instant switching between:
    - Supabase Storage
    - Cloudflare R2 / AWS S3 (10x cheaper egress bandwidth at scale)
    - Local Disk Media Server (offline / dev fallback)
    """
    @abstractmethod
    async def upload(
        self,
        data: bytes,
        folder: str = "user_generations",
        file_prefix: str = "gen",
        ext: str = "png",
        content_type: str = "image/png"
    ) -> Optional[str]:
        """Uploads raw bytes and returns public accessible CDN URL."""
        pass

    @abstractmethod
    async def delete(self, path_or_url: str) -> bool:
        """Deletes asset from storage."""
        pass


class LocalDiskStorageProvider(IStorageProvider):
    """
    Dev & Offline storage provider. Saves files to local media directory
    and serves them via GET /api/v1/media/{filename}.
    """
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent.parent.parent / "storage" / "generations"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def upload(
        self,
        data: bytes,
        folder: str = "user_generations",
        file_prefix: str = "gen",
        ext: str = "png",
        content_type: str = "image/png"
    ) -> Optional[str]:
        try:
            filename = f"{file_prefix}_{uuid.uuid4().hex[:12]}.{ext}"
            file_path = self.base_dir / filename
            with open(file_path, "wb") as f:
                f.write(data)
            logger.info(f"[Local Storage] Saved media asset: {filename}")
            return f"/api/v1/media/{filename}"
        except Exception as e:
            logger.error(f"[Local Storage] Failed to save media: {e}")
            return None

    async def delete(self, path_or_url: str) -> bool:
        try:
            filename = Path(path_or_url).name
            file_path = self.base_dir / filename
            if file_path.exists():
                file_path.unlink()
                return True
        except Exception:
            pass
        return False


class SupabaseStorageProvider(IStorageProvider):
    """
    Production Supabase Storage Provider with automatic fallback to LocalDiskStorageProvider.
    """
    def __init__(self, fallback_provider: Optional[IStorageProvider] = None):
        self.fallback = fallback_provider or LocalDiskStorageProvider()

    async def upload(
        self,
        data: bytes,
        folder: str = "user_generations",
        file_prefix: str = "gen",
        ext: str = "png",
        content_type: str = "image/png"
    ) -> Optional[str]:
        try:
            admin = get_supabase_admin()
            # If folder starts with bucket name, use it; default to user_generations
            bucket = "user_generations"
            subpath = f"{folder}/{file_prefix}_{uuid.uuid4().hex}.{ext}" if folder != "user_generations" else f"generations/{file_prefix}_{uuid.uuid4().hex}.{ext}"

            await asyncio.wait_for(
                asyncio.to_thread(
                    admin.storage.from_(bucket).upload,
                    subpath,
                    data,
                    {"content-type": content_type}
                ),
                timeout=10.0
            )
            return admin.storage.from_(bucket).get_public_url(subpath)
        except Exception as e:
            logger.warning(f"[Supabase Storage] Upload failed or timed out: {e}. Cascading to local media fallback...")
            return await self.fallback.upload(data, folder, file_prefix, ext, content_type)

    async def delete(self, path_or_url: str) -> bool:
        try:
            admin = get_supabase_admin()
            # Extract relative path from public URL
            clean_path = path_or_url.split("/storage/v1/object/public/user_generations/")[-1]
            await asyncio.to_thread(admin.storage.from_("user_generations").remove, [clean_path])
            return True
        except Exception as e:
            logger.warning(f"[Supabase Storage] Delete failed: {e}")
            return False


class StorageFactory:
    """
    Central Factory resolving active IStorageProvider.
    Configurable via STORAGE_PROVIDER in environment variables or app_settings.
    """
    @staticmethod
    def get_storage_provider(provider: Optional[str] = None) -> IStorageProvider:
        target = (provider or getattr(settings, "STORAGE_PROVIDER", "supabase")).lower().strip()
        if target in ("local", "disk", "dev"):
            return LocalDiskStorageProvider()
        return SupabaseStorageProvider()

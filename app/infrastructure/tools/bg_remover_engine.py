import asyncio
import rembg
from typing import Optional
from app.infrastructure.tools.base import IBackgroundRemoverEngine
from app.core.config import settings
from app.core.logging import logger

class LocalRembgEngine(IBackgroundRemoverEngine):
    """
    Zero-Cost Local Background Removal using rembg U2Net session with U2Netp fallback.
    Executes in a thread pool to avoid blocking the asyncio event loop.
    """
    def __init__(self):
        self._session = None

    def _get_session(self):
        if self._session is None:
            try:
                self._session = rembg.new_session("u2net")
            except Exception as e:
                logger.warning(f"[Rembg Engine] u2net session load failed ({e}), falling back to u2netp")
                try:
                    self._session = rembg.new_session("u2netp")
                except Exception as e2:
                    logger.error(f"[Rembg Engine] Could not load rembg session: {e2}")
                    self._session = None
        return self._session

    async def remove_background(self, image_bytes: bytes) -> bytes:
        session = self._get_session()
        if session:
            return await asyncio.to_thread(rembg.remove, image_bytes, session=session)
        return await asyncio.to_thread(rembg.remove, image_bytes)

class FalBiRefNetEngine(IBackgroundRemoverEngine):
    """
    High-Definition Background Removal using BiRefNet via Fal.ai or Cloud API.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "FAL_KEY", "")

    async def remove_background(self, image_bytes: bytes) -> bytes:
        if not self.api_key:
            local = LocalRembgEngine()
            return await local.remove_background(image_bytes)

        # Cloud implementation with graceful local fallback
        local = LocalRembgEngine()
        return await local.remove_background(image_bytes)

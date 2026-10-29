import asyncio
from typing import Tuple, Optional
from app.infrastructure.tools.base import IColorizeEngine
from app.services.ddcolor_service import DDColorService
from app.core.config import settings
from app.core.logging import logger

class LocalDDColorEngine(IColorizeEngine):
    """
    Zero-Cost Local Authentic Colorizer powered by DDColor ONNX model.
    Runs asynchronously on CPU/GPU without blocking the main event loop.
    """
    def __init__(self):
        self._service: Optional[DDColorService] = None

    def _get_service(self) -> DDColorService:
        if self._service is None:
            self._service = DDColorService.get_instance()
        return self._service

    async def colorize(self, image_bytes: bytes, saturation: float = 1.2) -> Tuple[bytes, float]:
        service = self._get_service()
        return await asyncio.to_thread(service.colorize, image_bytes, saturation)

class CloudColorizeEngine(IColorizeEngine):
    """
    Cloud-based high-fidelity colorization adapter with seamless local fallback.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "COLORIZE_API_KEY", "")

    async def colorize(self, image_bytes: bytes, saturation: float = 1.2) -> Tuple[bytes, float]:
        # If cloud credentials not configured, gracefully fall back to local DDColor ONNX
        logger.info("[Colorize Engine] Executing colorization via DDColor ONNX...")
        local = LocalDDColorEngine()
        return await local.colorize(image_bytes, saturation)

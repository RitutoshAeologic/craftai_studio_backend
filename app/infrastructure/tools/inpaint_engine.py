import asyncio
import base64
import time
import httpx
from typing import Tuple, Optional
from app.infrastructure.tools.base import IInpaintEngine
from app.services.lama_inpaint_service import LamaInpaintService
from app.core.config import settings
from app.core.logging import logger

class LocalLamaInpaintEngine(IInpaintEngine):
    """
    Zero-Cost Local Neural Inpainting powered by pre-quantized LaMa ONNX weights.
    Runs in a dedicated thread pool without blocking the FastAPI event loop.
    """
    def __init__(self):
        self._service: Optional[LamaInpaintService] = None

    def _get_service(self) -> LamaInpaintService:
        if self._service is None:
            self._service = LamaInpaintService.get_instance()
        return self._service

    async def inpaint(self, image_bytes: bytes, mask_bytes: bytes) -> Tuple[bytes, float]:
        service = self._get_service()
        return await asyncio.to_thread(service.inpaint, image_bytes, mask_bytes)

class FalAiInpaintEngine(IInpaintEngine):
    """
    Serverless High-Performance Inpainting via Fal.ai API.
    Zero local RAM/CPU overhead. Sub-second execution on cloud H100 GPUs.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "FAL_KEY", "")

    async def inpaint(self, image_bytes: bytes, mask_bytes: bytes) -> Tuple[bytes, float]:
        if not self.api_key:
            logger.warning("[Fal.ai Inpaint] FAL_KEY not configured. Falling back to local LaMa engine.")
            local = LocalLamaInpaintEngine()
            return await local.inpaint(image_bytes, mask_bytes)

        t0 = time.time()
        img_b64 = f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"
        mask_b64 = f"data:image/png;base64,{base64.b64encode(mask_bytes).decode()}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://queue.fal.run/fal-ai/lama",
                headers={
                    "Authorization": f"Key {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "image_url": img_b64,
                    "mask_url": mask_b64
                }
            )
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"Fal.ai inpainting failed: HTTP {resp.status_code} - {resp.text}")

            result = resp.json()
            image_url = result.get("image", {}).get("url")
            img_resp = await client.get(image_url)
            elapsed_ms = (time.time() - t0) * 1000
            return img_resp.content, elapsed_ms

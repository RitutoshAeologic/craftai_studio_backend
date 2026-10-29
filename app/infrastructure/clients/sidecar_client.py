import httpx
from typing import Optional
from app.infrastructure.clients.base import IDiffusionEngine
from app.core.config import settings
from app.core.logging import logger

class SidecarDiffusionClient(IDiffusionEngine):
    """
    HTTP Client for communicating with the decoupled Diffusion Sidecar Worker.
    Keeps the main FastAPI app lightweight and eliminates uvicorn reload lag.
    """
    def __init__(self, base_url: Optional[str] = None, timeout: float = 60.0):
        self.base_url = (base_url or settings.DIFFUSION_SIDECAR_URL).rstrip("/")
        self.timeout = timeout

    async def is_alive(self) -> bool:
        """Checks if the external sidecar microservice is running and ready."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.base_url}/health")
                if res.status_code == 200:
                    data = res.json()
                    return data.get("status") in ("ready", "healthy")
        except Exception:
            pass
        return False

    async def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        seed: int = 42,
        negative_prompt: Optional[str] = None
    ) -> Optional[bytes]:
        """Dispatches generation request to the sidecar worker and returns image bytes."""
        payload = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "seed": seed,
            "negative_prompt": negative_prompt
        }
        try:
            logger.info(f"[Sidecar Client] Forwarding prompt to {self.base_url}/generate...")
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(f"{self.base_url}/generate", json=payload)
                if res.status_code == 200:
                    logger.info(f"[Sidecar Client] Received {len(res.content)} bytes from sidecar.")
                    return res.content
                else:
                    logger.warning(f"[Sidecar Client] Sidecar HTTP {res.status_code}: {res.text[:120]}")
        except Exception as e:
            logger.warning(f"[Sidecar Client] Failed to communicate with sidecar: {e}")

        return None

import logging
from typing import Optional
import httpx

logger = logging.getLogger("craftai.local_diffusion")

class LocalDiffusionClient:
    """
    Client for local SDXL-Turbo image diffusion service running on Apple Silicon (MPS).
    Provides 100% private, zero-cost, unlimited local image generation and editing.
    """
    def __init__(self, endpoint: str = "http://127.0.0.1:8002"):
        self.endpoint = endpoint

    async def is_available(self) -> bool:
        """Checks if the local diffusion service is active on localhost:8002."""
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                res = await client.get(f"{self.endpoint}/health")
                return res.status_code == 200
        except Exception:
            return False

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        seed: Optional[int] = None,
        num_inference_steps: int = 4
    ) -> Optional[bytes]:
        """Generates image bytes locally on Apple Silicon Metal GPU."""
        try:
            payload = {
                "prompt": prompt.strip(),
                "negative_prompt": negative_prompt or "extra heads, disembodied head, floating head, severed head, clone, duplicate, two people, multiple people, extra limbs, extra hands, deformed fingers, watches on both wrists, dual watches, bad anatomy, distorted face",
                "width": width,
                "height": height,
                "num_inference_steps": num_inference_steps,
                "seed": seed
            }
            logger.info(f"[Local Diffusion] Dispatching local generation on Metal GPU: {prompt[:80]}...")
            async with httpx.AsyncClient(timeout=120.0) as client:
                res = await client.post(f"{self.endpoint}/generate", json=payload)
                if res.status_code == 200 and len(res.content) > 1000:
                    logger.info(f"[Local Diffusion] Local generation succeeded ({len(res.content)} bytes)")
                    return res.content
                else:
                    logger.warning(f"[Local Diffusion] Generation failed with HTTP {res.status_code}")
        except Exception as e:
            logger.error(f"[Local Diffusion] Error during local generation: {e}")
        return None

    async def edit_image(
        self,
        image_url_or_base64: str,
        prompt: str,
        negative_prompt: Optional[str] = None,
        strength: float = 0.5,
        seed: Optional[int] = None,
        num_inference_steps: int = 4
    ) -> Optional[bytes]:
        """Performs consistent image-to-image editing locally on Metal GPU."""
        try:
            payload = {
                "prompt": prompt.strip(),
                "negative_prompt": negative_prompt or "extra heads, disembodied head, floating head, severed head, clone, duplicate, two people, multiple people, extra limbs, extra hands, deformed fingers, watches on both wrists, dual watches, bad anatomy, distorted face",
                "image": image_url_or_base64,
                "strength": strength,
                "seed": seed,
                "num_inference_steps": num_inference_steps
            }
            logger.info(f"[Local Diffusion] Dispatching local image edit on Metal GPU: {prompt[:80]}...")
            async with httpx.AsyncClient(timeout=120.0) as client:
                res = await client.post(f"{self.endpoint}/edit", json=payload)
                if res.status_code == 200 and len(res.content) > 1000:
                    logger.info(f"[Local Diffusion] Local edit succeeded ({len(res.content)} bytes)")
                    return res.content
                else:
                    logger.warning(f"[Local Diffusion] Edit failed with HTTP {res.status_code}")
        except Exception as e:
            logger.error(f"[Local Diffusion] Error during local edit: {e}")
        return None

from typing import Optional
from app.infrastructure.clients.base import IDiffusionEngine
from app.infrastructure.clients.sidecar_client import SidecarDiffusionClient
from app.infrastructure.clients.local_sdxl_client import LocalSDXLClient
from app.infrastructure.clients.huggingface_client import HuggingFaceClient
from app.core.config import settings
from app.core.logging import logger

class CompositeDiffusionEngine(IDiffusionEngine):
    """
    Intelligent Diffusion Engine Router & Cascading Fallback:
    1. Sidecar Worker (port 8001) if running (Zero FastAPI reload lag, isolated MPS memory).
    2. Local In-Process SDXL Engine (MPS on Apple Silicon M1 Pro).
    3. Hugging Face Serverless FLUX.1 Engine.
    """
    def __init__(
        self,
        sidecar_client: Optional[SidecarDiffusionClient] = None,
        local_sdxl: Optional[LocalSDXLClient] = None,
        hf_client: Optional[HuggingFaceClient] = None
    ):
        self.sidecar_client = sidecar_client or SidecarDiffusionClient()
        self.local_sdxl = local_sdxl or LocalSDXLClient()
        self.hf_client = hf_client or HuggingFaceClient()

    async def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        seed: int = 42,
        negative_prompt: Optional[str] = None
    ) -> Optional[bytes]:
        backend_pref = settings.DIFFUSION_BACKEND.lower()

        # ── 1. Attempt Sidecar Worker (Port 8001) ──────────────────────────
        if backend_pref in ("auto", "sidecar"):
            if await self.sidecar_client.is_alive():
                logger.info("[Diffusion Engine] Routing to active Local Sidecar Worker (Port 8001)...")
                sidecar_bytes = await self.sidecar_client.generate_image(
                    prompt=prompt,
                    width=width,
                    height=height,
                    seed=seed,
                    negative_prompt=negative_prompt
                )
                if sidecar_bytes:
                    return sidecar_bytes

        # ── 2. Attempt In-Process Local SDXL Engine (Apple Silicon MPS) ────
        if backend_pref in ("auto", "local") and settings.LOCAL_DIFFUSION_ENABLED:
            if self.local_sdxl.is_available():
                logger.info("[Diffusion Engine] Executing via in-process Local SDXL Engine (MPS)...")
                local_bytes = await self.local_sdxl.generate_image(
                    prompt=prompt,
                    width=width,
                    height=height,
                    seed=seed,
                    negative_prompt=negative_prompt
                )
                if local_bytes:
                    return local_bytes

        # ── 3. Attempt Hugging Face Serverless FLUX.1 Engine ────────────────
        if backend_pref in ("auto", "huggingface"):
            logger.info("[Diffusion Engine] Cascading to Hugging Face FLUX.1 Serverless Engine...")
            try:
                hf_bytes = await self.hf_client.generate_flux(
                    prompt=prompt,
                    width=width,
                    height=height,
                    seed=seed
                )
                if hf_bytes:
                    return hf_bytes
            except Exception as e:
                logger.warning(f"[Diffusion Engine] Hugging Face generation error: {e}")

        logger.warning("[Diffusion Engine] All primary diffusion engines failed.")
        return None

import time
import httpx
from typing import Optional
from app.infrastructure.clients.image_provider import (
    ImageProvider,
    ImageProviderRequest,
    ImageProviderResult,
)
from app.core.logging import logger


class FalImageAdapter(ImageProvider):
    """
    Direct fal.ai adapter supporting:
      - `fal-ai/flux/schnell` (low-cost fast text-to-image)
      - `fal-ai/flux-pulid` (identity-preserving Face-Lock remix)
    Uses the dynamically injected `req.api_key` from Supabase `ai_provider_secrets`.
    """

    provider_key = "fal"

    def supports(self, task: str) -> bool:
        return task in ("text_to_image", "face_lock_remix")

    def _resolve_image_size(self, req: ImageProviderRequest) -> str:
        ratio_map = req.capabilities.get("aspect_ratio_map") or {
            "1:1": "square_hd",
            "16:9": "landscape_16_9",
            "9:16": "portrait_16_9",
            "4:5": "portrait_4_3",
        }
        return ratio_map.get(req.aspect_ratio, "square_hd")

    async def _call_fal_sync(self, endpoint: str, payload: dict, api_key: str) -> Optional[bytes]:
        url = f"https://fal.run/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Key {api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"[fal.ai] {endpoint} HTTP {resp.status_code}: {resp.text[:250]}")
                return None
            data = resp.json()
            images = data.get("images") or []
            if not images or not images[0].get("url"):
                return None
            img_resp = await client.get(images[0]["url"])
            if img_resp.status_code == 200:
                return img_resp.content
        return None

    async def generate(self, req: ImageProviderRequest) -> Optional[ImageProviderResult]:
        if not req.api_key:
            return None
        t0 = time.time()
        endpoint = req.external_model_id or "fal-ai/flux/schnell"
        payload = {
            "prompt": req.prompt,
            "image_size": self._resolve_image_size(req),
            "seed": req.seed,
            "num_images": 1,
        }
        img_bytes = await self._call_fal_sync(endpoint, payload, req.api_key)
        if not img_bytes:
            return None
        return ImageProviderResult(
            image_bytes=img_bytes,
            provider_key=self.provider_key,
            model_key="flux_schnell",
            external_model_id=endpoint,
            provider_cost_usd=0.003,
            latency_ms=int((time.time() - t0) * 1000),
        )

    async def facelock_remix(self, req: ImageProviderRequest) -> Optional[ImageProviderResult]:
        if not req.api_key or not req.reference_image_url:
            return None
        t0 = time.time()
        endpoint = req.external_model_id or "fal-ai/flux-pulid"
        payload = {
            "prompt": req.prompt,
            "reference_image_url": req.reference_image_url,
            "image_size": self._resolve_image_size(req),
            "seed": req.seed,
            "id_weight": 1.0,
        }
        if req.negative_prompt and req.capabilities.get("supports_negative_prompt", True):
            payload["negative_prompt"] = req.negative_prompt
        img_bytes = await self._call_fal_sync(endpoint, payload, req.api_key)
        if not img_bytes:
            return None
        return ImageProviderResult(
            image_bytes=img_bytes,
            provider_key=self.provider_key,
            model_key="flux_pulid_facelock",
            external_model_id=endpoint,
            provider_cost_usd=0.025,
            latency_ms=int((time.time() - t0) * 1000),
        )


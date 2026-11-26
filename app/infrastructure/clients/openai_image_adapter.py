import base64
import time
import httpx
from typing import Optional
from app.infrastructure.clients.image_provider import (
    ImageProvider,
    ImageProviderRequest,
    ImageProviderResult,
)
from app.core.logging import logger


class OpenAIImageAdapter(ImageProvider):
    """
    Direct OpenAI Images API adapter (`gpt-image-1`).
    Supports both text-to-image generation and natural-language image editing.
    Note: `negative_prompt` is intentionally omitted because `gpt-image-1` rejects unsupported params.
    """

    provider_key = "openai"

    def supports(self, task: str) -> bool:
        return task in ("text_to_image", "image_edit")

    def _resolve_size(self, req: ImageProviderRequest) -> str:
        ratio_map = req.capabilities.get("aspect_ratio_map") or {
            "1:1": "1024x1024",
            "16:9": "1536x1024",
            "9:16": "1024x1536",
        }
        return ratio_map.get(req.aspect_ratio, "1024x1024")

    async def generate(self, req: ImageProviderRequest) -> Optional[ImageProviderResult]:
        if not req.api_key:
            return None
        t0 = time.time()
        model_id = req.external_model_id or "gpt-image-1"
        payload = {
            "model": model_id,
            "prompt": req.prompt,
            "size": self._resolve_size(req),
            "n": 1,
        }
        headers = {
            "Authorization": f"Bearer {req.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post("https://api.openai.com/v1/images/generations", json=payload, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"[OpenAI Images] HTTP {resp.status_code}: {resp.text[:250]}")
                return None
            data = resp.json()
            item = (data.get("data") or [{}])[0]
            if item.get("b64_json"):
                img_bytes = base64.b64decode(item["b64_json"])
            elif item.get("url"):
                r2 = await client.get(item["url"])
                img_bytes = r2.content if r2.status_code == 200 else None
            else:
                img_bytes = None

        if not img_bytes:
            return None
        return ImageProviderResult(
            image_bytes=img_bytes,
            provider_key=self.provider_key,
            model_key="gpt_image_1",
            external_model_id=model_id,
            provider_cost_usd=0.04,
            latency_ms=int((time.time() - t0) * 1000),
        )

    async def edit(self, req: ImageProviderRequest) -> Optional[ImageProviderResult]:
        if not req.api_key or not req.reference_image_url:
            return None
        t0 = time.time()
        model_id = req.external_model_id or "gpt-image-1"
        async with httpx.AsyncClient(timeout=60.0) as client:
            src_resp = await client.get(req.reference_image_url)
            if src_resp.status_code != 200:
                return None
            files = {"image": ("source.png", src_resp.content, "image/png")}
            data = {"model": model_id, "prompt": req.prompt, "size": self._resolve_size(req)}
            headers = {"Authorization": f"Bearer {req.api_key}"}
            resp = await client.post("https://api.openai.com/v1/images/edits", data=data, files=files, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"[OpenAI Edit] HTTP {resp.status_code}: {resp.text[:250]}")
                return None
            item = (resp.json().get("data") or [{}])[0]
            if item.get("b64_json"):
                img_bytes = base64.b64decode(item["b64_json"])
            elif item.get("url"):
                r2 = await client.get(item["url"])
                img_bytes = r2.content if r2.status_code == 200 else None
            else:
                img_bytes = None

        if not img_bytes:
            return None
        return ImageProviderResult(
            image_bytes=img_bytes,
            provider_key=self.provider_key,
            model_key="gpt_image_1",
            external_model_id=model_id,
            provider_cost_usd=0.04,
            latency_ms=int((time.time() - t0) * 1000),
        )


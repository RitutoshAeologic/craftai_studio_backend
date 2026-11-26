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


class GeminiImageAdapter(ImageProvider):
    """
    Direct Google Gemini Multimodal Image adapter (`gemini-2.5-flash-image`).
    Handles natural-language image editing and generation via `generateContent`.
    """

    provider_key = "google"

    def supports(self, task: str) -> bool:
        return task in ("text_to_image", "image_edit")

    async def _call_gemini_image(
        self,
        api_key: str,
        model_id: str,
        parts: list,
    ) -> Optional[bytes]:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_id}:generateContent?key={api_key}"
        )
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {"responseModalities": ["IMAGE"]},
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.warning(f"[Gemini Image] HTTP {resp.status_code}: {resp.text[:250]}")
                return None
            data = resp.json()
            candidates = data.get("candidates") or []
            if not candidates:
                logger.warning("[Gemini Image] Empty candidates (possible safety filter block)")
                return None
            for part in candidates[0].get("content", {}).get("parts", []):
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    return base64.b64decode(inline["data"])
        return None

    async def generate(self, req: ImageProviderRequest) -> Optional[ImageProviderResult]:
        if not req.api_key:
            return None
        t0 = time.time()
        model_id = req.external_model_id or "gemini-2.5-flash-image"
        img_bytes = await self._call_gemini_image(
            req.api_key,
            model_id,
            [{"text": req.prompt}],
        )
        if not img_bytes:
            return None
        return ImageProviderResult(
            image_bytes=img_bytes,
            provider_key=self.provider_key,
            model_key="gemini_flash_image",
            external_model_id=model_id,
            provider_cost_usd=0.03,
            latency_ms=int((time.time() - t0) * 1000),
        )

    async def edit(self, req: ImageProviderRequest) -> Optional[ImageProviderResult]:
        if not req.api_key or not req.reference_image_url:
            return None
        t0 = time.time()
        model_id = req.external_model_id or "gemini-2.5-flash-image"
        async with httpx.AsyncClient(timeout=30.0) as client:
            src_resp = await client.get(req.reference_image_url)
            if src_resp.status_code != 200:
                return None
            mime = src_resp.headers.get("content-type", "image/png").split(";")[0]
            b64_src = base64.b64encode(src_resp.content).decode("utf-8")

        parts = [
            {"inlineData": {"mimeType": mime, "data": b64_src}},
            {"text": req.prompt},
        ]
        img_bytes = await self._call_gemini_image(req.api_key, model_id, parts)
        if not img_bytes:
            return None
        return ImageProviderResult(
            image_bytes=img_bytes,
            provider_key=self.provider_key,
            model_key="gemini_flash_image",
            external_model_id=model_id,
            provider_cost_usd=0.03,
            latency_ms=int((time.time() - t0) * 1000),
        )


import urllib.parse
from typing import Optional
import httpx
from app.infrastructure.clients.base import IDiffusionGateway
from app.core.config import settings
from app.core.logging import logger

class PollinationsClient(IDiffusionGateway):
    def __init__(self, base_url: str = "https://gen.pollinations.ai/image"):
        self.base_url = base_url
        self.edits_url = "https://gen.pollinations.ai/v1/images/edits"

    def build_safe_url(self, prompt: str, width: int = 1024, height: int = 1024, seed: int = 42, model: str = "flux") -> str:
        safe_prompt = urllib.parse.quote(prompt.strip(), safe="")
        api_key = settings.POLLINATIONS_API_KEY
        key_param = f"&key={api_key}" if api_key else ""
        return (
            f"{self.base_url}/{safe_prompt}"
            f"?width={width}&height={height}&model={model}&seed={seed}&nologo=true{key_param}"
        )

    async def edit_image(
        self,
        image_url_or_base64: str,
        prompt: str,
        seed: Optional[int] = None,
        model: str = "black-forest-labs/flux.1-kontext-pro"
    ) -> Optional[bytes]:
        """
        Executes true conversational image editing via FLUX.1 Kontext Pro.
        Preserves subject identity, facial features, pose, camera angle, and scene structure
        while applying only the requested modification (e.g. changing shirt, adding glasses).
        """
        api_key = settings.POLLINATIONS_API_KEY
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else ""
        }
        payload = {
            "model": model,
            "prompt": prompt.strip(),
            "image": image_url_or_base64,
            "response_format": "url"
        }
        if seed is not None:
            payload["seed"] = seed

        try:
            logger.info(f"[Pollinations Image Edit] Invoking {model} for image edit: {prompt[:100]}...")
            async with httpx.AsyncClient(timeout=120.0) as client:
                res = await client.post(self.edits_url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    out_url = data.get("data", [{}])[0].get("url")
                    if out_url:
                        logger.info(f"[Pollinations Image Edit] Edit succeeded, downloading output: {out_url}")
                        img_res = await client.get(out_url)
                        if img_res.status_code == 200:
                            return img_res.content
                else:
                    logger.warning(f"[Pollinations Image Edit] Failed with HTTP {res.status_code}: {res.text[:200]}")
        except Exception as e:
            logger.error(f"[Pollinations Image Edit] Exception during image edit: {e}")
        return None

    async def generate_image_bytes(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        seed: int = 42,
        model: str = "flux"
    ) -> Optional[bytes]:
        """Downloads high-res image bytes directly from authenticated Pollinations gateway."""
        url = self.build_safe_url(prompt=prompt, width=width, height=height, seed=seed, model=model)
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.get(url)
                if res.status_code == 200 and len(res.content) > 1000:
                    return res.content
        except Exception as e:
            logger.warning(f"[Pollinations] Error fetching image bytes: {e}")
        return None


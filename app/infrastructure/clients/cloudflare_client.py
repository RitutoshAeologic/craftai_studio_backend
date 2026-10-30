import logging
from typing import Optional
import httpx
from app.core.config import settings

logger = logging.getLogger("craftai.cloudflare")

class CloudflareAIClient:
    """
    Cloudflare Workers AI Serverless Inference Client.
    Provides free, ultra-fast serverless diffusion models on Cloudflare's Global Edge.
    Supported models:
      - @cf/black-forest-labs/flux-1-schnell (FLUX.1 Schnell)
      - @cf/stabilityai/stable-diffusion-xl-base-1.0 (SDXL Base 1.0)
      - @cf/bytedance/stable-diffusion-xl-lightning (SDXL Lightning)
    """

    def __init__(
        self,
        account_id: Optional[str] = None,
        api_token: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        self.account_id = (account_id or settings.CLOUDFLARE_ACCOUNT_ID).strip()
        self.api_token = (api_token or settings.CLOUDFLARE_API_TOKEN).strip()
        self.default_model = default_model or settings.CLOUDFLARE_IMAGE_MODEL or "@cf/black-forest-labs/flux-1-schnell"
        self.base_url = "https://api.cloudflare.com/client/v4/accounts"

    @property
    def is_configured(self) -> bool:
        """Returns True if valid Cloudflare Workers AI credentials are provided."""
        return bool(self.account_id and self.api_token)

    async def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        num_steps: int = 4,
        seed: Optional[int] = None,
        model: Optional[str] = None,
    ) -> Optional[bytes]:
        """
        Executes text-to-image inference on Cloudflare Workers AI.
        Returns raw image bytes (PNG/JPEG) on success, or None on failure/unconfigured.
        """
        if not self.is_configured:
            logger.debug("[Cloudflare Workers AI] Client not configured with ACCOUNT_ID/API_TOKEN. Skipping.")
            return None

        target_model = model or self.default_model
        endpoint = f"{self.base_url}/{self.account_id}/ai/run/{target_model}"

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "User-Agent": "CraftAI-Studio/1.0",
        }

        # Clamp prompt to Cloudflare's strict 2048 character limit
        safe_prompt = prompt.strip()
        if len(safe_prompt) > 2000:
            safe_prompt = safe_prompt[:2000].rsplit(" ", 1)[0]

        # Build model-specific payload
        payload = {"prompt": safe_prompt}
        if "flux" in target_model.lower():
            payload["steps"] = min(max(num_steps or 4, 1), 8)
        else:
            if num_steps:
                payload["num_steps"] = min(max(num_steps, 1), 30)
            if seed is not None:
                payload["seed"] = seed
            if width:
                payload["width"] = width
            if height:
                payload["height"] = height

        try:
            logger.info(f"[Cloudflare Workers AI] Dispatching generation to {target_model}...")
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(endpoint, json=payload, headers=headers)

                if resp.status_code == 200:
                    content_type = resp.headers.get("content-type", "")
                    content = resp.content

                    # Check for binary image response
                    if "image" in content_type or content.startswith(b"\x89PNG") or content.startswith(b"\xff\xd8\xff"):
                        logger.info(f"[Cloudflare Workers AI] Successfully generated image ({len(content)} bytes)")
                        return content

                    # Handle possible JSON wrapped response
                    try:
                        data = resp.json()
                        if isinstance(data, dict) and data.get("result", {}).get("image"):
                            import base64
                            b64_data = data["result"]["image"]
                            logger.info(f"[Cloudflare Workers AI] Decoded base64 result ({len(b64_data)} chars)")
                            return base64.b64decode(b64_data)
                    except Exception:
                        pass

                    logger.warning(f"[Cloudflare Workers AI] HTTP 200 received but unrecognized content-type: {content_type}")
                    return None
                elif resp.status_code == 429:
                    logger.warning("[Cloudflare Workers AI] Daily 10,000 neuron quota reached (HTTP 429). Will trigger fallback.")
                    return None
                else:
                    logger.warning(f"[Cloudflare Workers AI] Generation failed with HTTP {resp.status_code}: {resp.text[:200]}")
                    return None

        except httpx.TimeoutException:
            logger.error("[Cloudflare Workers AI] Request timed out after 45s.")
            return None
        except Exception as e:
            logger.error(f"[Cloudflare Workers AI] Unexpected error during inference: {e}")
            return None

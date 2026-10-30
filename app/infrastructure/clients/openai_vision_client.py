import base64
import json
import httpx
from typing import Dict, Any, Optional
from app.infrastructure.clients.base import IVisionClient
from app.core.config import settings
from app.core.logging import logger

class OpenAIVisionClient(IVisionClient):
    """
    Multimodal Aesthetic Vision Client powered by OpenAI GPT-4o-mini Vision.
    Reverse-engineers camera optics, lighting parameters, and visual style tags.
    """
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or getattr(settings, "OPENAI_API_KEY", "")
        self.model = model

    async def scan_photo(self, photo_url_or_path: str) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not configured for OpenAIVisionClient")

        prompt = (
            "Analyze this artwork/photo and return ONLY a valid JSON object with keys: "
            "extracted_prompt (a vivid 60-word generative diffusion prompt describing the scene, subject, lighting, and textures), "
            "detected_style (one of: 'Realistic Photo', 'Anime / Manga', '3D Cartoon', 'Cyberpunk', 'Cinematic', 'Oil Painting', 'Fantasy Art'), "
            "lighting_optics (e.g. 'Golden hour, rim light, 35mm f/1.4 lens, soft bokeh')."
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": photo_url_or_path}}
                            ]
                        }
                    ],
                    "max_tokens": 500
                }
            )

            if resp.status_code != 200:
                raise RuntimeError(f"OpenAI Vision error: HTTP {resp.status_code} - {resp.text}")

            result = resp.json()
            content_str = result["choices"][0]["message"]["content"]
            parsed = json.loads(content_str)

            return {
                "extracted_prompt": parsed.get("extracted_prompt", ""),
                "detected_style": parsed.get("detected_style", "Realistic Photo"),
                "lighting_optics": parsed.get("lighting_optics", "Cinematic ambient light"),
                "model_used": f"openai/{self.model}"
            }
